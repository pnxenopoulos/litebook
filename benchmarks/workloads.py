"""Deterministic event shapes mirrored by benches/support/mod.rs."""

from dataclasses import dataclass

import litebook as lb


@dataclass(frozen=True)
class Case:
    name: str
    kind: str
    scale: int


CASES = (
    Case("resting_existing/8", "existing", 8),
    Case("resting_existing/512", "existing", 512),
    Case("resting_new/256", "new", 256),
    Case("cancel/16", "cancel", 16),
    Case("cancel/256", "cancel", 256),
    Case("cancel/4096", "cancel", 4096),
    Case("partial/256", "partial", 256),
    Case("sweep/8", "sweep", 8),
    Case("sweep/64", "sweep", 64),
    Case("mixed/64", "mixed", 64),
)


class Random:
    def __init__(self):
        self.state = 0x5EED

    def next(self):
        self.state ^= (self.state << 13) & ((1 << 64) - 1)
        self.state ^= self.state >> 7
        self.state ^= (self.state << 17) & ((1 << 64) - 1)
        return self.state


@dataclass
class Trace:
    seeds: list
    commands: list
    fills: int
    cancels: int
    active: int


def trace(case):
    seeds, commands = [], []
    added = 0
    random = Random()

    def add(buy, ticks, quantity=1.0):
        nonlocal added
        slot = len(seeds) + added
        added += 1
        commands.append(("add", (buy, ticks, quantity)))
        return slot

    fills = cancels = active = 0
    if case.kind == "existing":
        seeds.extend((True, 10_000 - i, 1.0) for i in range(case.scale))
        for i in range(256):
            add(True, 10_000 - i % case.scale)
        active = case.scale + 256
    elif case.kind == "new":
        for i in range(case.scale):
            add(True, 10_000 + i)
        active = case.scale
    elif case.kind == "cancel":
        seeds.extend((True, 10_000, 1.0) for _ in range(case.scale))
        slots = list(range(case.scale))
        for i in range(len(slots) - 1, 0, -1):
            j = random.next() % (i + 1)
            slots[i], slots[j] = slots[j], slots[i]
        cancels = min(case.scale, 256)
        commands.extend(("cancel", slot) for slot in slots[:cancels])
        active = case.scale - cancels
    elif case.kind == "partial":
        seeds.append((False, 10_000, float(case.scale + 1)))
        for _ in range(case.scale):
            add(True, 10_000)
        fills, active = case.scale, 1
    elif case.kind == "sweep":
        seeds.extend((False, 10_000 + i, 1.0) for i in range(case.scale))
        add(True, 10_000 + case.scale, float(case.scale))
        fills = case.scale
    elif case.kind == "mixed":
        seeds.extend((True, 9_990 - i % 8, 1.0) for i in range(64))
        for _ in range(case.scale):
            bid = 9_990 - random.next() % 8
            ask = 10_010 + random.next() % 8
            slot = add(True, bid)
            commands.append(("cancel", slot))
            add(False, ask)
            add(True, ask)
            add(True, 9_990)
            add(False, 9_990)
        fills, cancels, active = case.scale * 2, case.scale, 64
    else:
        raise ValueError(case.kind)
    return Trace(seeds, commands, fills, cancels, active)


def create(book, spec):
    buy, ticks, quantity = spec
    return book.create_order(
        lb.OrderType.Buy if buy else lb.OrderType.Sell, float(ticks), quantity
    )


@dataclass
class Fixture:
    book: object
    events: list
    ids: list
    expected: Trace
    create_orders: bool

    def run(self):
        fills = cancels = 0
        for action, payload in self.events:
            if action == "add":
                if self.create_orders:
                    order = create(self.book, payload)
                    self.ids.append(order.id)
                else:
                    order = payload
                fills += len(self.book.add(order))
            else:
                order_id = self.ids[payload] if self.create_orders else payload
                cancels += self.book.cancel(order_id)
        return fills, cancels

    def validate(self, outcome):
        assert outcome == (self.expected.fills, self.expected.cancels)
        active = self.book.buy_orders + self.book.sell_orders
        assert len(active) == self.expected.active
        assert all(o.quantity > 0 and o.status == lb.OrderStatus.Open for o in active)


def prepare(case, create_orders=False):
    expected = trace(case)
    book = lb.OrderBook(tick_size=1.0)
    ids, events = [], []
    for spec in expected.seeds:
        order = create(book, spec)
        ids.append(order.id)
        fills = book.add(order)
        assert not fills
    for action, payload in expected.commands:
        if create_orders:
            events.append((action, payload))
        elif action == "add":
            order = create(book, payload)
            ids.append(order.id)
            events.append((action, order))
        else:
            events.append((action, ids[payload]))
    return Fixture(book, events, ids, expected, create_orders)

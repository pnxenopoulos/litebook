"""Generated event histories compared with an intentionally simple list-based book."""

from dataclasses import dataclass

import litebook as lb
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


@dataclass
class ModelOrder:
    id: str
    buy: bool
    ticks: int
    quantity: int
    sequence: int


class ReferenceBook:
    def __init__(self):
        self.orders = {}

    def add(self, incoming):
        fills = []
        while incoming.quantity:
            candidates = [
                order
                for order in self.orders.values()
                if order.quantity
                and order.buy != incoming.buy
                and (
                    incoming.ticks >= order.ticks
                    if incoming.buy
                    else incoming.ticks <= order.ticks
                )
            ]
            if not candidates:
                break
            resting = min(
                candidates,
                key=lambda o: (o.ticks if incoming.buy else -o.ticks, o.sequence),
            )
            quantity = min(incoming.quantity, resting.quantity)
            buy, sell = (incoming, resting) if incoming.buy else (resting, incoming)
            fills.append((quantity, sell.ticks * 0.25, buy.id, sell.id))
            incoming.quantity -= quantity
            resting.quantity -= quantity
        self.orders[incoming.id] = incoming
        return fills

    def cancel(self, order_id):
        order = self.orders.get(order_id)
        if order is None or not order.quantity:
            return False
        del self.orders[order_id]
        return True

    def active(self, buy):
        return sorted(
            (o for o in self.orders.values() if o.buy == buy and o.quantity),
            key=lambda o: (o.ticks, o.sequence),
        )


def assert_state(book, model, ids):
    for order_id in ids:
        actual = book.get_order(order_id)
        expected = model.orders.get(order_id)
        if expected is None:
            assert actual is None
        else:
            assert actual.id == expected.id
            assert actual.quantity == expected.quantity
            assert actual.price_in_ticks == expected.ticks
            assert actual.side == (
                lb.OrderType.Buy if expected.buy else lb.OrderType.Sell
            )
            assert actual.status == (
                lb.OrderStatus.Open if expected.quantity else lb.OrderStatus.Filled
            )
    for buy, actual in [(True, book.buy_orders), (False, book.sell_orders)]:
        expected = model.active(buy)
        assert [(o.id, o.quantity) for o in actual] == [
            (o.id, o.quantity) for o in expected
        ]
        assert all(o.quantity > 0 and o.status == lb.OrderStatus.Open for o in actual)
    buys, sells = model.active(True), model.active(False)
    expected_spread = (
        (sells[0].ticks - buys[-1].ticks) * 0.25 if buys and sells else None
    )
    assert book.spread() == expected_spread


@given(
    st.lists(
        st.tuples(
            st.sampled_from(["buy", "sell", "cancel", "lookup", "duplicate"]),
            st.integers(min_value=1, max_value=20),
            st.integers(min_value=1, max_value=10),
            st.integers(min_value=0, max_value=100),
        ),
        min_size=1,
        max_size=100,
    )
)
@settings(max_examples=150, deadline=None, derandomize=True)
def test_event_histories_match_reference(events):
    book = lb.OrderBook(tick_size=0.25)
    model = ReferenceBook()
    ids = []
    originals = {}
    for sequence, (action, ticks, quantity, index) in enumerate(events):
        if action in ("buy", "sell"):
            buy = action == "buy"
            order = book.create_order(
                lb.OrderType.Buy if buy else lb.OrderType.Sell, ticks * 0.25, quantity
            )
            ids.append(order.id)
            originals[order.id] = order
            expected = model.add(ModelOrder(order.id, buy, ticks, quantity, sequence))
            actual = book.add(order)
            assert [
                (f.quantity, f.price, f.buy_id, f.sell_id) for f in actual
            ] == expected
            assert (
                quantity
                == sum(f.quantity for f in actual) + book.get_order(order.id).quantity
            )
        elif ids:
            order_id = ids[index % len(ids)]
            if action == "cancel":
                assert book.cancel(order_id) == model.cancel(order_id)
            elif action == "duplicate" and order_id in model.orders:
                # Filled IDs remain known; canceled IDs are deliberately not retained.
                with pytest.raises(ValueError):
                    book.add(originals[order_id])
        assert_state(book, model, ids)

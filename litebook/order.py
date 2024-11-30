"""Module for an order in the orderbook."""

import datetime
import decimal
import enum
import uuid

from typing import NamedTuple


class OrderType(enum.StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(enum.StrEnum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELED = "CANCELED"

    def is_open(self) -> bool:
        return self == OrderStatus.OPEN


class Fill(NamedTuple):
    quantity: decimal.Decimal
    price: decimal.Decimal
    buy_id: uuid.UUID
    sell_id: uuid.UUID
    timestamp: datetime.datetime = datetime.datetime.now(datetime.UTC)


class Order:
    def __init__(
        self, side: OrderType, price: decimal.Decimal, quantity: decimal.Decimal
    ):
        if not isinstance(side, OrderType):
            raise NotImplementedError(f"{side} is not supported!")
        self.side = side

        assert price > 0
        self.price = decimal.Decimal(price)

        assert quantity > 0
        self.quantity = decimal.Decimal(quantity)

        self.id = uuid.uuid4()
        self.timestamp = datetime.datetime.now(datetime.UTC)
        self.status = OrderStatus.OPEN
        self.fills: list[Fill] = []

    @property
    def size(self) -> decimal.Decimal:
        return self.price * self.quantity

    def __lt__(self, comparison: "Order") -> bool:
        match self.side:
            case OrderType.BUY:
                return self.price > comparison.price or (
                    self.price == comparison.price
                    and self.timestamp < comparison.timestamp
                )
            case OrderType.SELL:
                return self.price < comparison.price or (
                    self.price == comparison.price
                    and self.timestamp < comparison.timestamp
                )
            case _:
                return False

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"[{self.id}] [{self.side} {self.quantity} @ {self.price}] [Placed at {int(self.timestamp.timestamp() * 1e9)}]"

    def cancel(self) -> None:
        self.status = OrderStatus.CANCELED

    def matches(self, comparison: "Order") -> bool:
        if self.side == comparison.side:
            return False
        return (self.side == OrderType.BUY and self.price >= comparison.price) or (
            self.side == OrderType.SELL and self.price <= comparison.price
        )

    def fill(self, incoming_order: "Order") -> Fill | None:
        if not self.matches(incoming_order):
            return None

        # Determine the fill quantity as the minimum of the two orders' quantities
        fill_quantity = min(self.quantity, incoming_order.quantity)

        # Adjust quantities on both orders
        self.quantity -= fill_quantity
        incoming_order.quantity -= fill_quantity

        # Check status
        if self.quantity == 0:
            self.status = OrderStatus.FILLED
        if incoming_order.quantity == 0:
            incoming_order.status = OrderStatus.FILLED

        # Create a shared Fill object
        fill_price = self.price if self.side == OrderType.SELL else incoming_order.price
        fill = Fill(
            quantity=fill_quantity,
            price=fill_price,
            buy_id=self.id if self.side == OrderType.BUY else incoming_order.id,
            sell_id=self.id if self.side == OrderType.SELL else incoming_order.id,
        )

        # Add the fill to both orders
        self.fills.append(fill)
        incoming_order.fills.append(fill)

        return fill

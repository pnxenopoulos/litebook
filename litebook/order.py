"""Module for an order in the orderbook."""

import datetime
import decimal
import enum
import functools
import uuid


class OrderType(enum.StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class Order:
    def __init__(
        self, side: OrderType, price: decimal.Decimal, quantity: decimal.Decimal
    ):
        self.side = side

        assert price > 0
        self.price = price

        assert quantity > 0
        self.quantity = quantity

        self.id = uuid.uuid4()
        self.timestamp = datetime.datetime.now(datetime.UTC)

    @functools.cached_property
    def value(self) -> decimal.Decimal:
        return self.price * self.quantity

    def __lt__(self, comparison: "Order") -> bool:
        if self.side == OrderType.BUY:
            return self.price > comparison.price or (
                self.price == comparison.price and self.timestamp < comparison.timestamp
            )
        elif self.side == OrderType.SELL:
            return self.price < comparison.price or (
                self.price == comparison.price and self.timestamp < comparison.timestamp
            )

    def __str__(self) -> str:
        return f"{self.side} {self.quantity} @ {self.price} [{int(self.timestamp.timestamp() * 1e9)}]"

    def matches(self, comparison: "Order") -> bool:
        return (
            self.side != comparison.side
            and (self.side == "buy" and self.price >= comparison.price)
            or (self.side == "sell" and self.price <= comparison.price)
        )

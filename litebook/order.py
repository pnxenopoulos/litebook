"""Module for an order in the orderbook."""

import datetime
import decimal
import enum
import uuid

from typing import NamedTuple


class OrderType(enum.StrEnum):
    """Enumeration for order types.

    Attributes:
        BUY: Represents a buy order.
        SELL: Represents a sell order.
    """

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(enum.StrEnum):
    """Enumeration for order statuses.

    Attributes:
        OPEN: The order is open and can be matched.
        FILLED: The order has been completely filled.
        CANCELED: The order has been canceled.
    """

    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELED = "CANCELED"


class Fill(NamedTuple):
    """Represents a trade fill between two orders.

    Attributes:
        quantity (decimal.Decimal): The quantity of the fill.
        price (decimal.Decimal): The price at which the trade was executed.
        buy_id (uuid.UUID): The ID of the buy order.
        sell_id (uuid.UUID): The ID of the sell order.
        timestamp (datetime.datetime): The time of the trade execution.
    """

    quantity: decimal.Decimal
    price: decimal.Decimal
    buy_id: uuid.UUID
    sell_id: uuid.UUID
    timestamp: datetime.datetime = datetime.datetime.now(datetime.UTC)


class Order:
    """Represents an order in the orderbook.

    Attributes:
        side (OrderType): The type of the order (BUY or SELL).
        price (decimal.Decimal): The price of the order.
        quantity (decimal.Decimal): The quantity of the order.
        id (uuid.UUID): The unique identifier for the order.
        timestamp (datetime.datetime): The timestamp when the order was created.
        status (OrderStatus): The current status of the order.
        fills (list[Fill]): A list of fills associated with this order.
    """

    def __init__(
        self, side: OrderType, price: decimal.Decimal, quantity: decimal.Decimal
    ):
        """Initializes an order.

        Args:
            side (OrderType): The type of the order (BUY or SELL).
            price (decimal.Decimal): The price of the order.
            quantity (decimal.Decimal): The quantity of the order.

        Raises:
            NotImplementedError: If the order type is unsupported.
            AssertionError: If the price or quantity is not greater than zero.
        """
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
        """Calculates the total size of the order.

        Returns:
            decimal.Decimal: The total size (price * quantity).
        """
        return self.price * self.quantity

    @property
    def is_open(self) -> bool:
        """Checks if the order is still open.

        Returns:
            bool: True if the order is open, False otherwise.
        """
        return self.status == OrderStatus.OPEN

    def __lt__(self, comparison: "Order") -> bool:
        """Compares two orders for sorting purposes.

        Orders are compared based on price and timestamp:
        - Higher price for BUY orders has priority.
        - Lower price for SELL orders has priority.
        - If prices are equal, earlier timestamps take priority.

        Args:
            comparison (Order): The order to compare against.

        Returns:
            bool: True if this order has priority, False otherwise.
        """
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
        """Provides a representation of the order when printing."""
        return self.__str__()

    def __str__(self) -> str:
        """Returns a formatted string representation of the order."""
        return f"[{self.id}] [{self.side} {self.quantity} @ {self.price}] [Placed at {int(self.timestamp.timestamp() * 1e9)}]"

    def cancel(self) -> None:
        """Cancels the order."""
        self.status = OrderStatus.CANCELED

    def matches(self, comparison: "Order") -> bool:
        """Checks if the order matches with another order.

        A match occurs if:
        - The orders are on opposite sides (BUY vs SELL).
        - The prices satisfy the trade condition.

        Args:
            comparison (Order): The order to check for a match.

        Returns:
            bool: True if the orders match, False otherwise.
        """
        if self.side == comparison.side:
            return False
        return (self.side == OrderType.BUY and self.price >= comparison.price) or (
            self.side == OrderType.SELL and self.price <= comparison.price
        )

    def fill(self, incoming_order: "Order") -> Fill | None:
        """Fills the order with another incoming order.

        Adjusts the quantities and creates a fill record.

        Args:
            incoming_order (Order): The incoming order to fill against.

        Returns:
            Fill | None: A Fill object if the orders are matched and filled, otherwise None.
        """
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

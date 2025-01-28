from typing import List, Optional

class OrderType:
    """Represents the side of an order, either Buy or Sell."""

    Buy: "OrderType"
    """An OrderType representing a Buy order."""

    Sell: "OrderType"
    """An OrderType representing a Sell order."""

    def __eq__(self, other: object) -> bool:
        """Checks if this OrderType is equal to another object.

        Args:
            other (object): The object to compare with.

        Returns:
            bool: True if both are the same OrderType, False otherwise.
        """
        ...

class OrderStatus:
    """Represents the status of an order (Open, Filled, or Canceled)."""

    Open: "OrderStatus"
    """An OrderStatus indicating the order is open."""

    Filled: "OrderStatus"
    """An OrderStatus indicating the order has been filled."""

    Canceled: "OrderStatus"
    """An OrderStatus indicating the order has been canceled."""

    def __eq__(self, other: object) -> bool:
        """Checks if this OrderStatus is equal to another object.

        Args:
            other (object): The object to compare with.

        Returns:
            bool: True if both are the same OrderStatus, False otherwise.
        """
        ...

class Fill:
    """Represents a trade fill with details about the matched quantity, price, and timing."""

    def __init__(
        self, quantity: float, price: float, buy_id: str, sell_id: str, timestamp: int
    ) -> None:
        """Initializes a Fill.

        Args:
            quantity (float): The quantity filled.
            price (float): The price at which the quantity was filled.
            buy_id (str): The identifier of the buy order.
            sell_id (str): The identifier of the sell order.
            timestamp (int): The timestamp (e.g., UNIX time) of the fill.
        """
        ...

    def __repr__(self) -> str:
        """Returns a string representation of the Fill."""
        ...

    @property
    def quantity(self) -> float:
        """float: The quantity that was filled."""
        ...

    @property
    def price(self) -> float:
        """float: The price at which the quantity was filled."""
        ...

    @property
    def buy_id(self) -> str:
        """str: The identifier of the buy order involved in the fill."""
        ...

    @property
    def sell_id(self) -> str:
        """str: The identifier of the sell order involved in the fill."""
        ...

    @property
    def timestamp(self) -> int:
        """int: The timestamp of when the fill occurred."""
        ...

class Order:
    """Represents an order in the order book, including side, price, quantity, and status."""

    def __init__(
        self, side: OrderType, price_in_ticks: int, quantity: float
    ) -> "Order":
        """Initializes an Order.

        Args:
            side (OrderType): The side of the order (Buy or Sell).
            price_in_ticks (int): The price, represented in ticks.
            quantity (float): The amount of the instrument to trade.

        Returns:
            Order: An instance of the Order class.
        """
        ...

    def __repr__(self) -> str:
        """Returns a string representation of the Order."""
        ...

    def can_match(self, other: "Order") -> bool:
        """Determines if this order can be matched with another order.

        Args:
            other (Order): Another order to compare against.

        Returns:
            bool: True if the orders can match (e.g., opposite sides, matching price),
            False otherwise.
        """
        ...

    def fill(self, incoming: "Order", tick_size: float) -> Optional[Fill]:
        """Attempts to fill this order with an incoming order.

        Args:
            incoming (Order): The incoming order attempting to match.
            tick_size (float): The minimum price increment.

        Returns:
            Optional[Fill]: A Fill object if a match occurs, otherwise None.
        """
        ...

    def is_open(self) -> bool:
        """Checks if the order is still open (not filled or canceled).

        Returns:
            bool: True if the order is open, False otherwise.
        """
        ...

    @property
    def id(self) -> str:
        """str: The unique identifier for this order."""
        ...

    @property
    def side(self) -> OrderType:
        """OrderType: The side (Buy or Sell) of this order."""
        ...

    @property
    def price_in_ticks(self) -> int:
        """int: The price of this order, represented in ticks."""
        ...

    @property
    def quantity(self) -> float:
        """float: The quantity of the order remaining."""
        ...

    @property
    def status(self) -> OrderStatus:
        """OrderStatus: The current status of this order."""
        ...

    @property
    def timestamp(self) -> int:
        """int: The time when this order was created (e.g., as a UNIX timestamp)."""
        ...

class OrderBook:
    """Represents an order book, which manages active orders and executes trades."""

    def __init__(self, *, tick_size: float = 0.01) -> None:
        """Initializes an OrderBook.

        Args:
            tick_size (float, optional): The minimum price increment for orders. Defaults to 0.01.
        """
        ...

    def create_order(self, side: OrderType, price: float, quantity: float) -> Order:
        """Creates a new order in the order book.

        Args:
            side (OrderType): The side of the order (Buy or Sell).
            price (float): The price of the order in floating point.
            quantity (float): The quantity of the instrument to trade.

        Returns:
            Order: The newly created Order object.
        """
        ...

    def add(self, order: Order) -> List[Fill]:
        """Adds an order to the book, matching it against existing orders if possible.

        Args:
            order (Order): The order to add to the book.

        Returns:
            List[Fill]: A list of Fill objects created by matching this order.
        """
        ...

    def cancel(self, order_id: str) -> bool:
        """Cancels an existing order if it is still open.

        Args:
            order_id (str): The ID of the order to cancel.

        Returns:
            bool: True if the order was successfully canceled, False otherwise.
        """
        ...

    def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieves an order by its ID.

        Args:
            order_id (str): The ID of the order to retrieve.

        Returns:
            Optional[Order]: The matching Order if found, otherwise None.
        """
        ...

    @property
    def buy_orders(self) -> List[Order]:
        """List[Order]: The list of active buy orders in the book."""
        ...

    @property
    def sell_orders(self) -> List[Order]:
        """List[Order]: The list of active sell orders in the book."""
        ...

    @property
    def tick_size(self) -> float:
        """float: The minimum price increment for orders in the book."""
        ...

    def spread(self) -> Optional[float]:
        """Calculates the spread between the best buy and sell orders.

        Returns:
            Optional[float]: The spread if both buy and sell orders exist,
            otherwise None.
        """
        ...

    def __repr__(self) -> str:
        """Returns a string representation of the OrderBook."""
        ...

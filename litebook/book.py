"""Module for a limit order book."""

import decimal
import uuid

import sortedcontainers

import litebook.order


class OrderBook:
    """Represents a limit order book for managing buy and sell orders.

    Attributes:
        bids (sortedcontainers.SortedDict): A sorted dictionary for buy orders.
            Keys are price levels in descending order, and values are lists of orders.
        asks (sortedcontainers.SortedDict): A sorted dictionary for sell orders.
            Keys are price levels in ascending order, and values are lists of orders.
        open_orders (dict[uuid.UUID, litebook.order.Order]): A mapping of open
            orders by their unique UUIDs.
        tick_size (decimal.Decimal | None): The minimum price increment for orders.
        market_depth (int | None): The number of ticks from the best bid/ask
            to retain in the order book. If None, no depth limit is enforced.
    """

    def __init__(
        self,
        tick_size: decimal.Decimal | None = decimal.Decimal("0.01"),
        market_depth: int | None = None,
    ) -> None:
        """Initializes the order book with empty bid and ask dictionaries.

        Args:
            tick_size (decimal.Decimal, optional): Default tick size to consider when adding orders. Defaults to decimal.Decimal("0.01").
            market_depth (int | None, optional): How many ticks from the best bid/ask to keep. Defaults to None.
        """
        # Two SortedDicts: one for buy orders, one for sell orders
        # Keys are price levels; values are lists of orders at each level
        self.bids = sortedcontainers.SortedDict(
            lambda x: -x
        )  # Max-heap semantics for buy orders
        self.asks = sortedcontainers.SortedDict()  # Min-heap semantics for sell orders

        # Mapping from UUID to litebook.order.Order
        self.open_orders: dict[uuid.UUID, litebook.order.Order] = {}

        # Tick size for rounding prices
        self.tick_size = decimal.Decimal(tick_size) if tick_size is not None else None

        # Market depth limit
        self.market_depth = int(market_depth) if market_depth is not None else None

    def _is_valid_price(self, price: decimal.Decimal) -> bool:
        """Checks if a price conforms to the tick size.

        Args:
            price (decimal.Decimal): Price to see if it conforms to the book's tick size.

        Returns:
            bool: True if the price is in the right tick size, False otherwise.
        """
        if self.tick_size is not None:
            return (price % self.tick_size) == 0
        else:
            return True

    def _enforce_market_depth(self) -> None:
        """Removes orders outside the allowed market depth in terms of tick size."""
        if (
            self.tick_size is None
            or self.market_depth is None
            or not (self.bids or self.asks)
        ):
            return

        # Calculate allowed price range based on tick size and market depth
        if self.bids:
            best_bid = self.best_bid
            assert isinstance(best_bid, decimal.Decimal)
            bid_lower_bound = best_bid - (self.tick_size * self.market_depth)
        else:
            bid_lower_bound = None

        if self.asks:
            best_ask = self.best_ask
            assert isinstance(best_ask, decimal.Decimal)
            ask_upper_bound = best_ask + (self.tick_size * self.market_depth)
        else:
            ask_upper_bound = None

        # Remove bids below the lower bound
        if bid_lower_bound is not None:
            for price in list(self.bids.keys()):
                if price < bid_lower_bound:
                    self._remove_price_level(price, self.bids)

        # Remove asks above the upper bound
        if ask_upper_bound is not None:
            for price in list(self.asks.keys()):
                if price > ask_upper_bound:
                    self._remove_price_level(price, self.asks)

    def _remove_price_level(
        self, price: decimal.Decimal, book_side: sortedcontainers.SortedDict
    ) -> None:
        """Removes all orders at a specific price level from the book.

        Args:
            price (decimal.Decimal): Price level to remove.
            book_side (sortedcontainers.SortedDict): A sorted dictionary represent an order book side.
        """
        if price in book_side:
            for order in book_side[price]:
                self.open_orders.pop(order.id, None)
            del book_side[price]

    def clear(self) -> None:
        """Clears all orders from the order book."""
        self.bids.clear()
        self.asks.clear()
        self.open_orders.clear()

    def add(self, order: litebook.order.Order) -> list[litebook.order.Fill]:
        """Adds an order to the book and attempts to match it.

        Args:
            order (litebook.order.Order): The order to add.

        Returns:
            list[litebook.order.Fill]: A list of fills resulting from matching
            this order with existing orders.
        """
        # Validate price against tick size
        if not self._is_valid_price(order.price):
            return []

        # Check for matching orders on the opposite side
        fills = self._match(order)

        # If the order is still open, add it to the appropriate side
        if order.is_open:
            order_book = (
                self.bids if order.side == litebook.order.OrderType.BUY else self.asks
            )
            if order.price not in order_book:
                order_book[order.price] = []
            order_book[order.price].append(order)

            # Add to the order map
            self.open_orders[order.id] = order

        # Enforce market depth after adding the order
        self._enforce_market_depth()

        return fills

    def _match(
        self,
        incoming_order: litebook.order.Order,
    ) -> list[litebook.order.Fill]:
        """Matches an incoming order with orders in the opposite book.

        Args:
            incoming_order (litebook.order.Order): The incoming order to match.

        Returns:
            list[litebook.order.Fill]: A list of fills resulting from the match.
        """
        fills = []

        # Determine the opposite book (bids for a sell order, asks for a buy order)
        opposite_book: sortedcontainers.SortedDict = (
            self.bids
            if incoming_order.side == litebook.order.OrderType.SELL
            else self.asks
        )

        # Traverse price levels that can match the incoming order
        while incoming_order.is_open and opposite_book:
            best_price = opposite_book.peekitem(0)[0]  # Best price level

            # Check if the price level matches
            if (
                incoming_order.side == litebook.order.OrderType.BUY
                and incoming_order.price < best_price
            ) or (
                incoming_order.side == litebook.order.OrderType.SELL
                and incoming_order.price > best_price
            ):
                break

            # Get orders at this price level
            orders_at_level = opposite_book[best_price]
            i = 0
            while i < len(orders_at_level) and incoming_order.is_open:
                matched_order = orders_at_level[i]
                fill = matched_order.fill(incoming_order)
                if fill is not None:
                    fills.append(fill)

                # If the matched order is fully filled, remove it from the list and map
                if matched_order.status == litebook.order.OrderStatus.FILLED:
                    self.open_orders.pop(matched_order.id, None)
                    orders_at_level.pop(i)
                else:
                    i += 1

            # If no more orders at this price level, remove the level from the book
            if not orders_at_level:
                del opposite_book[best_price]

        return fills

    def cancel(self, order_id: uuid.UUID | str) -> None:
        """Cancels an order by its unique ID.

        Args:
            order_id (uuid.UUID | str): The unique ID of the order to cancel.
        """
        if isinstance(order_id, str):
            order_id = uuid.UUID(order_id)

        if order_id in self.open_orders:
            order = self.open_orders[order_id]
            order_book = (
                self.bids if order.side == litebook.order.OrderType.BUY else self.asks
            )

            # Locate and remove the order from the order book
            if order.price in order_book:
                orders_at_level = order_book[order.price]
                for i, existing_order in enumerate(orders_at_level):
                    if existing_order.id == order.id:
                        order.cancel()
                        del orders_at_level[i]
                        if not orders_at_level:
                            del order_book[order.price]
                        break

            # Remove from the order map
            del self.open_orders[order_id]

    def get(self, order_id: uuid.UUID | str) -> litebook.order.Order | None:
        """Retrieves an order by its unique ID.

        Args:
            order_id (uuid.UUID | str): The unique ID of the order to retrieve.

        Returns:
            litebook.order.Order | None: The order if found, otherwise None.
        """
        if isinstance(order_id, str):
            order_id = uuid.UUID(order_id)

        if order_id in self.open_orders:
            order = self.open_orders[order_id]
            return order
        return None

    def get_orders_at_price(
        self,
        price: decimal.Decimal,
        side: litebook.order.OrderType,
        k: int | None = None,
    ) -> list[litebook.order.Order]:
        """Retrieves orders at a specific price level on a given side.

        Args:
            price (decimal.Decimal): The price level to query.
            side (litebook.order.OrderType): The side (BUY or SELL) to query.
            k (int | None): The number of orders to retrieve. If None, return all orders.

        Returns:
            list[litebook.order.Order]: A list of orders at the specified price level.
        """
        price = decimal.Decimal(price)  # Ensure price is a Decimal
        order_book = self.bids if side == litebook.order.OrderType.BUY else self.asks
        orders_at_price = order_book.get(price, [])

        # Return only the first `k` orders if `k` is specified, otherwise return all
        return orders_at_price[:k] if k is not None else orders_at_price

    @property
    def spread(self) -> decimal.Decimal | None:
        """Calculates the bid-ask spread.

        Returns:
            decimal.Decimal | None: The spread if both bids and asks exist, otherwise None.
        """
        best_buy_price: decimal.Decimal | None = (
            self.bids.peekitem(0)[0] if self.bids else None
        )
        best_sell_price: decimal.Decimal | None = (
            self.asks.peekitem(0)[0] if self.asks else None
        )
        return (
            best_sell_price - best_buy_price
            if best_buy_price and best_sell_price
            else None
        )

    @property
    def best_bid(self) -> decimal.Decimal | None:
        """Finds the best bid price.

        Returns:
            decimal.Decimal | None: The highest bid price, or None if there are no bids.
        """
        return self.bids.peekitem(0)[0] if self.bids else None

    @property
    def best_ask(self) -> decimal.Decimal | None:
        """Finds the best ask price.

        Returns:
            decimal.Decimal | None: The lowest ask price, or None if there are no asks.
        """
        return self.asks.peekitem(0)[0] if self.asks else None

    @property
    def buy_volume(self) -> decimal.Decimal:
        """Calculates the total buy volume.

        Returns:
            decimal.Decimal: The total buy volume across all price levels.
        """
        return decimal.Decimal(
            sum(
                sum(order.quantity for order in orders) for orders in self.bids.values()
            )
        )

    @property
    def sell_volume(self) -> decimal.Decimal:
        """Calculates the total sell volume.

        Returns:
            decimal.Decimal: The total sell volume across all price levels.
        """
        return decimal.Decimal(
            sum(
                sum(order.quantity for order in orders) for orders in self.asks.values()
            )
        )

    @property
    def open_volume(self) -> decimal.Decimal:
        """Calculates the total open volume (buy + sell).

        Returns:
            decimal.Decimal: The total open volume across all price levels.
        """
        return self.buy_volume + self.sell_volume

    def __repr__(self) -> str:
        """Provides a representation of the order when printing."""
        return f"Best Bid: {self.best_bid}, Best Ask: {self.best_ask} (Spread: {self.spread})\n Open Buy Volume: {self.buy_volume}, Open Sell Volume: {self.sell_volume}"

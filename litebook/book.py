import decimal
import sortedcontainers
import uuid

import litebook.order


class OrderBook:
    def __init__(self):
        # Two SortedDicts: one for buy orders, one for sell orders
        # Keys are price levels; values are lists of orders at each level
        self.bids = sortedcontainers.SortedDict(
            lambda x: -x
        )  # Max-heap semantics for buy orders
        self.asks = sortedcontainers.SortedDict()  # Min-heap semantics for sell orders

        # Mapping from UUID to litebook.order.Order
        self.open_orders = {}

    def clear(self) -> None:
        self.bids.clear()
        self.asks.clear()
        self.open_orders.clear()

    def add(self, order: litebook.order.Order) -> list[litebook.order.Fill]:
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

        return fills

    def _match(
        self,
        incoming_order: litebook.order.Order,
    ) -> list[litebook.order.Fill]:
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
        price = decimal.Decimal(price)  # Ensure price is a Decimal
        order_book = self.bids if side == litebook.order.OrderType.BUY else self.asks
        orders_at_price = order_book.get(price, [])

        # Return only the first `k` orders if `k` is specified, otherwise return all
        return orders_at_price[:k] if k is not None else orders_at_price

    @property
    def spread(self) -> decimal.Decimal | None:
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
        return self.bids.peekitem(0)[0] if self.bids else None

    @property
    def best_ask(self) -> decimal.Decimal | None:
        return self.asks.peekitem(0)[0] if self.asks else None

    @property
    def buy_volume(self) -> decimal.Decimal:
        return decimal.Decimal(
            sum(
                sum(order.quantity for order in orders) for orders in self.bids.values()
            )
        )

    @property
    def sell_volume(self) -> decimal.Decimal:
        return decimal.Decimal(
            sum(
                sum(order.quantity for order in orders) for orders in self.asks.values()
            )
        )

    @property
    def open_volume(self) -> decimal.Decimal:
        return self.buy_volume + self.sell_volume

    def __repr__(self) -> str:
        return f"Best Bid: {self.best_bid}, Best Ask: {self.best_ask} (Spread: {self.spread})\n Open Buy Volume: {self.buy_volume}, Open Sell Volume: {self.sell_volume}"

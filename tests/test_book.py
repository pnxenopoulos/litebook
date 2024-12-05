"""Test the litebook.book module."""

import pytest
import decimal
import uuid

from litebook.order import Order, OrderType, OrderStatus
from litebook.book import OrderBook


@pytest.fixture
def order_book() -> OrderBook:
    return OrderBook(tick_size=decimal.Decimal("0.05"), market_depth=100)


def test_orderbook_initialization(order_book):
    assert len(order_book.bids) == 0
    assert len(order_book.asks) == 0
    assert len(order_book.open_orders) == 0


def test_is_valid_price(order_book):
    assert order_book._is_valid_price(decimal.Decimal("10.05")) is True
    assert order_book._is_valid_price(decimal.Decimal("10.03")) is False
    assert order_book._is_valid_price(decimal.Decimal("0.10")) is True
    assert order_book._is_valid_price(decimal.Decimal("0.07")) is False


def test_enforce_market_depth_with_ticks(order_book):
    # Add orders within and outside the market depth (3 ticks)
    order_book.market_depth = None  # Enforce depth to 3 ticks

    buy_order1 = Order(
        OrderType.BUY, decimal.Decimal("10.00"), decimal.Decimal("5.0")
    )  # Best bid
    buy_order2 = Order(
        OrderType.BUY, decimal.Decimal("9.95"), decimal.Decimal("5.0")
    )  # 1 tick below
    buy_order3 = Order(
        OrderType.BUY, decimal.Decimal("9.90"), decimal.Decimal("5.0")
    )  # 2 ticks below
    buy_order4 = Order(
        OrderType.BUY, decimal.Decimal("9.85"), decimal.Decimal("5.0")
    )  # 3 ticks below
    buy_order5 = Order(
        OrderType.BUY, decimal.Decimal("9.80"), decimal.Decimal("5.0")
    )  # 4 ticks below (outside)

    sell_order1 = Order(
        OrderType.SELL, decimal.Decimal("10.20"), decimal.Decimal("5.0")
    )  # Best ask
    sell_order2 = Order(
        OrderType.SELL, decimal.Decimal("10.25"), decimal.Decimal("5.0")
    )  # 1 tick above
    sell_order3 = Order(
        OrderType.SELL, decimal.Decimal("10.30"), decimal.Decimal("5.0")
    )  # 2 ticks above
    sell_order4 = Order(
        OrderType.SELL, decimal.Decimal("10.35"), decimal.Decimal("5.0")
    )  # 3 ticks above
    sell_order5 = Order(
        OrderType.SELL, decimal.Decimal("10.40"), decimal.Decimal("5.0")
    )  # 4 ticks above (outside)

    order_book.add(buy_order1)
    order_book.add(buy_order2)
    order_book.add(buy_order3)
    order_book.add(buy_order4)
    order_book.add(buy_order5)

    order_book.add(sell_order1)
    order_book.add(sell_order2)
    order_book.add(sell_order3)
    order_book.add(sell_order4)
    order_book.add(sell_order5)

    # Enforce market depth
    order_book.market_depth = 3
    order_book._enforce_market_depth()

    # Verify orders within the depth remain
    assert buy_order1.id in order_book.open_orders
    assert buy_order2.id in order_book.open_orders
    assert buy_order3.id in order_book.open_orders
    assert buy_order4.id in order_book.open_orders

    assert sell_order1.id in order_book.open_orders
    assert sell_order2.id in order_book.open_orders
    assert sell_order3.id in order_book.open_orders
    assert sell_order4.id in order_book.open_orders

    # Verify orders outside the depth are removed
    assert buy_order5.id not in order_book.open_orders
    assert sell_order5.id not in order_book.open_orders


def test_remove_price_level(order_book):
    buy_order1 = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    buy_order2 = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("3.0"))
    sell_order = Order(OrderType.SELL, decimal.Decimal("12.0"), decimal.Decimal("4.0"))

    order_book.add(buy_order1)
    order_book.add(buy_order2)
    order_book.add(sell_order)

    # Remove price level for buy orders
    order_book._remove_price_level(decimal.Decimal("10.0"), order_book.bids)

    # Verify all orders at that price are removed
    assert buy_order1.id not in order_book.open_orders
    assert buy_order2.id not in order_book.open_orders
    assert decimal.Decimal("10.0") not in order_book.bids

    # Verify sell orders are unaffected
    assert sell_order.id in order_book.open_orders
    assert decimal.Decimal("12.0") in order_book.asks


def test_add_buy_order(order_book):
    order = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    fills = order_book.add(order)

    assert len(fills) == 0
    assert len(order_book.bids) == 1
    assert len(order_book.asks) == 0
    assert order.id in order_book.open_orders
    assert order_book.best_bid == decimal.Decimal("10.0")


def test_add_sell_order(order_book):
    order = Order(OrderType.SELL, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    fills = order_book.add(order)

    assert len(fills) == 0
    assert len(order_book.bids) == 0
    assert len(order_book.asks) == 1
    assert order.id in order_book.open_orders
    assert order_book.best_ask == decimal.Decimal("10.0")


def test_matching_orders(order_book):
    buy_order = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    sell_order = Order(OrderType.SELL, decimal.Decimal("10.0"), decimal.Decimal("5.0"))

    order_book.add(buy_order)
    fills = order_book.add(sell_order)

    assert len(fills) == 1
    assert fills[0].quantity == decimal.Decimal("5.0")
    assert fills[0].price == decimal.Decimal("10.0")
    assert fills[0].buy_id == buy_order.id
    assert fills[0].sell_id == sell_order.id
    assert len(order_book.bids) == 0
    assert len(order_book.asks) == 0


def test_partial_fill(order_book):
    buy_order = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    sell_order = Order(OrderType.SELL, decimal.Decimal("10.0"), decimal.Decimal("3.0"))

    order_book.add(buy_order)
    fills = order_book.add(sell_order)

    assert len(fills) == 1
    assert fills[0].quantity == decimal.Decimal("3.0")
    assert buy_order.quantity == decimal.Decimal("2.0")
    assert buy_order.status == OrderStatus.OPEN
    assert sell_order.status == OrderStatus.FILLED
    assert len(order_book.bids) == 1
    assert len(order_book.asks) == 0


def test_cancel_order(order_book):
    order = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    order_book.add(order)

    order_book.cancel(order.id)

    assert order.status == OrderStatus.CANCELED
    assert len(order_book.bids) == 0
    assert order.id not in order_book.open_orders


def test_get_order(order_book):
    order = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    order_book.add(order)

    retrieved_order = order_book.get(order.id)
    assert retrieved_order == order

    non_existent_id = uuid.uuid4()
    assert order_book.get(non_existent_id) is None


def test_get_orders_at_price(order_book):
    order1 = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    order2 = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("3.0"))
    order_book.add(order1)
    order_book.add(order2)

    orders = order_book.get_orders_at_price(decimal.Decimal("10.0"), OrderType.BUY)
    assert len(orders) == 2
    assert order1 in orders
    assert order2 in orders


def test_spread_calculation(order_book):
    buy_order = Order(OrderType.BUY, decimal.Decimal("9.0"), decimal.Decimal("5.0"))
    sell_order = Order(OrderType.SELL, decimal.Decimal("10.0"), decimal.Decimal("5.0"))

    order_book.add(buy_order)
    order_book.add(sell_order)

    assert order_book.spread == decimal.Decimal("1.0")


def test_volume_calculations(order_book):
    buy_order1 = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    buy_order2 = Order(OrderType.BUY, decimal.Decimal("9.0"), decimal.Decimal("3.0"))
    sell_order = Order(OrderType.SELL, decimal.Decimal("11.0"), decimal.Decimal("4.0"))

    order_book.add(buy_order1)
    order_book.add(buy_order2)
    order_book.add(sell_order)

    assert order_book.buy_volume == decimal.Decimal("8.0")
    assert order_book.sell_volume == decimal.Decimal("4.0")
    assert order_book.open_volume == decimal.Decimal("12.0")


def test_clear_orderbook(order_book):
    buy_order = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    sell_order = Order(OrderType.SELL, decimal.Decimal("11.0"), decimal.Decimal("5.0"))

    order_book.add(buy_order)
    order_book.add(sell_order)
    order_book.clear()

    assert len(order_book.bids) == 0
    assert len(order_book.asks) == 0
    assert len(order_book.open_orders) == 0


def test_price_time_priority(order_book):
    # Create orders with same price but different timestamps
    buy_order1 = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    buy_order2 = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("3.0"))
    sell_order = Order(OrderType.SELL, decimal.Decimal("10.0"), decimal.Decimal("2.0"))

    order_book.add(buy_order1)
    order_book.add(buy_order2)
    fills = order_book.add(sell_order)

    assert len(fills) == 1
    assert fills[0].buy_id == buy_order1.id  # First order should be filled first


def test_multiple_price_levels(order_book):
    buy_order1 = Order(OrderType.BUY, decimal.Decimal("10.0"), decimal.Decimal("5.0"))
    buy_order2 = Order(OrderType.BUY, decimal.Decimal("9.0"), decimal.Decimal("3.0"))
    sell_order = Order(OrderType.SELL, decimal.Decimal("9.5"), decimal.Decimal("6.0"))

    order_book.add(buy_order1)
    order_book.add(buy_order2)
    fills = order_book.add(sell_order)

    assert len(fills) == 1
    assert fills[0].buy_id == buy_order1.id  # Higher price order should be filled first

"""Test the litebook Order, OrderBook, OrderStatus, OrderType modules."""

import litebook as lb
import pytest


@pytest.fixture
def order_book() -> lb.OrderBook:
    """Create an OrderBook with a tick size of 0.05 for testing."""
    return lb.OrderBook(tick_size=0.05)


def test_order_creation():
    """Test that orders can be created through the OrderBook."""
    book = lb.OrderBook(tick_size=0.05)

    # Create a buy order
    buy_order = book.create_order(lb.OrderType.Buy, price=10.00, quantity=5.0)
    assert buy_order.side == lb.OrderType.Buy
    assert buy_order.quantity == 5.0
    assert buy_order.price_in_ticks == 200  # 10.00 / 0.05 = 200
    assert buy_order.status == lb.OrderStatus.Open

    # Create a sell order
    sell_order = book.create_order(lb.OrderType.Sell, price=10.05, quantity=3.0)
    assert sell_order.side == lb.OrderType.Sell
    assert sell_order.quantity == 3.0
    assert sell_order.price_in_ticks == 201  # 10.05 / 0.05 = 201
    assert sell_order.status == lb.OrderStatus.Open


def test_order_matching():
    """Test that orders can match correctly."""
    book = lb.OrderBook(tick_size=0.05)

    # Create orders that should match
    buy_order = book.create_order(lb.OrderType.Buy, price=10.05, quantity=5.0)
    sell_order = book.create_order(lb.OrderType.Sell, price=10.05, quantity=5.0)

    # Add buy order first
    fills = book.add(buy_order)
    assert len(fills) == 0  # No fills yet

    # Add matching sell order
    fills = book.add(sell_order)
    assert len(fills) == 1
    fill = fills[0]
    assert fill.quantity == 5.0
    assert fill.price == 10.05
    assert fill.buy_id == buy_order.id
    assert fill.sell_id == sell_order.id


def test_partial_fill():
    """Test partial order fills."""
    book = lb.OrderBook(tick_size=0.05)

    # Create orders where sell quantity < buy quantity
    buy_order = book.create_order(lb.OrderType.Buy, price=10.05, quantity=5.0)
    sell_order = book.create_order(lb.OrderType.Sell, price=10.05, quantity=3.0)

    # Add orders and check fill
    book.add(buy_order)
    fills = book.add(sell_order)

    assert len(fills) == 1
    fill = fills[0]
    assert fill.quantity == 3.0
    assert fill.price == 10.05
    buy_order_in_book = book.get_order(buy_order.id)
    assert buy_order_in_book.quantity == 2.0  # Remaining quantity
    sell_order_in_book = book.get_order(sell_order.id)
    assert sell_order_in_book.quantity == 0.0  # Fully filled
    assert (
        sell_order_in_book.status == lb.OrderStatus.Filled
    )  # Status should change to filled


def test_price_matching():
    """Test price matching logic."""
    book = lb.OrderBook(tick_size=0.05)

    # Create orders where buy price > sell price
    buy_order = book.create_order(lb.OrderType.Buy, price=10.10, quantity=5.0)
    sell_order = book.create_order(lb.OrderType.Sell, price=10.05, quantity=5.0)

    # They should match because buy price > sell price
    book.add(buy_order)
    fills = book.add(sell_order)

    assert len(fills) == 1
    assert fills[0].price == 10.05  # Should fill at sell price

    # Test non-matching prices
    buy_order2 = book.create_order(lb.OrderType.Buy, price=10.00, quantity=5.0)
    sell_order2 = book.create_order(lb.OrderType.Sell, price=10.05, quantity=5.0)

    book.add(buy_order2)
    fills = book.add(sell_order2)
    assert len(fills) == 0  # Should not match


def test_order_validation():
    """Test order validation rules."""
    book = lb.OrderBook(tick_size=0.05)

    # Test invalid price
    with pytest.raises(Exception):
        book.create_order(lb.OrderType.Buy, price=-10.0, quantity=5.0)

    # Test invalid quantity
    with pytest.raises(Exception):
        book.create_order(lb.OrderType.Buy, price=10.0, quantity=-5.0)

    # Test valid order
    order = book.create_order(lb.OrderType.Buy, price=10.0, quantity=5.0)
    assert order is not None


def test_can_match():
    """Test the can_match method between orders."""
    book = lb.OrderBook(tick_size=0.05)

    buy_high = book.create_order(lb.OrderType.Buy, price=10.10, quantity=5.0)
    buy_low = book.create_order(lb.OrderType.Buy, price=10.00, quantity=5.0)
    sell_mid = book.create_order(lb.OrderType.Sell, price=10.05, quantity=5.0)

    # Test matching conditions
    assert buy_high.can_match(sell_mid)  # Buy price > Sell price
    assert not buy_low.can_match(sell_mid)  # Buy price < Sell price
    assert not buy_high.can_match(buy_low)  # Same side shouldn't match


def test_cancel_order(order_book: lb.OrderBook):
    """Test that an order can be canceled by its ID."""
    book = order_book

    # Create and add a buy order
    buy_order = book.create_order(lb.OrderType.Buy, price=10.00, quantity=5.0)
    book.add(buy_order)

    # Ensure the order exists in the order book
    assert book.get_order(buy_order.id) is not None
    assert buy_order.status == lb.OrderStatus.Open

    # Cancel the order
    was_canceled = book.cancel(buy_order.id)
    assert was_canceled  # Should return True
    assert (
        book.get_order(buy_order.id) is None
    )  # Should no longer exist in the order book

    # Ensure it's removed from buy orders list
    buy_orders = book.buy_orders
    assert all(order.id != buy_order.id for order in buy_orders)

    # Create and add a sell order
    sell_order = book.create_order(lb.OrderType.Sell, price=10.05, quantity=3.0)
    book.add(sell_order)

    # Cancel the sell order
    was_canceled = book.cancel(sell_order.id)
    assert was_canceled  # Should return True
    assert (
        book.get_order(sell_order.id) is None
    )  # Should no longer exist in the order book

    # Ensure it's removed from sell orders list
    sell_orders = book.sell_orders
    assert all(order.id != sell_order.id for order in sell_orders)

    # Test canceling a non-existent order
    assert not book.cancel("non_existent_id")  # Should return False

"""Test the litebook Order module."""

import litebook as lb
import pytest


@pytest.fixture
def order_book():
    """Create an OrderBook with a standard tick size for testing."""
    return lb.OrderBook(tick_size=1.0)  # Using 1.0 for simpler price-to-tick conversion


@pytest.fixture
def buy_order(order_book):
    """Create a standard buy order at price 100."""
    return order_book.create_order(lb.OrderType.Buy, price=100.0, quantity=10.0)


@pytest.fixture
def sell_order(order_book):
    """Create a standard sell order at matching price 100."""
    return order_book.create_order(lb.OrderType.Sell, price=100.0, quantity=10.0)


@pytest.fixture
def sell_order_higher_price(order_book):
    """Create a sell order at a higher price that shouldn't match the standard buy."""
    return order_book.create_order(lb.OrderType.Sell, price=105.0, quantity=10.0)


@pytest.fixture
def buy_order_higher_price(order_book):
    """Create a buy order at a higher price that should match lower sells."""
    return order_book.create_order(lb.OrderType.Buy, price=105.0, quantity=10.0)


@pytest.fixture
def sell_order_lower_price(order_book):
    """Create a sell order at a lower price that should match standard buys."""
    return order_book.create_order(lb.OrderType.Sell, price=95.0, quantity=10.0)


@pytest.fixture
def buy_order_lower_price(order_book):
    """Create a buy order at a lower price that shouldn't match standard sells."""
    return order_book.create_order(lb.OrderType.Buy, price=95.0, quantity=10.0)


def test_order_creation(buy_order):
    """Test that orders are created with correct attributes."""
    assert buy_order.side == lb.OrderType.Buy
    assert buy_order.price_in_ticks == 100  # Since tick_size is 1.0
    assert buy_order.quantity == 10.0
    assert buy_order.status == lb.OrderStatus.Open
    assert isinstance(buy_order.id, str)
    assert isinstance(buy_order.timestamp, int)


def test_order_matching_logic(
    buy_order, sell_order, buy_order_higher_price, sell_order_higher_price
):
    """Test the can_match method for different order combinations."""
    # Orders at same price should match
    assert buy_order.can_match(sell_order)
    assert sell_order.can_match(buy_order)

    # Orders at non-crossing prices shouldn't match
    assert not buy_order.can_match(sell_order_higher_price)
    assert not sell_order_higher_price.can_match(buy_order)

    # Same-side orders shouldn't match
    assert not buy_order.can_match(buy_order_higher_price)
    assert not sell_order.can_match(sell_order_higher_price)


def test_order_fills(order_book):
    """Test the order filling process through the OrderBook."""
    # Create orders that should match
    buy_order = order_book.create_order(lb.OrderType.Buy, price=100.0, quantity=10.0)
    sell_order = order_book.create_order(lb.OrderType.Sell, price=100.0, quantity=10.0)

    # Add buy order first
    order_book.add(buy_order)

    # Add matching sell order and check fill
    fills = order_book.add(sell_order)

    assert len(fills) == 1
    fill = fills[0]
    assert fill.quantity == 10.0
    assert fill.price == 100.0
    assert fill.buy_id == buy_order.id
    assert fill.sell_id == sell_order.id
    assert isinstance(fill.timestamp, int)


def test_partial_fills(order_book):
    """Test partial order filling through the OrderBook."""
    # Create a buy order for 10 units
    buy_order = order_book.create_order(lb.OrderType.Buy, price=100.0, quantity=10.0)
    # Create a smaller sell order for 5 units
    sell_order = order_book.create_order(lb.OrderType.Sell, price=100.0, quantity=5.0)

    # Add orders and check partial fill
    order_book.add(buy_order)
    fills = order_book.add(sell_order)

    assert len(fills) == 1
    fill = fills[0]
    assert fill.quantity == 5.0
    assert fill.price == 100.0
    buy_order_in_book = order_book.get_order(buy_order.id)
    assert buy_order_in_book.quantity == 5.0  # Remaining quantity
    assert buy_order_in_book.status == lb.OrderStatus.Open
    sell_order_in_book = order_book.get_order(sell_order.id)
    assert sell_order_in_book.quantity == 0.0  # Fully filled
    assert sell_order_in_book.status == lb.OrderStatus.Filled


def test_no_fill_for_non_matching_orders(order_book):
    """Test that non-matching orders don't create fills."""
    buy_order = order_book.create_order(lb.OrderType.Buy, price=100.0, quantity=10.0)
    sell_order = order_book.create_order(lb.OrderType.Sell, price=105.0, quantity=10.0)

    order_book.add(buy_order)
    fills = order_book.add(sell_order)

    assert len(fills) == 0
    assert buy_order.status == lb.OrderStatus.Open
    assert sell_order.status == lb.OrderStatus.Open

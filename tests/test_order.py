import pytest
import decimal

from datetime import datetime

from litebook.order import Order, OrderType, OrderStatus


@pytest.fixture
def buy_order():
    return Order(
        side=OrderType.BUY,
        price=decimal.Decimal("100"),
        quantity=decimal.Decimal("10"),
    )


@pytest.fixture
def sell_order():
    return Order(
        side=OrderType.SELL,
        price=decimal.Decimal("100"),
        quantity=decimal.Decimal("10"),
    )


@pytest.fixture
def sell_order_higher_price():
    return Order(
        side=OrderType.SELL,
        price=decimal.Decimal("105"),
        quantity=decimal.Decimal("10"),
    )


@pytest.fixture
def buy_order_higher_price():
    return Order(
        side=OrderType.BUY,
        price=decimal.Decimal("105"),
        quantity=decimal.Decimal("10"),
    )


@pytest.fixture
def sell_order_lower_price():
    return Order(
        side=OrderType.SELL,
        price=decimal.Decimal("95"),
        quantity=decimal.Decimal("10"),
    )


@pytest.fixture
def buy_order_lower_price():
    return Order(
        side=OrderType.BUY,
        price=decimal.Decimal("95"),
        quantity=decimal.Decimal("10"),
    )


def test_order_creation(buy_order):
    assert buy_order.side == OrderType.BUY
    assert buy_order.price == decimal.Decimal("100")
    assert buy_order.quantity == decimal.Decimal("10")
    assert buy_order.status == OrderStatus.OPEN
    assert len(buy_order.fills) == 0
    assert isinstance(buy_order.timestamp, datetime)


def test_order_size(buy_order):
    assert buy_order.size == (buy_order.price * buy_order.quantity)


def test_order_cancel(buy_order):
    buy_order.cancel()
    assert buy_order.status == OrderStatus.CANCELED


def test_order_comparison_buy(buy_order, buy_order_higher_price, buy_order_lower_price):
    assert not buy_order < buy_order_higher_price
    assert buy_order < buy_order_lower_price


def test_order_comparison_sell(sell_order_lower_price, sell_order_higher_price):
    assert sell_order_lower_price < sell_order_higher_price


def test_order_matches(buy_order, sell_order, sell_order_higher_price):
    assert buy_order.matches(sell_order)
    assert not buy_order.matches(sell_order_higher_price)
    assert not sell_order.matches(sell_order_higher_price)
    assert not buy_order.matches(buy_order)


def test_fill(buy_order, sell_order):
    fill = buy_order.fill(sell_order)

    # Check the fill details
    assert fill is not None
    assert fill.quantity == decimal.Decimal("10")
    assert fill.price == decimal.Decimal("100")
    assert fill.buy_id == buy_order.id
    assert fill.sell_id == sell_order.id
    assert isinstance(fill.timestamp, datetime)

    # Check the updated order quantities
    assert buy_order.quantity == decimal.Decimal("0")
    assert sell_order.quantity == decimal.Decimal("0")

    # Check the order statuses
    assert buy_order.status == OrderStatus.FILLED
    assert sell_order.status == OrderStatus.FILLED

    # Check that the fills were added to the orders
    assert len(buy_order.fills) == 1
    assert len(sell_order.fills) == 1
    assert buy_order.fills[0] == fill
    assert sell_order.fills[0] == fill


def test_no_fill_if_not_matching(buy_order, sell_order_higher_price):
    fill = buy_order.fill(sell_order_higher_price)

    assert fill is None
    assert buy_order.quantity == decimal.Decimal("10")
    assert sell_order_higher_price.quantity == decimal.Decimal("10")
    assert buy_order.status == OrderStatus.OPEN
    assert sell_order_higher_price.status == OrderStatus.OPEN


def test_partial_fill(buy_order):
    # Create an incoming order with a smaller quantity
    incoming_order = Order(
        side=OrderType.SELL,
        price=decimal.Decimal("100"),
        quantity=decimal.Decimal("5"),
    )

    fill = buy_order.fill(incoming_order)

    # Check the fill details
    assert fill is not None
    assert fill.quantity == decimal.Decimal("5")
    assert fill.price == decimal.Decimal("100")
    assert fill.buy_id == buy_order.id
    assert fill.sell_id == incoming_order.id

    # Check the updated order quantities
    assert buy_order.quantity == decimal.Decimal("5")
    assert incoming_order.quantity == decimal.Decimal("0")

    # Check the order statuses
    assert buy_order.status == OrderStatus.OPEN
    assert incoming_order.status == OrderStatus.FILLED

    # Check that the fills were added to the orders
    assert len(buy_order.fills) == 1
    assert len(incoming_order.fills) == 1
    assert buy_order.fills[0] == fill
    assert incoming_order.fills[0] == fill

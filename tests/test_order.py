import pytest
from unittest.mock import patch
import decimal
import uuid
import datetime
from litebook.order import Order, OrderType


@pytest.fixture
def buy_order():
    """Fixture for a sample BUY order."""
    return Order(
        side=OrderType.BUY,
        price=decimal.Decimal("100.00"),
        quantity=decimal.Decimal("10"),
    )


@pytest.fixture
def sell_order():
    """Fixture for a sample SELL order."""
    return Order(
        side=OrderType.SELL,
        price=decimal.Decimal("105.00"),
        quantity=decimal.Decimal("5"),
    )


def test_order_initialization(buy_order):
    """Test initialization of the Order class."""
    assert buy_order.side == OrderType.BUY
    assert buy_order.price == decimal.Decimal("100.00")
    assert buy_order.quantity == decimal.Decimal("10")
    assert isinstance(buy_order.id, uuid.UUID)
    assert isinstance(buy_order.timestamp, datetime.datetime)


def test_order_initialization_invalid_price():
    """Test initialization with invalid price (zero or negative)."""
    with pytest.raises(AssertionError):
        Order(OrderType.BUY, price=decimal.Decimal("0"), quantity=decimal.Decimal("10"))

    with pytest.raises(AssertionError):
        Order(
            OrderType.BUY, price=decimal.Decimal("-10"), quantity=decimal.Decimal("10")
        )


def test_order_initialization_invalid_quantity():
    """Test initialization with invalid quantity (zero or negative)."""
    with pytest.raises(AssertionError):
        Order(
            OrderType.BUY, price=decimal.Decimal("100"), quantity=decimal.Decimal("0")
        )

    with pytest.raises(AssertionError):
        Order(
            OrderType.BUY, price=decimal.Decimal("100"), quantity=decimal.Decimal("-5")
        )


@patch("datetime.datetime")
def test_order_timestamp(mock_datetime):
    """Test that the timestamp is correctly set during initialization."""
    mock_datetime.now.return_value = datetime.datetime(2023, 1, 1, tzinfo=datetime.UTC)
    mock_datetime.UTC = datetime.timezone.utc  # Mocking datetime.UTC

    order = Order(
        OrderType.BUY, price=decimal.Decimal("100"), quantity=decimal.Decimal("10")
    )
    assert order.timestamp == datetime.datetime(2023, 1, 1, tzinfo=datetime.UTC)


def test_order_value(buy_order):
    """Test the value property of the Order class."""
    assert buy_order.value == decimal.Decimal("1000.00")  # 100 * 10


def test_order_lt_buy_priority():
    """Test the __lt__ method for BUY orders."""
    order1 = Order(
        OrderType.BUY, price=decimal.Decimal("101"), quantity=decimal.Decimal("5")
    )
    order2 = Order(
        OrderType.BUY, price=decimal.Decimal("100"), quantity=decimal.Decimal("5")
    )

    # Higher price should have higher priority
    assert order1 < order2


def test_order_lt_sell_priority():
    """Test the __lt__ method for SELL orders."""
    order1 = Order(
        OrderType.SELL, price=decimal.Decimal("99"), quantity=decimal.Decimal("5")
    )
    order2 = Order(
        OrderType.SELL, price=decimal.Decimal("100"), quantity=decimal.Decimal("5")
    )

    # Lower price should have higher priority for SELL
    assert order1 < order2


def test_order_lt_timestamp_priority():
    """Test the __lt__ method for orders with the same price."""
    order1 = Order(
        OrderType.BUY, price=decimal.Decimal("100"), quantity=decimal.Decimal("5")
    )
    order2 = Order(
        OrderType.BUY, price=decimal.Decimal("100"), quantity=decimal.Decimal("5")
    )

    # Mock timestamps for comparison
    with patch.object(
        order1, "timestamp", datetime.datetime(2023, 1, 1, tzinfo=datetime.UTC)
    ):
        with patch.object(
            order2, "timestamp", datetime.datetime(2023, 1, 2, tzinfo=datetime.UTC)
        ):
            assert order1 < order2  # Earlier timestamp should have higher priority


def test_order_str(buy_order):
    """Test the __str__ method."""
    assert str(buy_order).startswith("BUY 10 @ 100.00 [")


def test_order_matches():
    """Test the matches method."""
    buy_order = Order(
        OrderType.BUY, price=decimal.Decimal("100"), quantity=decimal.Decimal("5")
    )
    sell_order = Order(
        OrderType.SELL, price=decimal.Decimal("90"), quantity=decimal.Decimal("5")
    )

    assert buy_order.matches(sell_order)  # BUY price >= SELL price


def test_order_matches_no_match():
    """Test the matches method with no match."""
    buy_order = Order(
        OrderType.BUY, price=decimal.Decimal("80"), quantity=decimal.Decimal("5")
    )
    sell_order = Order(
        OrderType.SELL, price=decimal.Decimal("90"), quantity=decimal.Decimal("5")
    )

    assert not buy_order.matches(sell_order)  # BUY price < SELL price
    assert not sell_order.matches(buy_order)  # SELL price > BUY price

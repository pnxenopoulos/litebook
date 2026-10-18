"""Regressions for matching identity, validation, and order lifecycle rules."""

import math

import litebook as lb
import pytest


@pytest.mark.parametrize("resting_side", [lb.OrderType.Buy, lb.OrderType.Sell])
def test_fill_ids_follow_sides(resting_side):
    book = lb.OrderBook(tick_size=0.25)
    buy = book.create_order(lb.OrderType.Buy, 10.5, 3.0)
    sell = book.create_order(lb.OrderType.Sell, 10.0, 2.0)
    resting, incoming = (buy, sell) if resting_side == lb.OrderType.Buy else (sell, buy)
    book.add(resting)
    fill = book.add(incoming)[0]
    assert (fill.buy_id, fill.sell_id) == (buy.id, sell.id)
    assert fill.price == 10.0  # Preserve the established seller-limit policy.
    assert fill.quantity == 2.0


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_invalid_tick_sizes(value):
    with pytest.raises(ValueError, match="tick_size"):
        lb.OrderBook(tick_size=value)


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_invalid_quantities(value):
    with pytest.raises(ValueError, match="quantity"):
        lb.Order(lb.OrderType.Buy, 10, value)
    with pytest.raises(ValueError):
        lb.OrderBook().create_order(lb.OrderType.Buy, 10.0, value)


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_invalid_prices(value):
    with pytest.raises(ValueError):
        lb.OrderBook().create_order(lb.OrderType.Buy, value, 1.0)


@pytest.mark.parametrize("price", [0.49, float(2**63), 1e300])
def test_tick_conversion_rejects_zero_or_out_of_range(price):
    with pytest.raises(ValueError):
        lb.OrderBook(tick_size=1.0).create_order(lb.OrderType.Buy, price, 1.0)


def test_tick_conversion_near_i64_boundary():
    price = math.nextafter(float(2**63), 0.0)
    order = lb.OrderBook(tick_size=1.0).create_order(lb.OrderType.Buy, price, 1.0)
    assert order.price_in_ticks == int(price)
    assert (
        lb.OrderBook(tick_size=1.0)
        .create_order(lb.OrderType.Buy, 1.5, 1.0)
        .price_in_ticks
        == 2
    )


@pytest.mark.parametrize("value", [0.0, -1.0, math.nan, math.inf, -math.inf, 1e308])
def test_invalid_fill_price_does_not_mutate_orders(value):
    buy = lb.Order(lb.OrderType.Buy, 10, 2.0)
    sell = lb.Order(lb.OrderType.Sell, 10, 1.0)
    with pytest.raises(ValueError):
        buy.fill(sell, value)
    assert buy.quantity == 2.0 and sell.quantity == 1.0
    assert buy.status == sell.status == lb.OrderStatus.Open


def test_unrepresentable_price_is_rejected_before_book_mutation():
    book = lb.OrderBook(tick_size=1e308)
    order = lb.Order(lb.OrderType.Buy, 10, 1.0)
    with pytest.raises(ValueError):
        book.add(order)
    assert book.buy_orders == []
    assert book.get_order(order.id) is None


def test_duplicate_submission_leaves_book_unchanged():
    book = lb.OrderBook()
    order = book.create_order(lb.OrderType.Buy, 10.0, 2.0)
    book.add(order)
    with pytest.raises(ValueError, match="already"):
        book.add(order)
    assert [o.id for o in book.buy_orders] == [order.id]
    assert book.get_order(order.id).quantity == 2.0


def test_filled_id_cannot_be_resubmitted_or_canceled():
    book = lb.OrderBook()
    buy = book.create_order(lb.OrderType.Buy, 10.0, 1.0)
    sell = book.create_order(lb.OrderType.Sell, 10.0, 1.0)
    book.add(buy)
    book.add(sell)
    with pytest.raises(ValueError, match="already"):
        book.add(buy)  # The detached original still says Open.
    assert not book.cancel(buy.id)
    assert book.get_order(buy.id).status == lb.OrderStatus.Filled


def test_completed_orders_cannot_match_fill_or_enter_book():
    buy = lb.Order(lb.OrderType.Buy, 10, 1.0)
    sell = lb.Order(lb.OrderType.Sell, 10, 1.0)
    assert buy.fill(sell, 1.0).quantity == 1.0
    other = lb.Order(lb.OrderType.Sell, 10, 1.0)
    assert not buy.can_match(other)
    assert not other.can_match(buy)
    assert buy.fill(other, 1.0) is None
    assert other.quantity == 1.0
    with pytest.raises(ValueError, match="open"):
        lb.OrderBook(tick_size=1.0).add(buy)


def test_cancel_is_idempotent():
    book = lb.OrderBook()
    order = book.create_order(lb.OrderType.Buy, 10.0, 1.0)
    book.add(order)
    assert book.cancel(order.id)
    assert not book.cancel(order.id)
    assert book.buy_orders == []


@pytest.mark.parametrize("side", [lb.OrderType.Buy, lb.OrderType.Sell])
def test_fifo_after_partial_fill_and_middle_cancellation(side):
    book = lb.OrderBook(tick_size=1.0)
    opposite = lb.OrderType.Sell if side == lb.OrderType.Buy else lb.OrderType.Buy
    orders = [book.create_order(side, 10.0, 2.0) for _ in range(3)]
    for order in orders:
        book.add(order)
    first = book.add(book.create_order(opposite, 10.0, 1.0))[0]
    maker_id = first.buy_id if side == lb.OrderType.Buy else first.sell_id
    assert maker_id == orders[0].id
    assert book.cancel(orders[1].id)
    fills = book.add(book.create_order(opposite, 10.0, 3.0))
    assert [
        (f.buy_id if side == lb.OrderType.Buy else f.sell_id, f.quantity) for f in fills
    ] == [(orders[0].id, 1.0), (orders[2].id, 2.0)]
    assert book.buy_orders == book.sell_orders == []


def test_repr_preserves_fractional_prices():
    book = lb.OrderBook(tick_size=0.05)
    book.add(book.create_order(lb.OrderType.Buy, 10.05, 1.0))
    book.add(book.create_order(lb.OrderType.Sell, 10.10, 1.0))
    assert "1.00 @ 10.05" in repr(book)
    assert "1.00 @ 10.1" in repr(book)


def test_rounding_cannot_create_an_infinite_reporting_price():
    with pytest.raises(ValueError):
        lb.OrderBook(tick_size=1e308).create_order(lb.OrderType.Buy, 1.7e308, 1.0)

"""Module to benchmark order maching"""

import time
import random
import decimal

import litebook.book
import litebook.order


def benchmark_order_book_matching(
    initial_orders: int = 1000, benchmark_orders: int = 1_000_000
) -> None:
    """
    Benchmarks the OrderBook class by simulating order processing.

    Args:
        initial_orders (int): Total number of orders to seed the book.
        benchmark_orders (int): Total number of orders to process.

    Returns:
        None
    """
    order_book = litebook.book.OrderBook()

    # Generate initial set of 1000
    for _ in range(initial_orders):
        price = decimal.Decimal(random.randint(1, 10))
        quantity = decimal.Decimal(random.randint(1, 10))
        order_type = random.choice(
            [litebook.order.OrderType.BUY, litebook.order.OrderType.SELL]
        )
        order_book.add(litebook.order.Order(order_type, price, quantity))  # type: ignore

    # Benchmark new orders. Only time the order matching (from .add())
    total_time = 0.0
    for _ in range(benchmark_orders):
        price = decimal.Decimal(random.randint(50, 150))
        quantity = decimal.Decimal(random.randint(1, 10))
        order_type = random.choice(
            [litebook.order.OrderType.BUY, litebook.order.OrderType.SELL]
        )
        order = litebook.order.Order(order_type, price, quantity)  # type: ignore
        start_time = time.time()
        order_book.add(order)
        total_time += time.time() - start_time

    orders_per_second = benchmark_orders / total_time
    print(f"Processed {benchmark_orders} orders in {total_time:.2f} seconds.")
    print(f"Orders per second: {orders_per_second:.2f}")

"""
Module for benchmarking the litebook.OrderBook class.

This script benchmarks the performance of the `OrderBook.add()` method by simulating
the addition of a large number of pre-generated orders.

The benchmark evaluates:
1. Initialization of the order book with a specified number of seed orders.
2. Speed of processing orders via the `.add()` method.

Each benchmark measures:
- Total execution time in seconds for `.add()` calls.
- Average orders processed per second.

Usage:
Run the script directly to execute the benchmark and print the results.

    python benchmark_order_book.py
"""

import decimal
import random
import time

from litebook import Order, OrderBook, OrderType


def generate_orders(num_orders: int, price_range: tuple[int, int]) -> list[Order]:
    """Generate a list of random orders for benchmarking.

    Args:
        num_orders (int): Number of orders to generate.
        price_range (tuple[int, int]): Range of prices for the orders.

    Returns:
        list[Order]: A list of generated Order objects.
    """
    orders = []
    for _ in range(num_orders):
        price = random.randint(*price_range)
        quantity = random.randint(1, 10)
        order_type = random.choice([OrderType.Buy, OrderType.Sell])
        orders.append(Order(order_type, price, quantity))
    return orders


def benchmark_order_book_matching(
    initial_orders: int = 1000, benchmark_orders: int = 1_000_000
):
    """Benchmark the OrderBook.add() method with pre-generated orders.

    Args:
        initial_orders (int): Total number of orders to seed the book.
        benchmark_orders (int): Total number of orders to process.
    """
    print(
        f"Seeding OrderBook with {initial_orders} initial orders "
        f"and processing {benchmark_orders} additional orders....\n"
    )

    # Initialize the OrderBook instance
    order_book = OrderBook()

    # Seed the order book with initial orders
    seed_orders = generate_orders(initial_orders, (1, 10))
    for order in seed_orders:
        order_book.add(order)

    # Generate benchmark orders
    benchmark_orders_list = generate_orders(benchmark_orders, (50, 150))

    # Benchmark only the .add() calls
    start_time = time.time()
    for order in benchmark_orders_list:
        order_book.add(order)
    total_time = time.time() - start_time

    # Calculate and print results
    orders_per_second = benchmark_orders / total_time
    print(f"Processed {benchmark_orders} orders in {total_time:.2f} seconds.")
    print(f"Orders per second: {orders_per_second:.2f}\n")


if __name__ == "__main__":
    print("Benchmarking litebook.OrderBook performance:\n")
    benchmark_order_book_matching()

"""
Module for benchmarking the litebook.Order class.

This script provides performance benchmarks for key functionalities of the `Order` class.
The benchmarks evaluate:

1. Order Initialization:
   Measures the time taken to create new orders through the OrderBook.
2. Order Matching:
   Tests the efficiency of the internal can_match method, which determines if two orders
   can match for a trade.
3. Order Filling:
   Benchmarks the fill method, which processes matches between compatible orders.

Each benchmark runs a specified number of iterations and reports:
- Total execution time in seconds.
- Average time per call in microseconds (µs).

Usage:
Run the script directly to execute all benchmarks and print the results.

    python benchmark_order.py
"""

import timeit


def benchmark_order_initialization():
    """
    Benchmark the initialization of Order objects. Note that orders must now be created
    through an OrderBook since price conversion is handled at that level.
    """
    setup = """
from litebook import OrderBook, OrderType
book = OrderBook()  # Uses default tick_size of 0.01
"""
    # Creating an order now goes through the OrderBook
    stmt = "book.create_order(OrderType.Buy, 100.50, 10.0)"
    executions = 10000

    total_time = timeit.timeit(stmt, setup=setup, number=executions)
    print(
        f"Order initialization: {total_time:.4f} seconds for {executions} executions."
    )
    print(f"Time per call: {total_time / executions * 1e6:.2f} μs")
    print("\n")


def benchmark_order_matching():
    """
    Benchmark the internal can_match method of the Order class, which determines
    if two orders are compatible for trading based on their tick prices.
    """
    setup = """
from litebook import OrderBook, OrderType
book = OrderBook()  # Uses default tick_size of 0.01
buy_order = book.create_order(OrderType.Buy, 100.50, 10.0)
sell_order = book.create_order(OrderType.Sell, 100.40, 5.0)
"""
    # We need to use the internal can_match method since it's what the OrderBook uses
    stmt = "buy_order.can_match(sell_order)"
    executions = 100000

    total_time = timeit.timeit(stmt, setup=setup, number=executions)
    print(f"Order matching: {total_time:.4f} seconds for {executions} executions.")
    print(f"Time per call: {total_time / executions * 1e6:.2f} μs")
    print("\n")


def benchmark_order_fill():
    """
    Benchmark the fill method of the Order class, which processes a match between
    two compatible orders and generates a Fill event.
    """
    setup = """
from litebook import OrderBook, OrderType
book = OrderBook()  # Uses default tick_size of 0.01
buy_order = book.create_order(OrderType.Buy, 100.50, 10.0)
sell_order = book.create_order(OrderType.Sell, 100.40, 5.0)
"""
    # Note that fill now requires the tick_size parameter
    stmt = "buy_order.fill(sell_order, 0.01)"
    executions = 100000

    total_time = timeit.timeit(stmt, setup=setup, number=executions)
    print(f"Order filling: {total_time:.4f} seconds for {executions} executions.")
    print(f"Time per call: {total_time / executions * 1e6:.2f} μs")
    print("\n")


def run_all_benchmarks():
    """Run all benchmarks and print results with clear separation."""
    print("Benchmarking litebook.Order performance:\n")
    print("=" * 60)
    print("1. Order Initialization Benchmark")
    print("-" * 60)
    benchmark_order_initialization()

    print("2. Order Matching Benchmark")
    print("-" * 60)
    benchmark_order_matching()

    print("3. Order Fill Benchmark")
    print("-" * 60)
    benchmark_order_fill()


if __name__ == "__main__":
    run_all_benchmarks()

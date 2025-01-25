"""
Module for benchmarking the litebook.order.Order class.

This script provides performance benchmarks for key functionalities of the `Order` class
in the `litebook.order` module. The benchmarks include:

1. Order Initialization:
   Measures the time taken to initialize Order objects.
2. Order Comparison (__lt__):
   Evaluates the performance of the comparison method for sorting and prioritization.
3. Order Matching:
   Tests the efficiency of the `matches` method, which determines if two orders are compatible for a trade.
4. Order Filling:
   Benchmarks the `fill` method, which adjusts quantities and creates fills between matching orders.

Each benchmark runs a specified number of iterations and reports:
- Total execution time in seconds.
- Average time per call in microseconds (µs).

Usage:
Run the script directly to execute all benchmarks and print the results.

    python benchmark_order.py
"""

import timeit


def benchmark_order_initialization():
    """Benchmark the initialization of Order objects."""
    setup = "from litebook.order import Order, OrderType; import decimal"
    stmt = "Order(OrderType.BUY, decimal.Decimal('100.00'), decimal.Decimal('10.00'))"
    executions = 10000
    total_time = timeit.timeit(stmt, setup=setup, number=executions)
    print(
        f"Order initialization: {total_time:.4f} seconds for {executions} executions."
    )
    print(f"Time per call: {total_time / executions * 1e6:.2f} μs")
    print("\n")


def benchmark_order_comparison():
    """Benchmark the __lt__ method of the Order class."""
    setup = (
        "from litebook import Order, OrderType; "
        "import decimal; "
        "order1 = Order(OrderType.BUY,100.00, 10.00); "
        "order2 = Order(OrderType.SELL, 90.00, 5.00)"
    )
    stmt = "order1 < order2"
    executions = 100000
    total_time = timeit.timeit(stmt, setup=setup, number=executions)
    print(f"Order comparison: {total_time:.4f} seconds for {executions} executions.")
    print(f"Time per call: {total_time / executions * 1e6:.2f} μs")
    print("\n")


def benchmark_order_matching():
    """Benchmark the matches method of the Order class."""
    setup = (
        "from litebook import Order, OrderType; "
        "buy_order = Order(OrderType.BUY,100.00, 10.00); "
        "sell_order = Order(OrderType.SELL, 90.00, 5.00)"
    )
    stmt = "buy_order.matches(sell_order)"
    executions = 100000
    total_time = timeit.timeit(stmt, setup=setup, number=executions)
    print(f"Order matching: {total_time:.4f} seconds for {executions} executions.")
    print(f"Time per call: {total_time / executions * 1e6:.2f} μs")
    print("\n")


def benchmark_order_fill():
    """Benchmark the fill method of the Order class."""
    setup = (
        "from litebook import Order, OrderType; "
        "import decimal; "
        "buy_order = Order(OrderType.BUY,100.00, 10.00); "
        "sell_order = Order(OrderType.SELL, 90.00, 5.00)"
    )
    stmt = "buy_order.fill(sell_order)"
    executions = 100000
    total_time = timeit.timeit(stmt, setup=setup, number=executions)
    print(f"Order filling: {total_time:.4f} seconds for {executions} executions.")
    print(f"Time per call: {total_time / executions * 1e6:.2f} μs")
    print("\n")


if __name__ == "__main__":
    print("Benchmarking litebook.order.Order performance:\n")
    benchmark_order_initialization()
    benchmark_order_comparison()
    benchmark_order_matching()
    benchmark_order_fill()

# litebook

[![litebook Downloads](https://static.pepy.tech/personalized-badge/litebook?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/litebook) [![Build](https://github.com/pnxenopoulos/litebook/actions/workflows/build.yml/badge.svg)](https://github.com/pnxenopoulos/litebook/actions/workflows/build.yml) [![MIT License](https://img.shields.io/badge/license-MIT-lightgrey)](https://github.com/pnxenopoulos/litebook/blob/main/LICENSE)

A fast and performant limit order book in Python utilizing a Rust backend. Install it with

```shell
pip install litebook
```

## Using litebook
Get started with litebook using the following example:

```python
import litebook as lb

# Create an OrderBook
orderbook = lb.OrderBook(tick_size=0.01)

# Create some orders (this not _add_ the order!)
buy_order = book.create_order(lb.OrderType.Buy, price=10.05, quantity=10.0)
sell_order = book.create_order(lb.OrderType.Sell, price=10.05, quantity=5.0)

# Add the orders (this returns a list of Fill objects)
_no_fills = book.add(buy_order)
fills = book.add(sell_order)

# Check the fill
print(fill)

# Check the status of the remainder of the open buy order
# DO NOT rely on the previous `buy_order` or `sell_order` objects
# to be updated! Fetch them from the book, instead
open_buy_order = orderbook.get_order(buy_order.id)
```
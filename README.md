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

Matching and lifecycle rules are documented in [docs/semantics.md](docs/semantics.md).

## Development

Install Rust and [uv](https://docs.astral.sh/uv/), then rebuild the release
extension and run its Python tests from this checkout:

```shell
bash scripts/rebuild.sh
```

The script installs development tools from `uv.lock`, builds with `Cargo.lock`,
prints the imported native extension path, and runs tests only after the build
succeeds. Run it again after changing Rust code. Pass pytest options through the
script, for example `bash scripts/rebuild.sh -q`.

See [benchmarks/README.md](benchmarks/README.md) for native and Python baseline commands.

Rust tools can run without the extension feature; Maturin enables it for Python
builds. Track the review sequence and validation in [REFACTOR_PLAN.md](REFACTOR_PLAN.md).

#### Need help?
Please [open an issue](https://github.com/pnxenopoulos/litebook/issues) if you need help or have a feature request.
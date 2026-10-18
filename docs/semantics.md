# Order book behavior

Stage one preserves the existing matching policy while enforcing valid inputs and
consistent order lifecycles. These rules define the benchmark and reference-model contract.

## Matching and quantities

Orders match opposite-side orders when the buy limit is at least the sell limit.
The best opposing price executes first, with FIFO priority within each price level.
A partial fill keeps the resting order at the front of its queue.

The execution price is the seller's limit price, including when the seller is the
incoming order. This preserves the original behavior; switching to resting-order
pricing requires a separate compatibility decision.

Prices and quantities must be positive and finite. Tick size must also be positive
and finite. Price conversion rounds to the nearest tick, with positive half-ticks
rounded up, and rejects results outside positive i64 ticks or with a non-finite
reporting price. Quantities remain binary floating point in this stage.

## Submission and cancellation

An order must be open to enter a book. Submitting an ID that is already known to
that book raises ValueError before changing book state. Filled orders remain
available through get_order and cannot be resubmitted or canceled.

Cancellation removes an open order from the queue and the lookup map. Canceling a
missing, already canceled, or filled order returns false. Since canceled IDs are
not retained, submitting a detached original again after cancellation is allowed.
Permanent ID uniqueness would require a separate retention policy.

## Python snapshots

create_order creates a detached order. add copies it into book state; the original
Python object does not reflect later fills or cancellation. get_order and the
buy_orders and sell_orders properties return detached snapshots as well.

The public Order.fill operation changes only its two supplied objects. It returns
None for completed or incompatible orders, and rejects an invalid tick size or
non-finite execution price before changing either object. Index maintenance remains
internal to OrderBook and is not exposed as a Python mutation method.

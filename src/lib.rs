use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use std::collections::{BTreeMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

/// Enum for order side
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Buy,
    Sell,
}

/// Enum for order status
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    Open,
    Filled,
    Canceled,
}

/// A fill event records how two orders matched.
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fill {
    quantity: f64,
    price: f64, // We'll store the fill price as a float for reporting.
    buy_id: String,
    sell_id: String,
    timestamp: u64, // Nanoseconds since the Unix epoch
}

#[pymethods]
impl Fill {
    #[new]
    pub fn new(quantity: f64, price: f64, buy_id: String, sell_id: String, timestamp: u64) -> Self {
        Self {
            quantity,
            price,
            buy_id,
            sell_id,
            timestamp,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "[{:.2} @ {:.2}] Buy: {}, Sell: {}, Filled at {}",
            self.quantity, self.price, self.buy_id, self.sell_id, self.timestamp
        )
    }

    #[getter]
    pub fn quantity(&self) -> f64 {
        self.quantity
    }

    #[getter]
    pub fn price(&self) -> f64 {
        self.price
    }

    #[getter]
    pub fn buy_id(&self) -> &str {
        &self.buy_id
    }

    #[getter]
    pub fn sell_id(&self) -> &str {
        &self.sell_id
    }

    #[getter]
    pub fn timestamp(&self) -> u64 {
        self.timestamp
    }
}

/// An Order.  
/// **Important**: We store `price_in_ticks` (i64) instead of a float price.  
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    id: String,
    side: OrderType,
    price_in_ticks: i64,
    quantity: f64,
    status: OrderStatus,
    timestamp: u64,
}

#[pymethods]
impl Order {
    /// Create a new order with a price in ticks
    #[new]
    pub fn new(side: OrderType, price_in_ticks: i64, quantity: f64) -> PyResult<Self> {
        // Validate the inputs
        if price_in_ticks <= 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "price_in_ticks must be positive",
            ));
        }
        if quantity <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "quantity must be positive",
            ));
        }

        let id = Uuid::new_v4().to_string();
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("Time went backwards")
            .as_nanos() as u64;

        Ok(Self {
            id,
            side,
            price_in_ticks,
            quantity,
            status: OrderStatus::Open,
            timestamp: now,
        })
    }

    /// Check if this order can match with another order.
    /// Returns true if:
    /// 1. The orders are on opposite sides (buy vs sell)
    /// 2. The buy price is greater than or equal to the sell price
    #[pyo3(text_signature = "(self, other)")]
    pub fn can_match(&self, other: &Order) -> bool {
        if self.side == other.side {
            return false;
        }
        match self.side {
            // A buy matches if its price_in_ticks >= the sell's price_in_ticks
            OrderType::Buy => self.price_in_ticks >= other.price_in_ticks,
            // A sell matches if its price_in_ticks <= the buy's price_in_ticks
            OrderType::Sell => self.price_in_ticks <= other.price_in_ticks,
        }
    }

    /// Attempt to fill `self` with `incoming`. Returns Some(Fill) if a fill occurred.
    fn fill(&mut self, incoming: &mut Order, tick_size: f64) -> Option<Fill> {
        if !self.can_match(incoming) {
            return None;
        }

        // Determine how much we can fill
        let fill_quantity = self.quantity.min(incoming.quantity);

        // Decrement the quantities
        self.quantity -= fill_quantity;
        incoming.quantity -= fill_quantity;

        // Mark orders as filled if quantity hits zero
        if self.quantity <= 0.0 {
            self.status = OrderStatus::Filled;
        }
        if incoming.quantity <= 0.0 {
            incoming.status = OrderStatus::Filled;
        }

        // By convention: if the resting order is a sell, use its price_in_ticks;
        // otherwise use the incoming's price_in_ticks.
        let final_ticks = if self.side == OrderType::Sell {
            self.price_in_ticks
        } else {
            incoming.price_in_ticks
        };

        let fill_price = (final_ticks as f64) * tick_size;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("Time went backwards")
            .as_nanos() as u64;

        Some(Fill::new(
            fill_quantity,
            fill_price,
            self.id.clone(),
            incoming.id.clone(),
            now,
        ))
    }

    fn is_open(&self) -> bool {
        self.status == OrderStatus::Open
    }

    fn __repr__(&self) -> String {
        // Convert price from ticks to actual price
        format!(
            "[{:?} {} @ {}] [{}, placed at {}]",
            self.side, self.quantity, self.price_in_ticks, self.id, self.timestamp
        )
    }

    /// Getters for Python
    #[getter]
    pub fn id(&self) -> &str {
        &self.id
    }

    #[getter]
    pub fn side(&self) -> OrderType {
        self.side.clone()
    }

    #[getter]
    pub fn price_in_ticks(&self) -> i64 {
        self.price_in_ticks
    }

    #[getter]
    pub fn quantity(&self) -> f64 {
        self.quantity
    }

    #[getter]
    pub fn status(&self) -> OrderStatus {
        self.status.clone()
    }

    #[getter]
    pub fn timestamp(&self) -> u64 {
        self.timestamp
    }
}

/// A container for the OrderBook, keyed by integer ticks (i64).
/// We do immediate matching in `add(...)`.
#[pyclass]
pub struct OrderBook {
    buy_orders: BTreeMap<i64, VecDeque<Order>>,
    sell_orders: BTreeMap<i64, VecDeque<Order>>,
    tick_size: f64,
}

#[pymethods]
impl OrderBook {
    /// Create a new book with a given tick size. For example, if tick_size=0.01,
    /// then a price of 123.45 is stored as 12345 ticks.
    #[new]
    #[pyo3(text_signature = "($self, *, tick_size=0.01)")]
    pub fn new(tick_size: f64) -> Self {
        Self {
            buy_orders: BTreeMap::new(),
            sell_orders: BTreeMap::new(),
            tick_size,
        }
    }

    /// Create a new order in this book given a float price.
    /// This handles converting the float price to ticks using this book's tick_size.
    #[pyo3(text_signature = "(self, side, price, quantity)")]
    pub fn create_order(&self, side: OrderType, price: f64, quantity: f64) -> PyResult<Order> {
        if price <= 0.0 || quantity <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Price and quantity must be positive",
            ));
        }

        let price_in_ticks = (price / self.tick_size).round() as i64;
        if price_in_ticks <= 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Resulting price_in_ticks must be positive",
            ));
        }

        Order::new(side, price_in_ticks, quantity)
    }

    /// Add an existing Order (already constructed) and immediately attempt to match it.
    /// Returns a list of Fills that occurred.
    ///
    /// For example, from Python:
    ///
    ///     order = Order(OrderType.Buy, 100.5, 10.0, 0.01)
    ///     fills = orderbook.add(order)
    ///
    #[pyo3(text_signature = "(self, order)")]
    pub fn add(&mut self, incoming_order: &mut Order) -> PyResult<Vec<Fill>> {
        let mut fills = Vec::new();

        // Validate some basic sanity on the incoming order (optional):
        if incoming_order.price_in_ticks <= 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Order has invalid price_in_ticks <= 0",
            ));
        }
        if incoming_order.quantity <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Order has non-positive quantity",
            ));
        }

        // Match until the order is filled or no longer crosses
        match incoming_order.side {
            OrderType::Buy => {
                while incoming_order.is_open() {
                    let (best_sell_price, sell_queue) = match self.sell_orders.iter_mut().next() {
                        Some((k, q)) => (*k, q),
                        None => break,
                    };
                    if incoming_order.price_in_ticks < best_sell_price {
                        break;
                    }

                    let mut resting_sell = sell_queue
                        .pop_front()
                        .expect("Queue is not empty if it exists in map");

                    if let Some(fill) = resting_sell.fill(incoming_order, self.tick_size) {
                        fills.push(fill);
                    }

                    if resting_sell.is_open() {
                        sell_queue.push_front(resting_sell);
                    }

                    if sell_queue.is_empty() {
                        self.sell_orders.remove(&best_sell_price);
                    }
                }

                // Only store the order if it's still open
                if incoming_order.is_open() {
                    let price_ticks = incoming_order.price_in_ticks;
                    self.buy_orders
                        .entry(price_ticks)
                        .or_default()
                        .push_back(incoming_order.clone());
                }
            }

            OrderType::Sell => {
                while incoming_order.is_open() {
                    let (best_buy_price, buy_queue) = match self.buy_orders.iter_mut().next_back() {
                        Some((k, q)) => (*k, q),
                        None => break,
                    };
                    if incoming_order.price_in_ticks > best_buy_price {
                        break;
                    }

                    let mut resting_buy = buy_queue
                        .pop_front()
                        .expect("Queue is not empty if it exists in map");

                    if let Some(fill) = resting_buy.fill(incoming_order, self.tick_size) {
                        fills.push(fill);
                    }

                    // Update: Only push back if the order is still open
                    if resting_buy.is_open() {
                        buy_queue.push_front(resting_buy);
                    }

                    if buy_queue.is_empty() {
                        self.buy_orders.remove(&best_buy_price);
                    }
                }
            }
        }

        Ok(fills)
    }

    // Helper method to get best bid
    fn best_bid(&self) -> Option<(i64, f64)> {
        self.buy_orders.iter().next_back().map(|(price, queue)| {
            (
                *price,
                queue.front().map(|order| order.quantity).unwrap_or(0.0),
            )
        })
    }

    // Helper method to get best ask
    fn best_ask(&self) -> Option<(i64, f64)> {
        self.sell_orders.iter().next().map(|(price, queue)| {
            (
                *price,
                queue.front().map(|order| order.quantity).unwrap_or(0.0),
            )
        })
    }

    // Helper method to calculate total buy volume
    fn buy_volume(&self) -> f64 {
        self.buy_orders
            .values()
            .flat_map(|queue| queue.iter())
            .map(|order| order.quantity)
            .sum()
    }

    // Helper method to calculate total sell volume
    fn sell_volume(&self) -> f64 {
        self.sell_orders
            .values()
            .flat_map(|queue| queue.iter())
            .map(|order| order.quantity)
            .sum()
    }

    /// Calculate the current spread in the order book.
    /// Returns None if there are no orders on either side.
    /// The spread is returned in the same units as the prices (not ticks).
    #[pyo3(text_signature = "($self)")]
    fn spread(&self) -> Option<f64> {
        match (self.best_bid(), self.best_ask()) {
            (Some((bid_price, _)), Some((ask_price, _))) => {
                // Convert from tick difference to price difference
                let spread_in_ticks = ask_price - bid_price;
                Some(spread_in_ticks as f64 * self.tick_size)
            }
            _ => None,
        }
    }

    fn __repr__(&self) -> String {
        let best_bid = self
            .best_bid()
            .map(|(price, qty)| format!("{:.2} @ {}", qty, price * self.tick_size as i64))
            .unwrap_or_else(|| "None".to_string());

        let best_ask = self
            .best_ask()
            .map(|(price, qty)| format!("{:.2} @ {}", qty, price * self.tick_size as i64))
            .unwrap_or_else(|| "None".to_string());

        let spread = match (self.best_bid(), self.best_ask()) {
            (Some((bid, _)), Some((ask, _))) => {
                format!("{:.4}", (ask - bid) as f64 * self.tick_size)
            }
            _ => "None".to_string(),
        };

        format!(
            "Best Bid: {}, Best Ask: {} (Spread: {})\nOpen Buy Volume: {:.2}, Open Sell Volume: {:.2}",
            best_bid,
            best_ask,
            spread,
            self.buy_volume(),
            self.sell_volume()
        )
    }

    /// Return the tick size for informational purposes
    #[getter]
    pub fn tick_size(&self) -> f64 {
        self.tick_size
    }
}

impl Default for OrderBook {
    fn default() -> Self {
        Self::new(0.01)
    }
}

// Python module declaration
#[pymodule]
fn litebook(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Order>()?;
    m.add_class::<Fill>()?;
    m.add_class::<OrderBook>()?;
    m.add_class::<OrderType>()?;
    m.add_class::<OrderStatus>()?;
    Ok(())
}

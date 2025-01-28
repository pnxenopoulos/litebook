use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use std::collections::{BTreeMap, HashMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

/// Represents the side of an order: either Buy or Sell.
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Buy,
    Sell,
}

/// Represents the current status of an order.
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    Open,
    Filled,
    Canceled,
}

/// Represents a match (fill) between two orders.
/// Tracks details such as the quantity, price, and the involved order IDs.
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fill {
    quantity: f64,
    price: f64,      // Fill price as a float for reporting
    buy_id: String,  // ID of the buy order
    sell_id: String, // ID of the sell order
    timestamp: u64,  // Nanoseconds since the Unix epoch
}

#[pymethods]
impl Fill {
    /// Creates a new Fill record.
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

    /// Returns a string representation of the Fill.
    fn __repr__(&self) -> String {
        format!(
            "[{:.2} @ {:.2}] Buy: {}, Sell: {}, Filled at {}",
            self.quantity, self.price, self.buy_id, self.sell_id, self.timestamp
        )
    }

    /// Getter for the quantity filled.
    #[getter]
    pub fn quantity(&self) -> f64 {
        self.quantity
    }

    /// Getter for the fill price.
    #[getter]
    pub fn price(&self) -> f64 {
        self.price
    }

    /// Getter for the buy order ID.
    #[getter]
    pub fn buy_id(&self) -> &str {
        &self.buy_id
    }

    /// Getter for the sell order ID.
    #[getter]
    pub fn sell_id(&self) -> &str {
        &self.sell_id
    }

    /// Getter for the fill timestamp.
    #[getter]
    pub fn timestamp(&self) -> u64 {
        self.timestamp
    }
}

/// Represents a single order in the order book.
/// Contains details such as price, quantity, side (Buy/Sell), and status.
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    id: String,
    side: OrderType,
    price_in_ticks: i64, // Price stored as integer ticks
    quantity: f64,
    status: OrderStatus,
    timestamp: u64, // Nanoseconds since the Unix epoch
}

#[pymethods]
impl Order {
    /// Creates a new order.
    ///
    /// # Arguments
    /// - `side`: The side of the order (`Buy` or `Sell`).
    /// - `price_in_ticks`: The price in integer ticks (scaled by tick size).
    /// - `quantity`: The quantity of the order.
    ///
    /// # Errors
    /// - Returns an error if `price_in_ticks` or `quantity` is non-positive.
    #[new]
    pub fn new(side: OrderType, price_in_ticks: i64, quantity: f64) -> PyResult<Self> {
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

    /// Determines whether this order can match with another order.
    ///
    /// # Arguments
    /// - `other`: The other order to match against.
    ///
    /// # Returns
    /// - `true` if the orders are on opposite sides and the prices are compatible.
    #[pyo3(text_signature = "(self, other)")]
    pub fn can_match(&self, other: &Order) -> bool {
        if self.side == other.side {
            return false;
        }
        match self.side {
            OrderType::Buy => self.price_in_ticks >= other.price_in_ticks,
            OrderType::Sell => self.price_in_ticks <= other.price_in_ticks,
        }
    }

    /// Attempts to fill this order with another incoming order.
    /// Updates the quantities and statuses of both orders.
    fn fill(&mut self, incoming: &mut Order, tick_size: f64) -> Option<Fill> {
        if !self.can_match(incoming) {
            return None;
        }

        let fill_quantity = self.quantity.min(incoming.quantity);
        self.quantity -= fill_quantity;
        incoming.quantity -= fill_quantity;

        if self.quantity <= 0.0 {
            self.status = OrderStatus::Filled;
        }
        if incoming.quantity <= 0.0 {
            incoming.status = OrderStatus::Filled;
        }

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

    /// Checks if the order is still open.
    fn is_open(&self) -> bool {
        self.status == OrderStatus::Open
    }

    /// Returns a string representation of the order.
    fn __repr__(&self) -> String {
        format!(
            "[{:?} {} @ {}] [{}, placed at {}]",
            self.side, self.quantity, self.price_in_ticks, self.id, self.timestamp
        )
    }

    /// Getter for the order ID.
    #[getter]
    pub fn id(&self) -> &str {
        &self.id
    }

    /// Getter for the order side.
    #[getter]
    pub fn side(&self) -> OrderType {
        self.side.clone()
    }

    /// Getter for the price in ticks.
    #[getter]
    pub fn price_in_ticks(&self) -> i64 {
        self.price_in_ticks
    }

    /// Getter for the quantity.
    #[getter]
    pub fn quantity(&self) -> f64 {
        self.quantity
    }

    /// Getter for the order status.
    #[getter]
    pub fn status(&self) -> OrderStatus {
        self.status.clone()
    }

    /// Getter for the timestamp.
    #[getter]
    pub fn timestamp(&self) -> u64 {
        self.timestamp
    }
}

/// Represents the main order book for matching buy and sell orders.
#[pyclass]
pub struct OrderBook {
    buy_orders: BTreeMap<i64, VecDeque<Order>>, // Buy-side orders, keyed by price
    sell_orders: BTreeMap<i64, VecDeque<Order>>, // Sell-side orders, keyed by price
    orders: HashMap<String, Order>,             // Map of UUID -> Order for quick lookup
    tick_size: f64,                             // Tick size for price scaling
}

#[pymethods]
impl OrderBook {
    /// Creates a new OrderBook with a specified tick size.
    #[new]
    #[pyo3(signature = (tick_size=0.01))]
    pub fn new(tick_size: f64) -> Self {
        Self {
            buy_orders: BTreeMap::new(),
            sell_orders: BTreeMap::new(),
            orders: HashMap::new(),
            tick_size,
        }
    }

    /// Creates an order (but does not add to the book) based off the book's tick size.
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

    /// Adds an order to the book, attempting to match it with resting orders.
    #[pyo3(text_signature = "(self, order)")]
    pub fn add(&mut self, mut incoming_order: Order) -> PyResult<Vec<Fill>> {
        let mut fills = Vec::new();

        match incoming_order.side {
            OrderType::Buy => {
                while incoming_order.is_open() {
                    let (_best_sell_price, resting_sell) = {
                        // Restrict the mutable borrow of `sell_queue` to this block
                        let (best_sell_price, sell_queue) = match self.sell_orders.iter_mut().next()
                        {
                            Some((k, q)) => (*k, q),
                            None => break,
                        };

                        if incoming_order.price_in_ticks < best_sell_price {
                            break;
                        }

                        let mut resting_sell = sell_queue
                            .pop_front()
                            .expect("Queue is not empty if it exists in map");

                        // Process the fill
                        if let Some(fill) = resting_sell.fill(&mut incoming_order, self.tick_size) {
                            fills.push(fill);
                        }

                        // Push back the partially filled resting order, if necessary
                        if resting_sell.is_open() {
                            sell_queue.push_front(resting_sell.clone());
                        }

                        if sell_queue.is_empty() {
                            self.sell_orders.remove(&best_sell_price);
                        }

                        (best_sell_price, resting_sell)
                    };

                    // Update the resting sell order and incoming order in the `orders` map
                    self.update_order(&resting_sell);
                    self.update_order(&incoming_order);
                }

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
                    let (_best_buy_price, resting_buy) = {
                        // Restrict the mutable borrow of `buy_queue` to this block
                        let (best_buy_price, buy_queue) =
                            match self.buy_orders.iter_mut().next_back() {
                                Some((k, q)) => (*k, q),
                                None => break,
                            };

                        if incoming_order.price_in_ticks > best_buy_price {
                            break;
                        }

                        let mut resting_buy = buy_queue
                            .pop_front()
                            .expect("Queue is not empty if it exists in map");

                        // Process the fill
                        if let Some(fill) = resting_buy.fill(&mut incoming_order, self.tick_size) {
                            fills.push(fill);
                        }

                        // Push back the partially filled resting order, if necessary
                        if resting_buy.is_open() {
                            buy_queue.push_front(resting_buy.clone());
                        }

                        if buy_queue.is_empty() {
                            self.buy_orders.remove(&best_buy_price);
                        }

                        (best_buy_price, resting_buy)
                    };

                    // Update the resting buy order and incoming order in the `orders` map
                    self.update_order(&resting_buy);
                    self.update_order(&incoming_order);
                }

                if incoming_order.is_open() {
                    let price_ticks = incoming_order.price_in_ticks;
                    self.sell_orders
                        .entry(price_ticks)
                        .or_default()
                        .push_back(incoming_order.clone());
                }
            }
        }

        // Always ensure the incoming order is updated in `orders` at the end
        self.update_order(&incoming_order);

        Ok(fills)
    }

    /// Cancels an order by its ID.
    #[pyo3(text_signature = "(self, order_id)")]
    pub fn cancel(&mut self, order_id: &str) -> bool {
        // Use a scoped block to avoid overlapping mutable borrows
        let mut canceled_order = None;

        if let Some(order) = self.orders.get_mut(order_id) {
            // Mark the order as canceled
            order.status = OrderStatus::Canceled;

            // Determine which book to remove it from
            let target_book = match order.side {
                OrderType::Buy => &mut self.buy_orders,
                OrderType::Sell => &mut self.sell_orders,
            };

            // Find the specific price level queue
            if let Some(queue) = target_book.get_mut(&order.price_in_ticks) {
                // Remove the order from the queue
                queue.retain(|o| o.id != order.id);

                // Remove the price level if the queue is empty
                if queue.is_empty() {
                    target_book.remove(&order.price_in_ticks);
                }
            }

            // Take ownership of the modified order for updating outside the borrow
            canceled_order = Some(order.clone());
        }

        if let Some(order) = canceled_order {
            self.orders.remove(&order.id);
            return true; // Order successfully canceled
        }

        false // Order not found
    }

    /// Retrieves an order by its ID. Returns None if the order is not found.
    #[pyo3(text_signature = "(self, order_id)")]
    pub fn get_order(&self, order_id: &str) -> Option<Order> {
        self.orders.get(order_id).cloned()
    }

    /// Helper method to update an order in the `orders` map.
    fn update_order(&mut self, order: &Order) {
        self.orders.insert(order.id.clone(), order.clone());
    }

    /// Get a list of all buy orders
    #[getter]
    pub fn get_buy_orders(&self) -> Vec<Order> {
        self.buy_orders
            .values()
            .flat_map(|queue| queue.iter().cloned())
            .collect()
    }

    /// Get a list of all sell orders
    #[getter]
    pub fn get_sell_orders(&self) -> Vec<Order> {
        self.sell_orders
            .values()
            .flat_map(|queue| queue.iter().cloned())
            .collect()
    }

    /// Helper method to get best bid
    fn best_bid(&self) -> Option<(i64, f64)> {
        self.buy_orders.iter().next_back().map(|(price, queue)| {
            (
                *price,
                queue.front().map(|order| order.quantity).unwrap_or(0.0),
            )
        })
    }

    /// Helper method to get best ask
    fn best_ask(&self) -> Option<(i64, f64)> {
        self.sell_orders.iter().next().map(|(price, queue)| {
            (
                *price,
                queue.front().map(|order| order.quantity).unwrap_or(0.0),
            )
        })
    }

    /// Helper method to calculate total buy volume
    fn buy_volume(&self) -> f64 {
        self.buy_orders
            .values()
            .flat_map(|queue| queue.iter())
            .map(|order| order.quantity)
            .sum()
    }

    /// Helper method to calculate total sell volume
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

    /// Return the tick size for informational purposes
    #[getter]
    pub fn tick_size(&self) -> f64 {
        self.tick_size
    }

    /// Returns a string representation of the order book.
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

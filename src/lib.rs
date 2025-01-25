use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::time::{SystemTime, UNIX_EPOCH};

// Enum for order type
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderType {
    Buy,
    Sell,
}

// Enum for order status
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum OrderStatus {
    Open,
    Filled,
    Canceled,
}

// Fill structure
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fill {
    quantity: f64,
    price: f64,
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
}

// Order structure
#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Order {
    id: String,
    side: OrderType,
    price: f64,
    quantity: f64,
    status: OrderStatus,
    timestamp: u64, // Nanoseconds since the Unix epoch
}

#[pymethods]
impl Order {
    #[new]
    pub fn new(side: OrderType, price: f64, quantity: f64) -> PyResult<Self> {
        if price <= 0.0 || quantity <= 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Price and quantity must be positive",
            ));
        }

        let id = uuid::Uuid::new_v4().to_string();
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("Time went backwards")
            .as_nanos() as u64;

        Ok(Self {
            id,
            side,
            price,
            quantity,
            status: OrderStatus::Open,
            timestamp,
        })
    }

    #[getter]
    pub fn id(&self) -> &str {
        &self.id
    }

    #[getter]
    pub fn price(&self) -> &f64 {
        &self.price
    }

    #[getter]
    pub fn quantity(&self) -> &f64 {
        &self.quantity
    }

    #[getter]
    pub fn is_open(&self) -> bool {
        self.status == OrderStatus::Open
    }

    #[getter]
    pub fn timestamp(&self) -> &u64 {
        &self.timestamp
    }

    pub fn matches(&self, other: &Order) -> bool {
        if self.side == other.side {
            return false;
        }
        match self.side {
            OrderType::Buy => self.price >= other.price,
            OrderType::Sell => self.price <= other.price,
        }
    }

    pub fn fill(&mut self, incoming: &mut Order) -> Option<Fill> {
        if !self.matches(incoming) {
            return None;
        }

        let fill_quantity = self.quantity.min(incoming.quantity);
        self.quantity -= fill_quantity;
        incoming.quantity -= fill_quantity;

        if self.quantity == 0.0 {
            self.status = OrderStatus::Filled;
        }
        if incoming.quantity == 0.0 {
            incoming.status = OrderStatus::Filled;
        }

        let fill_price = if self.side == OrderType::Sell {
            self.price
        } else {
            incoming.price
        };

        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("Time went backwards")
            .as_nanos() as u64;

        Some(Fill::new(
            fill_quantity,
            fill_price,
            self.id.clone(),
            incoming.id.clone(),
            timestamp,
        ))
    }
}

// A container for the OrderBook
#[pyclass]
pub struct OrderBook {
    buy_orders: Vec<Order>,
    sell_orders: Vec<Order>,
}

#[pymethods]
impl OrderBook {
    #[new]
    pub fn new() -> Self {
        Self {
            buy_orders: vec![],
            sell_orders: vec![],
        }
    }

    pub fn add(&mut self, order: Order) {
        match order.side {
            OrderType::Buy => self.buy_orders.push(order),
            OrderType::Sell => self.sell_orders.push(order),
        }
        self.sort_orders();
    }

    pub fn sort_orders(&mut self) {
        self.buy_orders
            .sort_by(|a, b| b.price.partial_cmp(&a.price).unwrap_or(Ordering::Equal));
        self.sell_orders
            .sort_by(|a, b| a.price.partial_cmp(&b.price).unwrap_or(Ordering::Equal));
    }

    pub fn match_orders(&mut self) -> Vec<Fill> {
        let mut fills = vec![];

        while let (Some(mut buy), Some(mut sell)) = (self.buy_orders.pop(), self.sell_orders.pop())
        {
            if let Some(fill) = buy.fill(&mut sell) {
                fills.push(fill);
            }
            if buy.is_open() {
                self.buy_orders.push(buy);
            }
            if sell.is_open() {
                self.sell_orders.push(sell);
            }
        }

        self.sort_orders();
        fills
    }
}

impl Default for OrderBook {
    fn default() -> Self {
        Self::new()
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

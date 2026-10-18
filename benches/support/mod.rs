//! Deterministic workloads shared by Criterion and fixture validation tests.
use litebook::{Order, OrderBook, OrderType};

#[derive(Clone, Copy)]
pub enum Kind {
    Existing,
    NewLevels,
    Cancel,
    Partial,
    Sweep,
    Mixed,
}

#[derive(Clone, Copy)]
pub struct Case {
    pub name: &'static str,
    pub kind: Kind,
    pub scale: usize,
}

pub const CASES: [Case; 10] = [
    Case {
        name: "resting_existing/8",
        kind: Kind::Existing,
        scale: 8,
    },
    Case {
        name: "resting_existing/512",
        kind: Kind::Existing,
        scale: 512,
    },
    Case {
        name: "resting_new/256",
        kind: Kind::NewLevels,
        scale: 256,
    },
    Case {
        name: "cancel/16",
        kind: Kind::Cancel,
        scale: 16,
    },
    Case {
        name: "cancel/256",
        kind: Kind::Cancel,
        scale: 256,
    },
    Case {
        name: "cancel/4096",
        kind: Kind::Cancel,
        scale: 4096,
    },
    Case {
        name: "partial/256",
        kind: Kind::Partial,
        scale: 256,
    },
    Case {
        name: "sweep/8",
        kind: Kind::Sweep,
        scale: 8,
    },
    Case {
        name: "sweep/64",
        kind: Kind::Sweep,
        scale: 64,
    },
    Case {
        name: "mixed/64",
        kind: Kind::Mixed,
        scale: 64,
    },
];

pub enum Event {
    Add(Order),
    Cancel(String),
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Outcome {
    pub fills: usize,
    pub cancels: usize,
}

pub struct Fixture {
    pub book: OrderBook,
    pub events: Vec<Event>,
    pub expected: Outcome,
    pub expected_active: usize,
}

impl Fixture {
    pub fn run(&mut self) -> Outcome {
        let mut outcome = Outcome::default();
        for event in self.events.drain(..) {
            match event {
                Event::Add(order) => outcome.fills += self.book.add(order).unwrap().len(),
                Event::Cancel(id) => outcome.cancels += usize::from(self.book.cancel(&id)),
            }
        }
        outcome
    }
}

fn order(buy: bool, ticks: i64, quantity: f64) -> Order {
    Order::new(
        if buy { OrderType::Buy } else { OrderType::Sell },
        ticks,
        quantity,
    )
    .unwrap()
}

fn seed(fixture: &mut Fixture, buy: bool, ticks: i64, quantity: f64) -> String {
    let order = order(buy, ticks, quantity);
    let id = order.id().to_owned();
    assert!(fixture.book.add(order).unwrap().is_empty());
    id
}

fn add(fixture: &mut Fixture, buy: bool, ticks: i64, quantity: f64) -> String {
    let order = order(buy, ticks, quantity);
    let id = order.id().to_owned();
    fixture.events.push(Event::Add(order));
    id
}

pub fn next_random(state: &mut u64) -> u64 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    *state
}

pub fn prepare(case: Case) -> Fixture {
    let mut f = Fixture {
        book: OrderBook::new(1.0).unwrap(),
        events: Vec::new(),
        expected: Outcome::default(),
        expected_active: 0,
    };
    let mut random = 0x5eed;
    match case.kind {
        Kind::Existing => {
            for i in 0..case.scale {
                seed(&mut f, true, 10_000 - i as i64, 1.0);
            }
            for i in 0..256 {
                add(&mut f, true, 10_000 - (i % case.scale) as i64, 1.0);
            }
            f.expected_active = case.scale + 256;
        }
        Kind::NewLevels => {
            for i in 0..case.scale {
                add(&mut f, true, 10_000 + i as i64, 1.0);
            }
            f.expected_active = case.scale;
        }
        Kind::Cancel => {
            let mut ids: Vec<_> = (0..case.scale)
                .map(|_| seed(&mut f, true, 10_000, 1.0))
                .collect();
            for i in (1..ids.len()).rev() {
                let j = (next_random(&mut random) % (i as u64 + 1)) as usize;
                ids.swap(i, j);
            }
            let count = case.scale.min(256);
            f.events
                .extend(ids.into_iter().take(count).map(Event::Cancel));
            f.expected.cancels = count;
            f.expected_active = case.scale - count;
        }
        Kind::Partial => {
            seed(&mut f, false, 10_000, case.scale as f64 + 1.0);
            for _ in 0..case.scale {
                add(&mut f, true, 10_000, 1.0);
            }
            f.expected.fills = case.scale;
            f.expected_active = 1;
        }
        Kind::Sweep => {
            for i in 0..case.scale {
                seed(&mut f, false, 10_000 + i as i64, 1.0);
            }
            add(&mut f, true, 10_000 + case.scale as i64, case.scale as f64);
            f.expected.fills = case.scale;
        }
        Kind::Mixed => {
            for i in 0..64 {
                seed(&mut f, true, 9_990 - (i % 8) as i64, 1.0);
            }
            for _ in 0..case.scale {
                let bid = 9_990 - (next_random(&mut random) % 8) as i64;
                let ask = 10_010 + (next_random(&mut random) % 8) as i64;
                let canceled = add(&mut f, true, bid, 1.0);
                f.events.push(Event::Cancel(canceled));
                add(&mut f, false, ask, 1.0);
                add(&mut f, true, ask, 1.0);
                add(&mut f, true, 9_990, 1.0);
                add(&mut f, false, 9_990, 1.0);
            }
            f.expected = Outcome {
                fills: case.scale * 2,
                cancels: case.scale,
            };
            f.expected_active = 64;
        }
    }
    f
}

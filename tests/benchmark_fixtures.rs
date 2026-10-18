#[path = "../benches/support/mod.rs"]
mod support;

#[test]
fn benchmark_fixtures_produce_real_operations() {
    for case in support::CASES {
        let mut fixture = support::prepare(case);
        let mut fills = 0;
        let mut cancels = 0;
        for event in fixture.events.drain(..) {
            match event {
                support::Event::Add(order) => {
                    let result = fixture.book.add(order).unwrap();
                    assert!(result
                        .iter()
                        .all(|f| f.quantity() > 0.0 && f.price().is_finite()));
                    fills += result.len();
                }
                support::Event::Cancel(id) => cancels += usize::from(fixture.book.cancel(&id)),
            }
        }
        assert_eq!(fills, fixture.expected.fills, "{}", case.name);
        assert_eq!(cancels, fixture.expected.cancels, "{}", case.name);
        assert_eq!(
            fixture.book.get_buy_orders().len() + fixture.book.get_sell_orders().len(),
            fixture.expected_active,
            "{}",
            case.name
        );
        // A repeated run on the consumed fixture performs no events.
        assert_eq!(fixture.run(), support::Outcome::default());
    }
}

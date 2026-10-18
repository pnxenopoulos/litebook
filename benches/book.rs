use criterion::{criterion_group, criterion_main, BatchSize, Criterion, Throughput};
use std::hint::black_box;

mod support;

fn book(c: &mut Criterion) {
    let mut group = c.benchmark_group("book");
    for case in support::CASES {
        let mut fixture = support::prepare(case);
        let count = fixture.events.len();
        assert_eq!(fixture.run(), fixture.expected);
        drop(fixture);
        group.throughput(Throughput::Elements(count as u64));
        group.bench_function(case.name, |b| {
            b.iter_batched_ref(
                || support::prepare(case),
                |fixture| black_box(fixture.run()),
                BatchSize::LargeInput,
            );
        });
    }
    group.finish();
}

criterion_group!(benches, book);
criterion_main!(benches);

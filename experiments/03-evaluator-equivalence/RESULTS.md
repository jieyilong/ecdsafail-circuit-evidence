# Evaluator Equivalence: Results

The two evaluators agree on all 8,192 input/output/flag records and all 128 batches of integer gate totals. File completion order and byte offsets may differ. This is an agreement test for the mixed beta-one interface, not independent quantum verification.

| Evaluator | Cases | Batches | Total Toffolis | Total counted Clifford | Any failures |
|---|---|---|---|---|---|
| official | 8192 | 128 | 7804692572 | 91019583257 | 4 |
| auxiliary | 8192 | 128 | 7804692572 | 91019583257 | 4 |

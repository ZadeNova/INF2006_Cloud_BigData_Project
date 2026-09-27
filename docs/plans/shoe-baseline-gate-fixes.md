# Shoe-baseline gate fixes: G-001 and G-002

Written 27 September 2026, branch `syah&hermann/ML`. The user approved fixes for G-001 and G-002 from
the round-1 review in [shoe-baseline-gate.md](../reviews/shoe-baseline-gate.md). G-003 and G-004 are
not in scope. The user directed Claude Opus 5.5 to implement these fixes instead of Astra Low and to run
the re-review. The re-review is therefore logged as a same-session review.

## G-001: shoe-consistency rejects do not reach order lines

`validate` rejects a sized product after parsing when its name or category differs from its shoe's first
row, or when a size appears twice. The order-item check tests only `product_id not in parsed["products"]`,
so lines pointing at that product stay valid. With `--allow-rejects`, `persist` then fails with an
unhandled `KeyError`.

Fix in `src/config/dataset.py`: an order line is rejected as "missing/rejected product" when its product
is absent **or** its product row is in `rejects`. The existing cascade then rejects the whole order and
its other lines, as data/README.md already states.

Test: one regression in `tests/test_import.py`. Under `--allow-rejects`, an inconsistent size is
rejected, orders that use it are rejected, and an order that does not use it is imported.

## G-002: `seed_demo` retirement never matches a real row

The `demo-` and `sneaker-` rows were created in the old namespace `synthetic/revision-a/demo/v1`.
`seed_demo` looks for them only in the current `DEMO_NAMESPACE`, so it deactivates nothing. The namespace
switch already hides those rows from the shop, and checkout rejects them.

Fix: remove `RETIRED_EXTERNAL_ID_PREFIXES`, the deactivation loop and its docstring clause. Remove the
retired-row set-up and assertions from the `seed_demo` test and keep the 20 x 10 catalogue assertions.
This supersedes the retirement line in [shoe-sizes-catalogue.md](shoe-sizes-catalogue.md).

## Verification

Only the targeted tests: `tests/test_import.py` and `tests/test_catalogue.py` in the web image, after
`docker compose build web`.

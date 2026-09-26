# Self-review fixes: vendored model-viewer and shoe-dataset tests in CI

Written 27 September 2026, branch `syah&hermann/ML`. Approved by the user from the Claude self-review
(fresh pass) of `origin/main..HEAD`: fix findings 2 and 4 only. Findings 1, 3 and 5 (review gate log,
manifest values, evidence hygiene) are left for the user.

## Finding 2: model-viewer loaded from jsDelivr without integrity

`catalogue/product_list.html` and `catalogue/product_detail.html` loaded
`https://cdn.jsdelivr.net/npm/@google/model-viewer@4.1.0/dist/model-viewer.min.js` with no `integrity`
attribute, reintroducing the CDN dependency that review finding CR-009 removed for HTMX.

Fix: vendor the same file under `src/static/vendor/model-viewer/`, following the HTMX and Chart.js
precedent, and load it with `{% static %}`.

- Source: npm tarball `@google/model-viewer@4.1.0`, checked against the registry `dist.integrity`;
  `dist/model-viewer.min.js` compared byte-for-byte with the jsDelivr copy the pages loaded.
- The minified file ends with `sourceMappingURL=model-viewer.min.js.map`, so the map is vendored beside
  it (as for Chart.js) to keep WhiteNoise `CompressedManifestStaticFilesStorage` post-processing clean.
- Apache-2.0 `LICENSE` and a `README.md` with version, source, integrity and SHA-256 values.
- The twelve `.glb` models use no Draco, meshopt or KTX2 extensions, so model-viewer fetches no
  decoder from Google's CDN at runtime.

## Finding 4: CI does not run `analytics/tests/test_build_shoe_dataset.py`

The test is self-contained (`tmp_path` fixtures, no pandas) and imports `catalogue.shoes` and
`config.dataset`, so it joins the existing "Analytics PostgreSQL and strict loader tests" step, which
already sets `PYTHONPATH=/app`.

## Verification

- `collectstatic` in the web image, to confirm the manifest storage accepts the vendored file and map.
- `pytest` of `test_build_shoe_dataset.py` the same way CI runs it, plus the catalogue template tests.
- Hosted CI is not run locally.

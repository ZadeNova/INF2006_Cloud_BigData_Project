# HTMX vendor

This directory vendors the HTMX minified build so the site has no CDN dependency (review finding CR-009); it replaces the jsDelivr script tag in `base.html`.

- Version: htmx 2.0.4
- Authoritative release: [htmx v2.0.4](https://github.com/bigskysoftware/htmx/releases/tag/v2.0.4)
- Vendored distribution source: npm tarball `https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.4.tgz`, file `package/dist/htmx.min.js`. The tarball matched the registry's integrity value `sha512-HLxMCdfXDOJirs3vBZl/ZLoY+c7PfM4Ahr2Ad4YXh6d22T5ltbTXFFkpx9Tgb2vvmWFMbIc3LqN2ToNkZJvyYQ==`, and the extracted file is byte-identical to the jsDelivr copy the site loaded before (24 September 2026).
- Licence: Zero-Clause BSD, reproduced in `LICENSE.md`
- `htmx.min.js` SHA-256: `E209DDA5C8235479F3166DEFC7750E1DBCD5A5C1808B7792FC2E6733768FB447`

The minified file has no `sourceMappingURL`, so no source map is needed for WhiteNoise `collectstatic`.

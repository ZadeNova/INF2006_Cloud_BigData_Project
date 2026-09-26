# model-viewer vendor

This directory vendors Google's `<model-viewer>` web component so the catalogue's 3D shoe models load without a CDN dependency (as review finding CR-009 did for HTMX); it replaces the jsDelivr script tag in `catalogue/product_list.html` and `catalogue/product_detail.html`.

- Version: @google/model-viewer 4.1.0 (bundles its three.js dependency)
- Authoritative release: [model-viewer v4.1.0](https://github.com/google/model-viewer/releases/tag/v4.1.0)
- Vendored distribution source: npm tarball `https://registry.npmjs.org/@google/model-viewer/-/model-viewer-4.1.0.tgz`, files `package/dist/model-viewer.min.js` and `package/dist/model-viewer.min.js.map`. The tarball matched the registry's integrity value `sha512-7WB/jS6wfBfRl/tWhsUUvDMKFE1KlKME97coDLlZQfvJD0nCwjhES1lJ+k7wnmf7T3zMvCfn9mIjM/mgZapuig==`, and the extracted `model-viewer.min.js` is byte-identical to the jsDelivr copy the site loaded before (27 September 2026).
- Licence: Apache-2.0, reproduced in `LICENSE`
- `model-viewer.min.js` SHA-256: `8367184A607FBE07A78B650C0D359E5EBBD96F7E2B22F95F761F559B63430386`
- `model-viewer.min.js.map` SHA-256: `ED148D7D2453CC863DA185A54F95A0ADDCE38543B35BBC0159D00927A3B5E1AC`

The minified file references `model-viewer.min.js.map`; the matching source map is kept beside it so WhiteNoise `collectstatic` can post-process the asset without an absent-file error.

The shoe models in `static/models/` use no Draco, meshopt or KTX2 compression, so model-viewer does not fetch a decoder from Google's CDN at runtime. Re-check this if a compressed `.glb` is added.

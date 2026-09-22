# Chart.js vendor

This directory vendors the Chart.js 4.x UMD build so the analytics dashboard works without a CDN dependency.

- Version: Chart.js 4.4.7
- Authoritative release: [Chart.js v4.4.7](https://github.com/chartjs/Chart.js/releases/tag/v4.4.7)
- Vendored distribution source: [jsDelivr npm package](https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js)
- Licence: MIT, reproduced in `LICENSE.md`
- `chart.umd.min.js` SHA-256: `206B6E8BB00FC7BBA2C7EE80CA41DB3E9E05BA7BE0AA35ABEBA9CFD5357F5D0E`
- `chart.umd.js.map` SHA-256: `2AB6E6D07FCC59C470F2B5C4DF97CA2A6B8A8A0CF418D0564E9CA4AC6FF8BCFD`

The minified distribution references `chart.umd.js.map`; the matching source map is kept beside it so WhiteNoise `collectstatic` can post-process the asset without an absent-file warning.

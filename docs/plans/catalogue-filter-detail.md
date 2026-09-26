# Manage-products filter and product detail page

Status: implemented 26 September 2026 (96 related tests pass; checked in headless Chrome at desktop and
phone widths). Approved 26 September 2026 (user request: "add a filter for UI/UX to the manage products
page"; "click the product to show a detail page, like the Shopee example; just the size dropdown
and add to cart"). A first draft of both already existed uncommitted; this plan finishes it.

## Manage products filter (`GET /products/manage/`, operator only)

- Filter bar in a `surface-card` above the table, styled per DESIGN.md: a search box (name, `q`)
  with Search and Clear, then **filter chips** (DESIGN.md "Filter Chip", the existing `.chip` /
  `.chip--on` used by the analytics range selector) for Status (All / Active / Inactive) and
  Category (All plus each category). Chips are plain links, so no JavaScript; each keeps the
  other active filters and resets to page 1. The selected chip has `aria-current="true"`.
- Query parameters stay `q`, `category`, `status`; unknown values fall back to "all".
- Fixes to the draft:
  - Pager links keep the active filters (the draft dropped them on page 2).
  - Activate/Deactivate returns to the same filtered page: the form posts a `next` path that the
    view accepts only if it is the manage-list path (no open redirect); otherwise page 1 as now.
    This also closes review finding W-04.
  - An empty result shows "No products match these filters" with a Clear link.
  - The count reads "N products" for the filtered result.

## Product detail page (`GET /products/<id>/`, public)

- Card image and name on the catalogue link to it (draft already does this).
- Shopee-style two-column layout, stacking on phones: large product tile or 3D model on the left;
  on the right the category, name, price, stock line, the size dropdown and Add to cart (logged
  out: "Log in to add"; sold out: disabled). Reuses the catalogue's existing size select and
  add-to-cart form unchanged; `cart:add` still redirects to the cart. A "Back to products" link.
- Only shoes with an active size are shown; others 404 (draft behaviour).

## Tests

Existing draft tests plus: pager links keep filters; toggle returns to the filtered page and
rejects an off-site `next`; empty-filter message; chip links carry the other filters; detail page
for a logged-out user shows the login link.

## Not in scope

Cart behaviour, HTMX, product editing, catalogue list filters.

## Addendum: stay on the page after Add to cart (26 September 2026)

Teammate request (Hermann): Add to cart should not jump to the cart page, because customers add
several products. Both add-to-cart forms (catalogue card and detail page) post a hidden `next`
with the current page. `cart:add` accepts it only if it is a `/products/` path (not
`/products/manage/`) on this host; on success it redirects there with the existing success
message bar ("<shoe · size> added to your cart.") plus a "View cart" link, and on a validation
error with the error bar. Without a valid `next` the old redirect to the cart is kept, so other
callers and HTMX responses are unchanged. The header cart count updates on the reload. Tests:
redirect back with the message, error back to the page, unsafe `next` ignored.

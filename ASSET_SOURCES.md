# 2026-09-24 Library redesign assets

- Method: built-in `imagegen`; original generated image, no reference photograph copied into production.
- Saved website assets: `assets/library-hero.webp` (117,514 bytes), `assets/library-hero-mobile.webp` (38,630 bytes), `assets/library-og.webp` (72,038 bytes).
- Existing sheep icon retained, resized into `assets/sheep-icon-64.png` and `assets/sheep-icon-180.png` for appropriate display sizes.
- Existing review covers retain their Rakuten URLs. New-title covers use the publisher URLs linked in `library_content.py`, with adjacent book information and source links.

## Final image-generation prompt

Use case: photorealistic-natural. Asset type: wide photographic website hero background for a Japanese investment-book editorial library. Create an original authentic old British private library reading room, intellectual, quiet, slightly mysterious but welcoming and trustworthy. Dark aged walnut built-in bookshelves densely lined with old cloth-bound and leather books, muted stone arch details, warm brass reading lamps, an inviting antique wooden desk with an open book and a few stacked volumes, small amber light pools, rich deep forest green shadows. Photorealistic interior architectural editorial photography, subtle film texture, beautifully restrained and realistic, no fantasy, no horror, no people, no candles, no text, no logos, no watermarks. Wide landscape 16:9 composition: the LEFT HALF is mostly dark softly visible shelves and shadow for legible HTML heading overlay, right half features warmly lit reading table, books and brass lamp with a glimpse of tall arched stone window. Camera at eye level, natural perspective, refined atmosphere, no excessive dramatic fog. Warm amber, antique brass, walnut, dark olive and charcoal palette. The resulting website will add its own text; generate only the interior photograph.

## Verified editorial sources

- https://www.diamond.co.jp/book/9784478125137.html — AIバブル後の投資戦略
- https://prtimes.jp/main/html/rd/p/000000545.000045710.html — publisher's release date announcement (2026-07-15)
- https://www.diamond.co.jp/book/9784478122983.html — ママ投資家が育休中に1億貯めた株式投資
- https://www.diamond.co.jp/book/9784478121368.html — THE WEALTH LADDER 富の階段 (2025-11, not labelled a 2026 release)
- https://www.tohan.jp/wp/wp-content/uploads/2026/06/20260616.pdf — historical sales signal, period 2026-06-08 to 2026-06-14

## Technical references

- https://developers.google.com/search/docs/essentials
- https://developers.google.com/search/docs/appearance/structured-data/review-snippet
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap

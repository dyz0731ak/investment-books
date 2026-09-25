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


## 2026-09-25 追加書籍の書影

書誌・表紙を照合した書籍紹介用の書影。縦横比を維持し最大400×600pxのWebPへ変換。装飾加工なし。各書籍ページの情報源と合わせて確認する。

| ISBN | 書籍 | 書影の確認先 |
|---|---|---|
| 9784023334632 | 今さら聞けない 投資の超基本 改訂新版 | [画像](https://publications.asahi.com/uploads/cover_image_25630_06c65827b4.jpg) / [書誌](https://publications.asahi.com/product/25630.html) |
| 9784478119310 | 新NISAはこの9本から選びなさい | [画像](https://www.diamond.co.jp/book/p74hs00000009gai-img/9784478119310.jpg) / [書誌](https://www.diamond.co.jp/book/9784478119310.html) |
| 9784478123720 | 新NISAで買うべき株＆投信77 2026年度版 | [画像](https://www.diamond.co.jp/book/kl8je0000000cm6s-img/9784478123720.jpg) / [書誌](https://www.diamond.co.jp/book/9784478123720.html) |
| 9784775973318 | 投資の4原則 | [画像](https://www.panrolling.com/books/wb/wb362.jpg) / [書誌](https://www.panrolling.com/books/wb/wb362.html) |
| 9784106110627 | 年1時間で億になる投資の正解 | [画像](https://www.shinchosha.co.jp/images_v2/book/cover/611062/611062_l.jpg) / [書誌](https://www.shinchosha.co.jp/book/611062/) |
| 9784478107041 | ファンダメンタル投資の教科書 改訂版 | [画像](https://www.diamond.co.jp/images/book/1/9784478107041.jpg) / [書誌](https://www.diamond.co.jp/book/9784478107041.html) |
| 9784198627058 | バフェットの財務諸表を読む力 | [画像](https://m.media-amazon.com/images/I/71gpladnrYL._AC_UL320_.jpg) / [書誌](https://www.books.or.jp/book-details/9784198627058) |
| 9784478121368 | THE WEALTH LADDER 富の階段 | [画像](https://www.diamond.co.jp/book/kl8je0000000ck4a-img/9784478121368.jpg) / [書誌](https://www.diamond.co.jp/book/9784478121368.html) |
| 9784295410898 | 不動産投資の成功法則 | [画像](https://book.cm-marketing.jp/wp-content/uploads/2025/03/9784295410898.jpg) / [書誌](https://book.cm-marketing.jp/books/9784295410898/) |
| 9784866678306 | インフレ時代の不動産投資 最短で成功するロードマップ | [画像](https://newscast.jp/attachments/ac4urvtINIjtjQtJZI4d.jpg?w=600&h=600&a=1) / [書誌](https://www.atpress.ne.jp/news/8902975) |
| 9784296001460 | 株式投資 第6版 | [画像](https://bookplus.nikkei.com/atcl/catalog/25/02/12/01858/9784296001460a.jpg) / [書誌](https://bookplus.nikkei.com/atcl/catalog/25/02/12/01858/) |
| 9784046068514 | 【超完全版】フルオートモードで月に31.5万円が入ってくる「強配当」株投資 | [画像](https://cdn.kdkw.jp/cover_1000/322401/322401000223.webp) / [書誌](https://www.kadokawa.co.jp/product/322401000223/) |
| 9784065350355 | わが投資術 市場は誰に微笑むか | [画像](https://dvs-cover.kodansha.co.jp/0000387083/BGv8gROQ7Q72MxAxPEBYFXnAOCZYAa1AHIjjkxZd.jpg) / [書誌](https://www.kodansha.co.jp/book/products/0000387083) |
| 9784065450147 | なぜ株の上手い人はIRセミナーに集まるのか | [画像](https://images.microcms-assets.io/assets/ae0f16f9610449e2a63fa84711747515/cc0bdc8a9da845e5b226458ef39e9d34/396_cover.jpg?w=1200&fit=max&fm=webp&q=80) / [書誌](https://seikaisha.co.jp/books/shinsho/boov5-9-1r/) |
| 9784478122983 | ママ投資家が育休中に1億貯めた株式投資 | [画像](https://www.diamond.co.jp/book/vh2s9k0000001qoi-img/9784478122983.jpg) / [書誌](https://www.diamond.co.jp/book/9784478122983.html) |

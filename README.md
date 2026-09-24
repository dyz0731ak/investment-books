# 迷える子羊たちの投資本ガイド

本番: https://stock-overflow24.com/ — ConoHa WING。`main` への push で既存の GitHub Actions が FTP デプロイします。

英国の図書館をイメージした、投資本の静的な書評・比較サイトです。27書評、9テーマ、5比較記事など50のインデックス対象ページと、専用404ページを生成します。

## 編集とビルド

```sh
python3 -m pip install -r requirements.txt
python3 build.py
python3 scripts/audit_site.py
python3 -m http.server 8765 --bind 127.0.0.1
```

- `build.py`: 書評・カテゴリ・比較記事、HTML生成、構造化データ、サイトマップ。`CONTENT_DATE` は編集を確認した日にだけ更新します。
- `library_content.py`: トップの選書、新刊・話題書の出典・刊行情報、FAQ。新刊の書誌紹介と読了レビューを区別します。
- `style.css`: 共通の文章・比較表レイアウトと図書館テーマ、レスポンシブ、読みやすさの調整。
- `assets/library.js`: 検索・絞り込み・画像取得失敗時の代替表示。検索条件はURLのハッシュに保存し、検索結果の大量インデックスを避けます。
- `data/books.json`: 楽天の公開書誌情報のキャッシュ。API認証情報がないビルドでも書影とリンクを維持します。キャッシュ価格は掲載しません。
- `scripts/audit_site.py`: 全ページの見出し、メタ情報、内部リンク・アンカー、構造化データ、画像寸法、サイトマップ整合性を検証。デプロイ前にも実行します。
- `.htaccess`: 旧WordPress URLの301を維持し、正規ホスト・index.htmlを集約。404は実際の404ステータスで返します。HTML再検証、バージョン付きCSS/JSのキャッシュ、圧縮を設定します。

楽天APIを明示的に更新する場合のみ `RAKUTEN_APP_ID`、`RAKUTEN_ACCESS_KEY`、`RAKUTEN_AFFILIATE_ID` を環境変数で設定します。秘密情報をファイル・コミットに入れないでください。

生成HTMLもバージョン管理します。編集後は必ずビルドして検証してください。公開時のGA4 IDは既存のGitHub Secretから注入されます。アフィリエイトのリンク属性・計測は維持しています。AdSense Auto Adsは書評・比較記事・ガイド・過去調査に残し、load後のidle時に読み込みます。トップ・本棚・カテゴリ・新刊・比較一覧には自動広告を読み込みません。公開測定で24MB超の動画広告を確認したため、本を探す主要画面の視認性と通信量を優先しています。

## SEOと運用

- `/`: 投資本・投資のおすすめ本を探す入口。
- `/beginner/`、`/stocks/`、`/nisa/` など: 検索目的別のカテゴリ。
- `/books/`: 全27冊の検索可能な一覧。JavaScript無効でも全書評へ移動可能。
- `/compare/` と既存の比較記事: 本の違い・読む順番に答えるページ。
- `/new/`: 新刊・話題書の確認日・出典・定番との関連を示す書誌紹介。
- `/trends/2026-08/`: 過去の売れ筋調査。現在の順位と混同しない表記を維持。
- `/books/<slug>/`: 個別書評（Book + 既存の運営者Review）。実読体験は確認済みの事実だけを追記してください。

既存URLを移動しない設計です。構造化データは可視情報に対応したWebSite、Organization、BreadcrumbList、ItemList、Book、Review、CollectionPageを使用します。FAQは通常のHTMLに留めています。

公開後はSearch Consoleのサイトマップ読み込み・主要新規URLのインデックスを確認し、対象クエリ群の表示回数・クリック・CTRとページ別流入を比較します。順位上昇を保証するものではなく、実読レビュー・新刊情報の継続的な更新が必要です。

## 画像

図書館写真は2026年9月24日に組み込みimagegenで作成したオリジナルです。`assets/library-hero.webp`（PC）、`library-hero-mobile.webp`（モバイル）、`library-og.webp`（SNS）を参照しています。参考写真自体は転載していません。詳細プロンプト・検証記録は同日のリニューアル記録に保存。

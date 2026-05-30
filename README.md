# 迷える子羊たちの株ノート（投資本の紹介サイト）

`manabiya.stock-overflow24.com` で公開する、投資の名著を紹介する静的サイト。
楽天ブックスAPIから表紙・価格・楽天アフィリ購入リンクを取得し、`index.html` に焼き込む。

## 構成
- `index.html` / `style.css` … 公開する静的サイト（`build.py` が生成）
- `build.py` … 楽天ブックスAPIで書誌情報を取得し index.html / data/books.json を生成するビルドスクリプト
- `data/books.json` … 生成された書籍データ（公開情報のみ。秘密情報は含まない）
- `.htaccess` / `robots.txt` / `sitemap.xml` … 公開用設定
- `.github/workflows/deploy.yml` … main への push で ConoHa WING へFTPデプロイ

## 再ビルド（表紙・価格を更新したいとき）
楽天ウェブサービスの認証情報を **環境変数** で渡して実行する（コードには絶対に書かない）:

```bash
RAKUTEN_APP_ID="<アプリID(UUID)>" \
RAKUTEN_ACCESS_KEY="<アクセスキー pk_...>" \
RAKUTEN_AFFILIATE_ID="<楽天アフィリID>" \
python3 build.py
```

生成された `index.html` / `data/books.json` には **表紙URL・公開アフィリリンクのみ** が入り、
アクセスキー等の秘密情報は含まれない。生成後にコミット→push でデプロイ。

## デプロイ（ConoHa WING + GitHub Actions）
[[収益化サイト運用ハブ]] / 「サブドメインで静的サイトを公開する手順」に準拠。

1. ConoHa WING で `manabiya.stock-overflow24.com` を作成（無料独自SSL ON）
2. FTPアカウント作成
3. GitHub Secrets に登録: `FTP_SERVER` / `FTP_USERNAME` / `FTP_PASSWORD`
4. main へ push → 自動デプロイ

## 注意
- 紹介文・ランキングは当サイトのオリジナル。出版社コピー（APIのitemCaption）は転載しない。
- 当サイトはアフィリエイトプログラム（楽天アフィリ等）を利用。

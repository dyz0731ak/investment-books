#!/usr/bin/env python3
"""
迷える子羊たちの株ノート ── 静的サイト ビルド

- 楽天ブックス書籍検索API（新仕様 openapi.rakuten.co.jp）から
  各書籍の「表紙画像・正式タイトル・著者・価格・楽天アフィリ購入リンク」を取得。
- 紹介文・ポイント・タグ・ランキングは“当サイトのオリジナル”（出版社コピーは転載しない）。
- data/books.json と index.html を生成する。

認証情報は環境変数から読む（コード・生成物には残さない）:
  RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY, RAKUTEN_AFFILIATE_ID
"""
from __future__ import annotations
import os, sys, json, html, re, time
import requests

API = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://stock-overflow24.com/",
    "Origin": "https://stock-overflow24.com",
}
SITE_NAME = "迷える子羊たちの株ノート"
SITE_TAGLINE = "迷える子羊たちへ。投資の“はじめの一冊”を。"

# ── キュレーション（紹介文・ポイント・タグはオリジナル） ──
BOOKS = [
    dict(rank=1, q="ウォール街のランダム・ウォーカー", author="マルキール",
         tags=["不朽の定番", "インデックス投資"],
         desc="「市場の値動きは予測できない。だからこそ低コストのインデックスファンドを長く持ち続けるのが最善」——半世紀読み継がれる、インデックス投資の世界的バイブル。まず1冊だけ選ぶなら、迷わずこれ。",
         points=["個別株やタイミング投資から卒業できる", "“ほったらかし”で良い理由が腑に落ちる"]),
    dict(rank=2, q="敗者のゲーム", author="エリス",
         tags=["初心者必読", "インデックス投資"],
         desc="プロでも市場平均に勝ち続けるのは至難の業。だからこそ個人は「勝とうとしない＝市場全体を買う」のが合理的——その理由をテニスの比喩でやさしく解き明かす一冊。薄くて読みやすい。",
         points=["“なぜインデックスなのか”が短時間でわかる", "投資の世界の現実を最初に知れる"]),
    dict(rank=3, q="インデックス投資は勝者のゲーム", author="ボーグル",
         tags=["低コスト", "インデックス投資"],
         desc="世界最大級の運用会社バンガードを創り、低コスト・インデックスファンドを世に広めた本人が語る、個人投資家が勝つための王道。手数料が長期リターンをどれだけ蝕むかが腹落ちする。",
         points=["“コストの低さ”が最強の武器だと納得できる", "長期・分散・低コストの原点を学べる"]),
    dict(rank=4, q="お金の大学", author="",
         tags=["超入門", "家計・節約"],
         desc="「貯める・稼ぐ・増やす・守る・使う」——お金の5つの力を図解たっぷりで体系的に。投資の前に整えるべき家計の基礎から学べるので、何も知らない状態の最初の一冊に最適。",
         points=["投資より前に“固定費の見直し”から始められる", "イラスト中心で挫折しにくい"]),
    dict(rank=5, q="ほったらかし投資術", author="山崎元",
         tags=["実践向け", "NISA・つみたて"],
         desc="「結局、日本の個人は何をどう買えばいいの?」に、口座・銘柄レベルで具体的に答えてくれる実践書。新NISA時代の今こそ、最初に手を動かすときの道しるべになる。",
         points=["口座開設〜銘柄選びまで具体的に進められる", "新NISAの活用イメージがつかめる"]),
    dict(rank=6, q="株式投資の未来", author="シーゲル",
         tags=["長期投資", "配当"],
         desc="過去データをもとに「派手な成長株より、配当を着実に再投資する優良株のほうが報われた」ことを示した名著。長期・配当再投資の力をデータで腹落ちさせてくれる。",
         points=["配当再投資の威力をデータで理解できる", "短期の値動きに振り回されなくなる"]),
    dict(rank=7, q="賢明なる投資家", author="グレアム",
         tags=["古典", "バリュー投資"],
         desc="ウォーレン・バフェットの師が記した、バリュー投資の原典。「価格」と「価値」を分けて考える姿勢など、相場の本質を学びたい人の到達点。やや骨太なので慣れてきた頃に。",
         points=["“安全域”の考え方が身につく", "暴落時にうろたえない軸ができる"]),
    dict(rank=8, q="金持ち父さん貧乏父さん", author="キヨサキ",
         tags=["マインド", "入門"],
         desc="「資産と負債の違い」「お金に働いてもらう」というお金との向き合い方を変えてくれた世界的ベストセラー。具体的な投資手法より、最初のマインドセットを作る一冊。",
         points=["お金の“考え方”が根本から変わる", "投資を始める動機づけになる"]),
]


def rakuten_lookup(book: dict, app_id: str, access_key: str, aff_id: str) -> dict:
    """タイトル(+著者)で売れ筋順検索し、表紙/著者/価格/アフィリリンクを取得。
    title+author で0件ならtitleのみで再検索する。"""
    auth = {"applicationId": app_id, "accessKey": access_key, "affiliateId": aff_id,
            "format": "json", "hits": 1, "sort": "sales"}
    queries = []
    if book.get("author"):
        queries.append({"title": book["q"], "author": book["author"]})
    queries.append({"title": book["q"]})
    for params in queries:
        items = None
        for attempt in range(3):  # レート制限対策に最大3回リトライ
            try:
                r = requests.get(API, params={**auth, **params}, headers=HEADERS, timeout=20)
                if r.status_code == 200 and '"Items"' in r.text:
                    items = r.json().get("Items") or []
                    break
                time.sleep(1.5 * (attempt + 1))
            except Exception as e:
                print(f"  [warn] {book['q']}: {e}", file=sys.stderr)
                time.sleep(1.5 * (attempt + 1))
        if not items:
            time.sleep(0.8)
            continue
        it = items[0]["Item"]
        img = it.get("largeImageUrl") or it.get("mediumImageUrl") or ""
        # 表紙を少し大きめに（_ex=120x120 → 300x300）
        img = re.sub(r"_ex=\d+x\d+", "_ex=300x300", img)
        return {
            "title": it.get("title", book["q"]),
            "author": it.get("author", ""),
            "cover": img,
            "price": it.get("itemPrice"),
            "url": it.get("affiliateUrl") or it.get("itemUrl") or "",
        }
    return {"title": book["q"], "author": "", "cover": "", "price": None, "url": ""}


def build_books() -> list[dict]:
    app_id = os.environ.get("RAKUTEN_APP_ID", "")
    access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")
    aff_id = os.environ.get("RAKUTEN_AFFILIATE_ID", "")
    have_creds = bool(app_id and access_key)
    out = []
    for b in BOOKS:
        info = rakuten_lookup(b, app_id, access_key, aff_id) if have_creds else \
               {"title": b["q"], "author": "", "cover": "", "price": None, "url": ""}
        out.append({**b, **info})
        print(f"  #{b['rank']} {info['title'][:28]} cover={'Y' if info['cover'] else '-'} aff={'Y' if info['url'] else '-'}", file=sys.stderr)
        if have_creds:
            time.sleep(1.0)  # レート制限回避のため本ごとに間隔
    return out


def esc(s): return html.escape(str(s or ""))


def amazon_search(title: str) -> str:
    return "https://www.amazon.co.jp/s?k=" + requests.utils.quote(title)


def rakuten_url(b: dict) -> str:
    return b.get("url") or ("https://search.rakuten.co.jp/search/mall/" + requests.utils.quote(b["q"]) + "/")


def render_card(b: dict) -> str:
    rank = b["rank"]
    rank_cls = f"book rank-{rank} is-top" if rank <= 3 else "book"
    cover = (f'<img class="book-cover" src="{esc(b["cover"])}" alt="{esc(b["title"])}の表紙" loading="lazy">'
             if b.get("cover") else f'<div class="book-cover book-cover--ph">{esc(b["title"])}</div>')
    tags = "".join(f'<span class="tag{" tag-gold" if i==0 else ""}">{esc(t)}</span>'
                   for i, t in enumerate(b["tags"]))
    points = "".join(f"<li>{esc(p)}</li>" for p in b["points"])
    price = f'<span class="book-price">楽天価格 {b["price"]:,}円〜</span>' if b.get("price") else ""
    author = f'<p class="book-author">{esc(b["author"])}</p>' if b.get("author") else ""
    return f"""
      <article class="{rank_cls}" id="rank{rank}">
        <div class="book-rank"><span class="rank-num">{rank}</span></div>
        <div class="book-coverwrap">{cover}</div>
        <div class="book-body">
          <div class="book-tags">{tags}</div>
          <h3 class="book-title">{esc(b['title'])}</h3>
          {author}
          <p class="book-desc">{esc(b['desc'])}</p>
          <ul class="book-points">{points}</ul>
          {price}
          <div class="book-cta">
            <a class="btn btn-amazon" href="{esc(amazon_search(b['title']))}" target="_blank" rel="sponsored nofollow noopener">Amazonで見る</a>
            <a class="btn btn-rakuten" href="{esc(rakuten_url(b))}" target="_blank" rel="sponsored nofollow noopener">楽天ブックスで見る</a>
          </div>
        </div>
      </article>"""


PERSONAS = [
    "<strong>何から始めるか分からない</strong>初心者。まず1冊で全体像をつかみたい人。",
    "<strong>NISA・つみたて</strong>を始めたいけど、銘柄選びで迷っている人。",
    "流行りの手法ではなく、<strong>長く使える原理原則</strong>を身につけたい人。",
]


def render_personas() -> str:
    cells = "".join(f'<div class="persona"><p class="persona-text">{t}</p></div>' for t in PERSONAS)
    return f'<div class="personas">{cells}</div>'


def render_toc(books: list[dict]) -> str:
    items = "".join(
        f'<li><a href="#rank{b["rank"]}"><span class="num">{b["rank"]}.</span>{esc(b["title"])}</a></li>'
        for b in books)
    return f'''<nav class="toc" aria-label="目次">
      <p class="toc-title">この記事の目次（おすすめ8冊）</p>
      <ul class="toc-list">{items}</ul>
    </nav>'''


RELATED = [
    ("📊", "投資の砦", "日本株・米国株の急騰銘柄やストップ高、決算速報がひと目で分かるリアルタイム・ダッシュボード。本で学んだら、実際の相場をのぞいてみよう。",
     "https://dashboard.stock-overflow24.com/", "ダッシュボードを見る"),
    ("📖", "やさしい投資用語辞典", "「PER・PBR・ROEって何？」——投資の専門用語をやさしく解説。本を読んでいて分からない言葉が出てきたら、ここで調べよう。",
     "https://yougo.stock-overflow24.com/", "用語を調べる"),
]


def render_related() -> str:
    cards = "".join(f'''<a class="related-card" href="{esc(u)}">
        <span class="related-body">
          <span class="related-name">{esc(n)}</span>
          <span class="related-desc">{esc(d)}</span>
          <span class="related-go">{esc(cta)} ›</span>
        </span>
      </a>''' for e, n, d, u, cta in RELATED)
    return f'<div class="related-grid">{cards}</div>'


def render_compare(books: list[dict]) -> str:
    rows = ""
    for b in books:
        price = f'{b["price"]:,}円〜' if b.get("price") else "—"
        feature = b["tags"][0] if b.get("tags") else ""
        rows += f'''<tr>
          <td class="c-rank">{b['rank']}</td>
          <td class="c-title">{esc(b['title'])}</td>
          <td>{esc(feature)}</td>
          <td>{price}</td>
          <td class="c-link"><a href="{esc(rakuten_url(b))}" target="_blank" rel="sponsored nofollow noopener">楽天 ›</a></td>
        </tr>'''
    return f'''<div class="compare-wrap">
      <table class="compare">
        <thead><tr><th>順位</th><th>書名</th><th>特徴</th><th>価格</th><th>リンク</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>'''


def render_html(books: list[dict]) -> str:
    cards = "".join(render_card(b) for b in books)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>投資初心者が最初に読むべき『投資の名著』8選 | {SITE_NAME}</title>
<meta name="description" content="投資を始めたい初心者がまず読むべき定番の名著だけを厳選。インデックス投資から相場の心構えまで、土台が作れる8冊をランキング形式で、選ぶ理由つきで紹介します。">
<meta property="og:title" content="投資初心者が最初に読むべき『投資の名著』8選">
<meta property="og:description" content="長く読み継がれる投資の定番だけを厳選。最初の一冊で迷わないためのランキング。">
<meta property="og:type" content="article">
<meta property="og:image" content="https://manabiya.stock-overflow24.com/assets/sheep-icon.png">
<link rel="icon" type="image/png" href="assets/sheep-icon.png">
<link rel="apple-touch-icon" href="assets/sheep-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/">
      <img class="brand-mark" src="assets/sheep-icon.png" alt="{SITE_NAME}" width="40" height="50">
      <span class="brand-text">
        <span class="brand-name">{SITE_NAME}</span>
        <span class="brand-tagline">{SITE_TAGLINE}</span>
      </span>
    </a>
    <input type="checkbox" id="navToggle" class="nav-toggle" hidden>
    <label for="navToggle" class="nav-btn" aria-label="メニュー"><span></span><span></span><span></span></label>
    <nav class="gnav">
      <a href="#ranking">ランキング</a>
      <a href="#compare">比較表</a>
      <a href="#about">このサイトについて</a>
    </nav>
  </div>
</header>

<section class="hero">
  <div class="hero-inner">
    <p class="hero-eyebrow">編集部が選ぶ・投資のバイブル</p>
    <h1 class="hero-title">投資初心者が最初に読むべき<br><em>『投資の名著』8選</em></h1>
    <p class="hero-lead">「投資を始めたいけれど、何から学べばいいのかわからない…」——そんな<strong>迷える子羊</strong>のあなたへ。世界中の投資家に長く読み継がれてきた<strong>定番の名著だけ</strong>を、選ぶ理由つきで厳選しました。</p>
    <div class="hero-rule"></div>
    <p class="hero-meta">更新日 2026.05.30 ・ {SITE_NAME}編集部</p>
  </div>
</section>

<main class="container">
  <nav class="breadcrumb"><a href="/">TOP</a> <span>›</span> 投資の名著8選</nav>

  {render_toc(books)}

  <section id="for-who">
    <h2 class="section-title">こんな人におすすめ</h2>
    {render_personas()}
  </section>

  <section id="ranking" class="ranking">
    <h2 class="section-title">まず読むべき投資の名著 <span class="section-sub">ランキング8選</span></h2>
    {cards}
  </section>

  <section id="compare">
    <h2 class="section-title">ひと目で比較 <span class="section-sub">順位・特徴・価格</span></h2>
    {render_compare(books)}
  </section>

  <section id="related">
    <h2 class="section-title">投資をもっと深める <span class="section-sub">姉妹サイト</span></h2>
    {render_related()}
  </section>

  <section id="about" class="about-box">
    <h2 class="section-title">このサイトについて</h2>
    <p>「{SITE_NAME}」は、投資を学びたい人が“最初の一冊”で迷わないように、長く読み継がれてきた定番の本を厳選して紹介するサイトです。流行に左右されない原理原則を大切にしています。まずは気になった1冊から、あなたの投資の土台を作っていきましょう。</p>
  </section>
</main>

<footer class="site-footer">
  <div class="footer-inner">
    <p class="footer-brand"><img class="footer-mark" src="assets/sheep-icon.png" alt="" width="28" height="35">{SITE_NAME}</p>
    <nav class="footer-nav">
      <a href="#ranking">ランキング</a>
      <a href="https://dashboard.stock-overflow24.com/">投資の砦</a>
      <a href="https://yougo.stock-overflow24.com/">用語辞典</a>
      <a href="#about">このサイトについて</a>
      <a href="#">お問い合わせ</a>
      <a href="#">プライバシーポリシー</a>
    </nav>
    <p class="footer-note">※当サイトはアフィリエイトプログラム（楽天アフィリエイト・Amazonアソシエイト等）を利用しています。リンク経由のご購入で運営者に紹介料が支払われる場合があります。</p>
    <p class="footer-note">※掲載内容は書籍の紹介であり、特定の投資・銘柄を推奨するものではありません。投資は自己責任で行ってください。</p>
    <p class="footer-copy">© 2026 {SITE_NAME}</p>
  </div>
</footer>
</body>
</html>
"""


def main():
    here = os.path.dirname(__file__)
    books = build_books()
    os.makedirs(os.path.join(here, "data"), exist_ok=True)
    # books.json には公開情報のみ（認証情報は含めない）
    with open(os.path.join(here, "data", "books.json"), "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)
    with open(os.path.join(here, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_html(books))
    print(f"[build] {len(books)}冊 / index.html 生成", file=sys.stderr)


if __name__ == "__main__":
    main()

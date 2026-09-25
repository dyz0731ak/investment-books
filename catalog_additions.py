"""Source-verified introductions; never assign unread books a review rating."""
import json
from pathlib import Path

ADDITIONAL_BOOKS = json.loads((Path(__file__).parent / 'data/catalog_additions.json').read_text(encoding='utf-8'))


def validate_additions(existing_slugs, themes):
    slugs, isbns = set(existing_slugs), set()
    for book in ADDITIONAL_BOOKS:
        isbn = book['isbn']
        assert len(isbn) == 13 and isbn.isdigit(), f"Invalid ISBN: {isbn}"
        assert sum(int(n) * (1 if i % 2 == 0 else 3) for i, n in enumerate(isbn)) % 10 == 0, f"ISBN checksum: {isbn}"
        assert book['slug'] not in slugs and isbn not in isbns, f"Duplicate book: {book['slug']}"
        assert book['theme'] in themes, f"Unknown category: {book['theme']}"
        assert book['source'].startswith('https://') and book['authors'] and book['publisher']
        slugs.add(book['slug']); isbns.add(isbn)
    for book in ADDITIONAL_BOOKS:
        assert all(slug in slugs for slug, label in book['related']), book['slug']


CATEGORY_ADDITIONS = {
    'beginner': ('はじめての投資本を選ぶなら', '家計全体を整える本に加え、図解で株・投資信託・NISAの違いを学ぶ改訂版を追加しました。', [('cho-kihon', '用語や商品の全体像から学ぶ')]),
    'nisa': ('NISAの本は「制度」と「商品選び」を読み分ける', '制度の入口を学んだら、投信の選定理由や、株と投信の比較へ。年度版は掲載情報の時点も確認して選びましょう。', [('nisa-nine', '積立投信を選ぶ判断軸を知る'), ('nisa-77-2026', '2026年度版で株と投信を比較する')]),
    'index': ('長期投資の原則を、別の視点でも読む', '今ある名著に、理論・歴史・心理を掘り下げる本と、忙しい人の長期運用を考える本を加えました。', [('four-pillars', '投資の原則を体系的に学ぶ'), ('one-hour', '相場を追いすぎない運用を考える')]),
    'buffett': ('投資哲学から財務分析へ', 'バフェット流の考え方を学んだ後、企業の強みを決算の数字で確かめたい人向けの定番を追加しました。', [('buffett-statements', '財務諸表と競争力を結びつける')]),
    'fire': ('経済的自由への、次の段階を考える', 'FIREの実践や人生設計の本に、資産の段階に応じて収入・支出・投資を考える選択肢を加えました。', [('wealth-ladder', '資産段階ごとの戦略を考える')]),
    'realestate': ('購入後の経営まで見渡して選ぶ', '入門書の次に、収支・融資・管理を整理する本を追加。新刊と改訂版で学べる範囲を比べられます。', [('realestate-success', '収益・資産保全まで見渡す'), ('realestate-roadmap', '物件調査から経営までの順番を学ぶ')]),
    'us': ('米国株の長期投資をデータから学ぶ', '始め方や配当の実践書に、歴史・金利・インフレから株式のリターンを検討する名著の第6版を加えました。', [('stocks-long-run', '長期投資の理論を深める')]),
    'dividend': ('配当利回りの先に、事業を見る', '企業の経営戦略に注目するシリーズ第3弾を追加しました。既存の第1作との重複や読み分けも紹介しています。', [('strong-dividend', '配当を支える経営戦略を学ぶ')]),
    'stocks': ('株のおすすめ本を、調べたいことから選ぶ', '決算資料を読む基礎、割安株を探す視点、IRでの企業との対話、育児と売買の両立という4つの選択肢を追加しました。', [('fundamentals', '決算書・会社四季報を読む'), ('waga-toushijutsu', '日本株の投資判断を深める'), ('ir-seminar', 'IRでの質問・事前準備を学ぶ'), ('mama-investor', '子育てと投資の経験を読む')]),
}

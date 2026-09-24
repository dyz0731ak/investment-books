"""Verified editorial selections. Update dates only after reviewing the sources."""

STOCK_SLUGS = ["peter-lynch", "mary-buffett", "kenmei", "mirai", "buffett-letters", "marks-20", "auto-mode-haitou"]

FEATURED = ["okane-no-daigaku", "losers-game", "random-walker", "psychology-money", "just-keep-buying", "peter-lynch"]

READING_NOTES = {
    "okane-no-daigaku": ("まずは家計の土台から", "図解でお金の全体像をつかむ", "入門"),
    "losers-game": ("長く続ける投資を学ぶ", "市場と付き合う考え方を身につける", "入門〜中級"),
    "random-walker": ("投資の根拠を深く知る", "理論と歴史をじっくり読む", "中級"),
    "psychology-money": ("値動きに心が揺れるなら", "お金との距離感を考え直す", "入門"),
    "just-keep-buying": ("積立を続ける理由を探す", "データから資産形成を考える", "入門〜中級"),
    "peter-lynch": ("個別株の目利きを学ぶ", "身近な企業を調べる視点を得る", "中級"),
}

NEW_BOOKS = [
    dict(slug="ai-bubble", title="AIバブル後の投資戦略", author="中村 仁", label="2026年の新刊", published="2026年7月15日発売", isbn="9784478125137",
         cover="https://www.diamond.co.jp/book/vh2s9k0000005gi9-img/9784478125137.jpg",
         source="https://www.diamond.co.jp/book/9784478125137.html",
         source_label="ダイヤモンド社・書籍情報",
         desc="AI関連株への集中が気になる人に。債券・為替も含めた分散の考え方を扱う一冊です。",
         note="出版社の目次では、債券・為替の知識からポートフォリオまでを扱っています。相場予測の当たり外れだけでなく、分散の前提を確かめる入口として選びました。",
         caution="タイトルは将来のバブル崩壊を保証するものではありません。提案する資産配分の前提やコストを確認して読みたい本です。",
         related="random-walker", related_label="分散の基礎を名著で読む"),
    dict(slug="mama-investor", title="ママ投資家が育休中に1億貯めた株式投資", author="ちょる子", label="売れ筋に登場", published="2026年5月刊", isbn="9784478122983",
         cover="https://www.diamond.co.jp/book/vh2s9k0000001qoi-img/9784478122983.jpg",
         source="https://www.diamond.co.jp/book/9784478122983.html",
         source_label="ダイヤモンド社・書籍情報",
         desc="育児と仕事の合間の株式投資。その経験と売買の考え方を知りたい人へ。",
         note="トーハンの2026年6月8日〜14日集計で一般書2位。出版社の目次にある大型株の売買や信用取引について、時間の使い方とリスク管理を併せて確認したい本です。",
         caution="著者の資産額は個人の実績です。短期売買・信用取引は損失が大きくなる場合があり、投資初心者全員の最初の一冊とは位置づけていません。",
         related="peter-lynch", related_label="個別株を学ぶ定番も読む"),
    dict(slug="wealth-ladder", title="THE WEALTH LADDER 富の階段", author="ニック・マジューリ", label="話題のテーマ", published="2025年11月刊", isbn="9784478121368",
         cover="https://www.diamond.co.jp/book/kl8je0000000ck4a-img/9784478121368.jpg",
         source="https://www.diamond.co.jp/book/9784478121368.html",
         source_label="ダイヤモンド社・書籍情報",
         desc="資産の段階が変わると、選ぶ戦略も変わる。次のステップを考えたい人へ。",
         note="出版社の目次では、資産段階ごとに収入・投資・事業・資産防衛を考えます。『JUST KEEP BUYING』を読んだ後、投資の続け方から人生全体の戦略へ視野を広げる候補です。",
         caution="2025年刊の話題書です。日本の制度や自分の家計に、そのまま当てはまるとは限りません。",
         related="just-keep-buying", related_label="前作との違いを考える"),
]

FAQ = [
    ("投資初心者は、どの本から読むのがおすすめですか？", "家計の見直しからなら『お金の大学』、長期投資の考え方からなら『敗者のゲーム』が入口になります。理論を詳しく学びたい方は『ウォール街のランダム・ウォーカー』へ。目的と読みやすさを比較して選べます。", "/compare/first-investment-books/", "最初の3冊を比較する"),
    ("株のおすすめ本と、投資信託の本はどう違いますか？", "個別株の本は企業の利益・競争力・株価と価値の違いを学びます。インデックス投資の本は市場全体への分散・コスト・長期保有を重視します。自分で企業を調べたいか、仕組みを作って続けたいかで選ぶと整理しやすくなります。", "/stocks/", "株のおすすめ本を見る"),
    ("古い名著と新刊、どちらを選べばよいですか？", "長期・分散・投資家心理などの原則は名著で、制度や最近のテーマは刊行年を確認した本で補うと読み分けやすくなります。NISA・税制などは本の説明だけでなく公式情報も確認しましょう。", "/new/", "新刊・話題の本を見る"),
    ("掲載順は売上ランキングですか？", "定番の本棚は編集上の選書です。売上順位や購入者の口コミ平均ではありません。売れ筋の紹介には確認できた集計期間と情報源を示し、新刊の書誌紹介は読了レビューと区別しています。", "/about/#review-policy", "編集・評価方針を読む"),
]

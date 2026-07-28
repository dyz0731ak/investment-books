#!/usr/bin/env python3
"""
迷える子羊たちの株ノート ── 複数ページ静的サイト ビルド

生成物:
  /                       … トップ（総合ランキング＋カテゴリ導線＋ガイド導線）
  /<theme>/               … 目的別ランキングページ（初心者/NISA/インデックス/バフェット/FIRE/不動産/米国株）
  /books/<slug>/          … 個別本レビュー（タイトル/著者/要点/誰におすすめ/購入リンク）
  /guide/                 … 投資本の選び方・読む順ガイド

楽天ブックスAPI（新仕様 openapi.rakuten.co.jp）で 表紙/著者/価格/楽天アフィリ購入リンク を取得。
紹介文・レビュー・ランキングは当サイトのオリジナル（出版社コピーは転載しない）。
認証情報は環境変数: RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY, RAKUTEN_AFFILIATE_ID
"""
from __future__ import annotations
import os, sys, json, html, re, time, shutil, datetime
import urllib.parse
import requests

API = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://stock-overflow24.com/", "Origin": "https://stock-overflow24.com"}
SITE = "https://stock-overflow24.com"
SITE_NAME = "迷える子羊たちの株ノート"
SITE_TAGLINE = "迷える子羊たちへ。投資の“はじめの一冊”を。"
JST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(JST)
UPDATED = os.environ.get("SITE_UPDATED", TODAY.strftime("%Y.%m.%d"))
SITEMAP_LASTMOD = os.environ.get("SITE_LASTMOD", TODAY.strftime("%Y-%m-%d"))
CONTACT_EMAIL = "info@stock-overflow24.com"  # お問い合わせ表示用（ConoHa WING側でメールボックス作成が必要）
CSS_VER = "1"  # style.css のキャッシュバスター（main内でハッシュに更新）
GA_ID = os.environ.get("GA4_ID", "")  # GA4測定ID（環境変数。未設定なら計測タグは出力されない）


ADSENSE_CLIENT = "ca-pub-8504127793204920"


def adsense_head():
    # Google AdSense（Auto Ads）。サイト登録はルートドメイン単位のため yougo と共通。
    return (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
            f'?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>')


def ga_head():
    if not GA_ID:
        return ""
    return f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>"""


def ga_click_script():
    # アフィリンクのクリックをGA4イベントとして計測（gtag未読込なら何もしない）
    return """<script>
document.addEventListener('click',function(e){var a=e.target.closest?e.target.closest('a.btn-amazon,a.btn-rakuten,a.btn-yahoo'):null;
if(!a&&e.target.closest){a=e.target.closest('a[data-store]');}
if(a&&typeof gtag==='function'){var s=a.dataset.store||(a.classList.contains('btn-amazon')?'amazon':(a.classList.contains('btn-rakuten')?'rakuten':'yahoo'));gtag('event','affiliate_click',{store:s,book_slug:a.dataset.book||'',book_title:a.dataset.title||'',cta_position:a.dataset.cta||'',link_url:a.href,page:location.pathname});}},true);
</script>"""

# ── 目的別テーマ ──
THEMES = [
    dict(slug="beginner", name="初心者向け", emoji="",
         lead="「何から始めればいい？」という投資初心者が、まず1冊で全体像をつかめる定番をまとめました。"),
    dict(slug="nisa", name="NISA・つみたて", emoji="",
         lead="新NISA・つみたて投資をこれから始める人へ。口座選びから銘柄まで、手を動かすための実践書。"),
    dict(slug="index", name="インデックス投資", emoji="",
         lead="「市場全体を低コストで持ち続ける」——インデックス投資の理論と実践を学べる名著。"),
    dict(slug="buffett", name="バフェット流・バリュー投資", emoji="",
         lead="ウォーレン・バフェットとその源流。価格と価値を分けて考える、王道のバリュー投資。"),
    dict(slug="fire", name="FIRE・経済的自由", emoji="",
         lead="お金との付き合い方を見直し、経済的自由（FIRE）を目指すためのマインドと戦略。"),
    dict(slug="realestate", name="不動産投資", emoji="",
         lead="株式とは違う資産クラス、不動産投資の基礎と始め方を学べる入門書。"),
    dict(slug="us", name="米国株投資", emoji="",
         lead="長期で世界をリードしてきた米国株。配当・成長・指数の活かし方を学ぶ。"),
    dict(slug="dividend", name="高配当・配当株", emoji="",
         lead="配当をコツコツ受け取りながら資産を育てる、高配当・連続増配スタイルの本。"),
]
THEME_NAME = {t["slug"]: t["name"] for t in THEMES}

# カテゴリページを単なる書影一覧にしないための、選び方と注意点。
# 制度・税制・相場環境が変わっても使える原則に限定する。
THEME_GUIDES = {
    "beginner": dict(
        points=["専門用語を図や具体例で説明しているか", "商品選びより先に家計・リスク・長期運用を扱っているか", "利益だけでなく損失の可能性も説明しているか"],
        caution="最初から個別銘柄や短期売買だけに絞らず、家計管理・分散・長期運用の全体像を学べる本を優先します。"),
    "nisa": dict(
        points=["制度の説明だけでなく運用を続ける考え方があるか", "手数料・分散・リスクを扱っているか", "制度変更後も残る原則を学べるか"],
        caution="NISAの制度・対象商品・税制は改正されることがあります。制度の最新情報は金融庁などの公式情報でも確認してください。"),
    "index": dict(
        points=["低コストの重要性を説明しているか", "長期・分散の根拠が示されているか", "暴落時にも続ける考え方を学べるか"],
        caution="過去の市場データは将来の成果を保証しません。理論だけでなく、自分が続けられる資産配分と値動きの許容範囲も考えます。"),
    "buffett": dict(
        points=["価格と企業価値を分けて考えているか", "決算・競争優位・経営を見る視点があるか", "成功例だけでなく判断の限界も扱っているか"],
        caution="海外企業や過去の会計データを扱う本は、現在の制度・市場環境と異なる場合があります。考え方と具体例を分けて読みます。"),
    "fire": dict(
        points=["必要資産を数字で考えられるか", "運用だけでなく支出・収入も扱っているか", "取り崩しや想定外の支出も考慮しているか"],
        caution="必要資産や実現年数は、家族構成・住居・収入・相場によって大きく変わります。他人の成功例をそのまま再現できるとは限りません。"),
    "realestate": dict(
        points=["物件選びだけでなく融資・空室・修繕を扱っているか", "収益計算の前提が明確か", "失敗例や出口戦略も説明しているか"],
        caution="金利・税制・地域の需給で結果が変わります。書籍の事例は、現在の融資条件や物件価格でも成立するかを確認してください。"),
    "us": dict(
        points=["米国株を選ぶ根拠が説明されているか", "為替・税金・地域集中のリスクを扱っているか", "個別株と指数を区別しているか"],
        caution="円換算の成果は株価だけでなく為替にも左右されます。税制や配当課税の説明は、最新の公式情報でも確認してください。"),
    "dividend": dict(
        points=["利回りだけでなく配当の持続性を見ているか", "減配・業績悪化のリスクを扱っているか", "税引後の受取額や分散も考えているか"],
        caution="高い配当利回りだけで安全性は判断できません。利益・キャッシュフロー・配当方針を合わせて確認する必要があります。"),
}

# 検索意図が明確で、読者が「次に読む一冊」を決められる比較・選び方ページ。
COMPARISON_PAGES = [
    dict(
        slug="first-investment-books",
        title="投資初心者が最初に読むべき3冊を比較",
        short="初心者の最初の3冊",
        lead="家計から整えるか、インデックス投資の考え方から学ぶか。定番3冊を目的別に比べ、最初の一冊を決めます。",
        books=["okane-no-daigaku", "losers-game", "random-walker"],
    ),
    dict(
        slug="random-walker-vs-losers-game",
        title="『ウォール街のランダム・ウォーカー』と『敗者のゲーム』を比較",
        short="ランダム・ウォーカー vs 敗者のゲーム",
        lead="どちらもインデックス投資の名著ですが、厚さ・読みやすさ・得られる納得感は異なります。先に読むべき一冊を整理します。",
        books=["random-walker", "losers-game"],
    ),
    dict(
        slug="nisa-books",
        title="新NISAを始める前に読む本5選",
        short="新NISA前に読む5冊",
        lead="制度だけでなく、家計・商品選び・長期継続まで学べる5冊を、読む目的と順番で比較します。",
        books=["okane-no-daigaku", "hottarakashi", "okane-nekasete", "losers-game", "shin-nisa"],
    ),
    dict(
        slug="index-reading-order",
        title="インデックス投資本のおすすめの読む順番",
        short="インデックス本の読む順番",
        lead="入門、理論、実践、継続の4段階に分け、挫折しにくい読む順番をまとめます。",
        books=["okane-no-daigaku", "losers-game", "random-walker", "index-winner", "okane-nekasete"],
    ),
    dict(
        slug="dividend-books",
        title="高配当株・配当投資の本を目的別に比較",
        short="高配当投資本の比較",
        lead="配当再投資の理論、日本株・米国株の実践、仕組み化。目的の違う本を比べ、今の自分に合う一冊を選びます。",
        books=["mirai", "beikoku-haitou", "auto-mode-haitou", "tapazou-beikoku"],
    ),
]

# ── 書籍データ（紹介文・要点・レビューはオリジナル） ──
BOOKS = [
    dict(rank=1, slug="random-walker", q="ウォール街のランダム・ウォーカー", author="マルキール",
         themes=["index", "beginner"], tags=["不朽の定番", "インデックス投資"],
         who="まず1冊だけ選びたい投資初心者",
         desc="半世紀読み継がれる、インデックス投資の世界的バイブル。",
         points=["個別株やタイミング投資から卒業できる", "“ほったらかし”で良い理由が腑に落ちる"],
         review="「市場の値動きは誰にも予測できない。だからこそ低コストのインデックスファンドを長く持ち続けるのが最善」——本書が一貫して説くのはこのシンプルな結論です。専門用語は出てきますが、なぜ多くの個人投資家が“市場全体を買う”という選択にたどり着くのか、その理由を歴史とデータで腹落ちさせてくれます。最初の1冊として、遠回りせず本質に届く名著です。"),
    dict(rank=2, slug="losers-game", q="敗者のゲーム", author="エリス",
         themes=["index", "beginner"], tags=["初心者必読", "インデックス投資"],
         who="“なぜインデックスなのか”を短時間で知りたい人",
         desc="プロでも市場平均に勝ち続けるのは至難——その現実をやさしく解説。",
         points=["“なぜインデックスなのか”が短時間でわかる", "薄くて読みやすい"],
         review="アマチュアのテニスは「打ち勝つ」より「ミスを減らす」ゲーム——この比喩で、個人投資家は“勝とうとしない＝市場全体を持つ”のが合理的だと説きます。プロでも市場平均に勝ち続けるのは難しいという現実を、嫌味なくすっと理解させてくれる一冊。薄めで読みやすいので、投資を始める前の“心構え”づくりに最適です。"),
    dict(rank=3, slug="index-winner", q="インデックス投資は勝者のゲーム", author="ボーグル",
         themes=["index"], tags=["低コスト", "インデックス投資"],
         who="低コスト投資の原点を知りたい人",
         desc="低コスト・インデックスファンドを世に広めた本人が語る王道。",
         points=["“コストの低さ”が最強の武器だと納得できる", "長期・分散・低コストの原点を学べる"],
         review="世界最大級の運用会社バンガードを創り、低コスト・インデックスファンドを世に広めたジョン・ボーグル本人による一冊。手数料という“見えにくいコスト”が、長期のリターンをどれほど蝕むのかを繰り返し示します。読み終えると「コストの低さこそ個人投資家最大の武器」だと確信できます。"),
    dict(rank=4, slug="okane-no-daigaku", q="お金の大学", author="",
         themes=["beginner", "nisa"], tags=["超入門", "家計・節約"],
         who="投資の前に家計から整えたい人",
         desc="貯める・稼ぐ・増やす・守る・使う、お金の5つの力を図解で。",
         points=["投資より前に“固定費の見直し”から始められる", "イラスト中心で挫折しにくい"],
         review="「貯める・稼ぐ・増やす・守る・使う」というお金の5つの力を、図解たっぷりで体系的にまとめた超入門書。投資の話だけでなく、固定費の見直しなど“土台づくり”から始められるのが強み。何も知らない状態で最初に手に取る一冊として、挫折しにくくおすすめです。"),
    dict(rank=5, slug="hottarakashi", q="ほったらかし投資術", author="山崎元",
         themes=["nisa", "index", "beginner"], tags=["実践向け", "NISA・つみたて"],
         who="新NISAで“何をどう買うか”の答えが欲しい人",
         desc="日本の個人が何をどう買えばいいかに、具体的に答える実践書。",
         points=["口座開設〜銘柄選びまで具体的に進められる", "新NISAの活用イメージがつかめる"],
         review="「結局、日本の個人投資家は何をどう買えばいいの？」という問いに、口座・銘柄レベルまで具体的に答えてくれる実践書です。理論より“今日から手を動かす”ことに重きが置かれているので、新NISA時代に最初の一歩を踏み出すときの道しるべになります。"),
    dict(rank=6, slug="mirai", q="株式投資の未来", author="シーゲル",
         themes=["us", "dividend"], tags=["長期投資", "配当"],
         who="長期・配当再投資の力をデータで知りたい人",
         desc="派手な成長株より、配当を再投資する優良株が報われた——を実証。",
         points=["配当再投資の威力をデータで理解できる", "短期の値動きに振り回されなくなる"],
         review="過去の長期データをもとに「派手な成長株より、地味でも配当を着実に再投資する優良株のほうが報われてきた」ことを示した名著。長期投資と配当再投資の力を“感覚”ではなくデータで腹落ちさせてくれるので、短期の値動きに振り回されない軸ができます。"),
    dict(rank=7, slug="kenmei", q="賢明なる投資家", author="グレアム",
         themes=["buffett"], tags=["古典", "バリュー投資"],
         who="相場の本質・バリュー投資の原典に触れたい人",
         desc="バフェットの師が記した、バリュー投資の原典。",
         points=["“安全域”の考え方が身につく", "暴落時にうろたえない軸ができる"],
         review="ウォーレン・バフェットの師ベンジャミン・グレアムが記した、バリュー投資の原典。「価格」と「価値」を分けて考える姿勢や“安全域”の発想など、相場の本質を学びたい人の到達点です。やや骨太なので、投資に少し慣れてきた頃にじっくり読むのがおすすめ。"),
    dict(rank=8, slug="kanemochi-tousan", q="金持ち父さん貧乏父さん", author="キヨサキ",
         themes=["beginner", "fire"], tags=["マインド", "入門"],
         who="お金との向き合い方をまず変えたい人",
         desc="資産と負債の違い、お金に働いてもらう——考え方を変える一冊。",
         points=["お金の“考え方”が根本から変わる", "投資を始める動機づけになる"],
         review="「資産と負債の違い」「お金に働いてもらう」という、お金との向き合い方そのものを問い直す世界的ベストセラー。具体的な投資手法というより、最初のマインドセットを作るための一冊。読むと“なぜ投資するのか”の動機がはっきりします。"),
    dict(rank=9, slug="okane-nekasete", q="お金は寝かせて増やしなさい", author="水瀬ケンイチ",
         themes=["index", "nisa", "beginner"], tags=["実践", "インデックス投資"],
         who="インデックス積立を“続ける”コツを知りたい人",
         desc="個人インデックス投資家による、続けるための実践と心構え。",
         points=["暴落でも積立を続けられる考え方が身につく", "日本の個人目線で具体的"],
         review="長年インデックス投資を実践してきた個人投資家による、“理論”より“続け方”に寄った実践書。暴落時にどう心を保つか、淡々と積み立てるための仕組みづくりなど、続けるためのリアルなコツが詰まっています。インデックス投資を始めた人の二冊目に最適。"),
    dict(rank=10, slug="3000en", q="3000円投資生活", author="横山光昭",
         themes=["beginner", "nisa"], tags=["超入門", "少額"],
         who="少額から無理なく始めたい人",
         desc="月3000円から始める、はじめての投資のハードルを下げる入門。",
         points=["少額だから心理的ハードルが低い", "家計の見直しとセットで学べる"],
         review="「いきなり大きな額は怖い」という人に向けて、月3000円という少額から始める発想を示した入門書。投資のハードルをとことん下げてくれるので、“まず口座を開いて少しだけ買ってみる”の最初の一歩を後押ししてくれます。"),
    dict(rank=11, slug="psychology-money", q="サイコロジー・オブ・マネー", author="ハウセル",
         themes=["beginner", "fire"], tags=["マインド", "行動"],
         who="“続けられる人”の考え方を身につけたい人",
         desc="知識より“ふるまい”。お金とうまく付き合う普遍的な原則。",
         points=["市場より自分の感情をコントロールする大切さがわかる", "短い話の集まりで読みやすい"],
         review="お金で成功するかどうかは、頭の良さより“ふるまい（行動）”で決まる——そんな普遍的な原則を、短いエピソードの積み重ねで伝えてくれる一冊。手法ではなく、長く投資を続けるための“心の持ち方”を整えたい人に響きます。"),
    dict(rank=12, slug="fire-saikyo", q="FIRE 最強の早期リタイア術", author="シェン",
         themes=["fire"], tags=["FIRE", "戦略"],
         who="経済的自由（FIRE）を本気で目指す人",
         desc="支出最適化＋インデックス投資で早期リタイアを目指す実践書。",
         points=["FIREの数字（必要資産・取り崩し）が具体的", "再現性のある考え方"],
         review="徹底した支出の最適化と、インデックス中心の資産運用で早期リタイア（FIRE）を実現した著者による実践書。必要資産の考え方や取り崩しの戦略まで具体的で、“なんとなく憧れ”を“数字で計画する”レベルに引き上げてくれます。"),
    dict(rank=13, slug="buffett-letters", q="バフェットからの手紙", author="カニンガム",
         themes=["buffett"], tags=["バリュー投資", "経営"],
         who="バフェットの思考を直接たどりたい人",
         desc="株主への手紙から、バフェットの投資哲学を体系的に。",
         points=["長期保有・優良企業選びの考え方が学べる", "投資だけでなく経営の視点も"],
         review="バフェットが株主に宛てた手紙を、テーマごとに整理した一冊。優良な企業を見極めて長く持つという哲学が、本人の言葉でたどれます。個別株・バリュー投資に興味が出てきた人が、王道の考え方に触れるのに向いています。"),
    dict(rank=14, slug="tapazou-beikoku", q="お金が増える 米国株超楽ちん投資術", author="たぱぞう",
         themes=["us", "nisa"], tags=["米国株", "実践"],
         who="米国株・米国ETFを具体的に始めたい人",
         desc="人気ブロガーによる、米国株・ETF投資の実践入門。",
         points=["米国ETFの選び方が具体的", "新NISAとの相性も学べる"],
         review="米国株投資で知られる人気ブロガーによる実践入門。なぜ米国株なのか、どのETFをどう選ぶかが具体的で、これから米国株・米国ETFを始めたい人の“最初の地図”になります。新NISAでの活用ともつながる内容です。"),
    dict(rank=15, slug="beikoku-haitou", q="バカでも稼げる 米国株高配当投資", author="バフェット太郎",
         themes=["us", "dividend"], tags=["米国株", "高配当"],
         who="米国株の高配当・連続増配に興味がある人",
         desc="米国株の高配当・連続増配株への投資をやさしく解説。",
         points=["高配当・連続増配の魅力がわかる", "ルール化された投資法"],
         review="米国株の高配当株・連続増配株への投資を、軽妙な語り口でやさしく解説した一冊。配当を軸にしたルールベースの投資法が示されており、「成長株より配当でコツコツ」というスタイルに興味がある人の入り口になります。"),
    dict(rank=16, slug="apato-ittou", q="まずはアパート一棟、買いなさい", author="石原博光",
         themes=["realestate"], tags=["不動産", "実践"],
         who="不動産投資の現実的な始め方を知りたい人",
         desc="実体験ベースで語る、不動産投資のリアルな始め方。",
         points=["物件選び・融資・運営の流れがつかめる", "失敗も含めた実体験"],
         review="自身の実体験をもとに、不動産投資の始め方をリアルに語る一冊。物件の選び方や融資、運営の流れなど、株式とは異なる“事業としての投資”の感覚がつかめます。不動産という資産クラスに興味が出てきた人の最初の一冊に。"),
    dict(rank=17, slug="fudosan-kyokasho", q="世界一やさしい 不動産投資の教科書", author="浅井佐知子",
         themes=["realestate"], tags=["不動産", "超入門"],
         who="不動産投資の用語・全体像から学びたい人",
         desc="図解中心で、不動産投資の基礎をゼロから解説。",
         points=["専門用語をやさしく整理できる", "全体像を最初につかめる"],
         review="不動産投資の基礎を、図解中心でゼロからやさしく解説した入門書。専門用語が多くて挫折しがちな分野を、全体像から整理してくれます。「アパート一棟」のような実践書の前に、土台を作るのにちょうど良い一冊です。"),
    dict(rank=18, slug="mary-buffett", q="バフェットの銘柄選択術", author="バフェット",
         themes=["buffett"], tags=["バリュー投資", "銘柄選び"],
         who="バフェット流の銘柄の見方を知りたい人",
         desc="バフェットの“買うべき企業”の見極め方を具体的に。",
         points=["“長期で強い企業”の条件がわかる", "数字の見方が具体的"],
         review="バフェットがどんな企業を“買うべき”と考えるのか、その見極め方を具体的に解説した一冊。長期で強さを保つ企業の条件や数字の見方が整理されており、個別株でバリュー投資に挑戦したい人の参考になります。"),
    dict(rank=19, slug="okane-fuyashikata", q="難しいことはわかりませんが、お金の増やし方を教えてください", author="山崎元",
         themes=["beginner", "index", "nisa"], tags=["超入門", "対話形式"],
         who="専門用語が苦手で、結論から知りたい人",
         desc="対話形式で“結局どうすればいいか”をズバッと教えてくれる超入門。",
         points=["難しい用語ゼロで結論にたどり着ける", "1〜2時間でサッと読める"],
         review="お金や投資にくわしくない聞き手と専門家の対話形式で、「結局、何をどうすればいいの？」にズバッと答えてくれる超入門書。難しい用語を避けつつ、低コストの投資信託を淡々と積み立てる、という結論まで最短距離で導いてくれます。とにかく1冊で迷いを消したい人に。"),
    dict(rank=20, slug="jason-okane", q="ジェイソン流お金の増やし方", author="厚切りジェイソン",
         themes=["beginner", "index", "nisa"], tags=["超入門", "節約＋投資"],
         who="節約と投資をセットでゆるく始めたい人",
         desc="芸人でもある著者が実践する、節約＋米国インデックス投資のシンプル術。",
         points=["支出を抑えてコツコツ積み立てる流れがわかる", "肩の力が抜けて読める"],
         review="お笑い芸人でIT企業役員でもある著者が、自身で実践する“支出を抑えて、余ったお金を米国インデックスに淡々と積み立てる”というシンプルな方法を語る一冊。ユーモアがありつつ実用的で、難しく考えず「まず始める」気持ちにさせてくれます。"),
    dict(rank=21, slug="just-keep-buying", q="JUST KEEP BUYING", author="マジューリ",
         themes=["index", "beginner"], tags=["データ重視", "積立"],
         who="“続けて買い続ける”の根拠をデータで知りたい人",
         desc="データ分析ブロガーが、貯蓄・投資の最適解をデータで検証。",
         points=["“いつ買うか”より“買い続ける”が効く理由がわかる", "感覚でなくデータで納得できる"],
         review="人気データ分析ブロガーが、貯蓄と投資にまつわる“よくある疑問”をデータで検証した一冊。タイトルどおり「（タイミングを計らず）ただ買い続ける」ことの強さを示し、感情ではなく数字で投資行動を決める助けになります。"),
    dict(rank=22, slug="peter-lynch", q="ピーター・リンチの株で勝つ", author="リンチ",
         themes=["buffett"], tags=["個別株", "成長株"],
         who="個別株で“身近な会社”から探したい人",
         desc="伝説のファンドマネジャーが説く、身近な視点からの銘柄発掘。",
         points=["生活者目線で有望株を探す視点が身につく", "個別株の楽しさと注意点がわかる"],
         review="圧倒的な成績を残した伝説のファンドマネジャーが、「身近な生活の中に有望株のヒントがある」という独自の視点を語る名著。インデックスとは別に、個別株を自分で選ぶ面白さと、その際の調べ方・注意点を教えてくれます。"),
    dict(rank=23, slug="marks-20", q="投資で一番大切な20の教え", author="マークス",
         themes=["buffett"], tags=["リスク", "相場の心得"],
         who="リスクと向き合う“考え方”を深めたい人",
         desc="一流投資家が説く、リスクと市場サイクルとの向き合い方。",
         points=["“リスク＝価格”という視点が身につく", "強気・弱気に流されない軸ができる"],
         review="名門運用会社の創業者が、長年の投資から得た“最も大切な考え方”をテーマごとに語る一冊。価格とリスクの関係や市場サイクルとの付き合い方など、手法ではなく「考え方」を深めたい中級者に響きます。"),
    dict(rank=24, slug="die-with-zero", q="DIE WITH ZERO", author="パーキンス",
         themes=["fire"], tags=["お金と人生", "使い方"],
         who="貯めるだけでなく“使い方”も考えたい人",
         desc="資産を“ゼロで死ぬ”発想で、お金と経験の最適配分を考える。",
         points=["お金を貯める目的を問い直せる", "経験への投資という視点が得られる"],
         review="「お金は使ってこそ価値になる」という視点から、人生のどのタイミングでお金を使うべきかを問い直す一冊。FIREや資産形成を“貯めること”だけで終わらせず、経験や時間とのバランスを考えるきっかけになります。"),
    dict(rank=25, slug="honki-fire", q="本気でFIREをめざす人のための資産形成入門", author="穂高唯希",
         themes=["fire", "dividend"], tags=["FIRE", "高配当"],
         who="日本でFIREを具体的に目指したい人",
         desc="30代でセミリタイアした著者による、高配当軸のFIRE実践入門。",
         points=["支出最適化＋高配当株の具体策がわかる", "日本の個人目線で再現性が高い"],
         review="支出の最適化と高配当株への投資で、30代でセミリタイアを実現した著者による実践入門。日本の個人がFIREを目指す際の具体的な家計設計や銘柄の考え方が語られ、“憧れ”を“計画”に変えてくれます。"),
    dict(rank=26, slug="shin-nisa", q="新NISA完全攻略", author="山口貴大",
         themes=["nisa", "index"], tags=["新NISA", "実践"],
         who="新NISAを最大限に活かしたい人",
         desc="新NISAの制度と使い方を、初心者向けに体系的に解説。",
         points=["新NISAの枠の使い方が整理できる", "銘柄選びの方針までわかる"],
         review="新NISAの制度をやさしく整理し、つみたて投資枠・成長投資枠をどう使い分けるか、どんな銘柄を選ぶかまで体系的に解説した一冊。制度が新しくなって「結局どう使えばいい？」と迷う人の道案内になります。"),
    dict(rank=27, slug="auto-mode-haitou", q="オートモードで月18.5万円が入ってくる 高配当株投資", author="長期株式投資",
         themes=["dividend"], tags=["高配当", "日本株"],
         who="配当で“自動的に入ってくる”仕組みを作りたい人",
         desc="高配当・連続増配株を長期保有し、配当を積み上げる手法を解説。",
         points=["高配当株の選び方・続け方がわかる", "配当でキャッシュフローを作る発想"],
         review="高配当株・連続増配株を長期で持ち、配当という“自動的に入ってくる収入”を積み上げていく手法を解説した一冊。銘柄の選び方や続けるための考え方が具体的で、値上がり益より配当重視のスタイルに興味がある人の入り口になります。"),
]


# ───────── 楽天API ─────────
def rakuten_lookup(book, app_id, access_key, aff_id):
    auth = {"applicationId": app_id, "accessKey": access_key, "affiliateId": aff_id,
            "format": "json", "hits": 1, "sort": "sales"}
    queries = []
    if book.get("author"):
        queries.append({"title": book["q"], "author": book["author"]})
    queries.append({"title": book["q"]})
    for params in queries:
        items = None
        for attempt in range(3):
            try:
                r = requests.get(API, params={**auth, **params}, headers=HEADERS, timeout=20)
                if r.status_code == 200 and '"Items"' in r.text:
                    items = r.json().get("Items") or []
                    break
                time.sleep(1.5 * (attempt + 1))
            except Exception as e:
                print(f"  [warn] {book['q']}: {e}", file=sys.stderr); time.sleep(1.5 * (attempt + 1))
        if not items:
            time.sleep(0.8); continue
        it = items[0]["Item"]
        img = re.sub(r"_ex=\d+x\d+", "_ex=400x400", it.get("largeImageUrl") or it.get("mediumImageUrl") or "")
        return {"r_title": it.get("title", book["q"]), "r_author": it.get("author", ""),
                "cover": img, "price": it.get("itemPrice"),
                "url": it.get("affiliateUrl") or it.get("itemUrl") or ""}
    return {"r_title": book["q"], "r_author": "", "cover": "", "price": None, "url": ""}


# ── 編集部評価（5点満点・本物の自社評価。構造化データReviewのreviewRatingに使用） ──
# Googleは評価の捏造を禁止。これは編集部の実際の推薦度であり、ページ上にも可視表示する。
# 値の調整はここだけ編集すればよい。
RATINGS = {
    "random-walker": 4.9, "losers-game": 4.7, "index-winner": 4.7, "okane-no-daigaku": 4.6,
    "hottarakashi": 4.6, "mirai": 4.7, "kenmei": 4.8, "kanemochi-tousan": 4.3,
    "okane-nekasete": 4.5, "3000en": 4.2, "psychology-money": 4.8, "fire-saikyo": 4.4,
    "buffett-letters": 4.6, "tapazou-beikoku": 4.4, "beikoku-haitou": 4.3, "apato-ittou": 4.2,
    "fudosan-kyokasho": 4.3, "mary-buffett": 4.5, "okane-fuyashikata": 4.5, "jason-okane": 4.3,
    "just-keep-buying": 4.6, "peter-lynch": 4.7, "marks-20": 4.7, "die-with-zero": 4.6,
    "honki-fire": 4.4, "shin-nisa": 4.4, "auto-mode-haitou": 4.4,
}


def build_books():
    app_id = os.environ.get("RAKUTEN_APP_ID", ""); access_key = os.environ.get("RAKUTEN_ACCESS_KEY", "")
    aff_id = os.environ.get("RAKUTEN_AFFILIATE_ID", ""); have = bool(app_id and access_key)
    # 楽天APIキーが無いときは、前回ビルドのキャッシュ(data/books.json)からカバー/アフィリンク等を再利用
    cache = {}
    try:
        with open(os.path.join(HERE, "data", "books.json"), encoding="utf-8") as f:
            for c in json.load(f):
                cache[c.get("slug")] = c
    except Exception:
        pass
    out = []
    for b in BOOKS:
        if have:
            info = rakuten_lookup(b, app_id, access_key, aff_id)
        elif b["slug"] in cache:
            c = cache[b["slug"]]
            info = {"r_title": c.get("r_title", b["q"]), "r_author": c.get("r_author", ""),
                    "cover": c.get("cover", ""), "price": c.get("price"), "url": c.get("url", "")}
        else:
            info = {"r_title": b["q"], "r_author": "", "cover": "", "price": None, "url": ""}
        nb = {**b, **info}
        nb["title"] = b["q"]            # 表示タイトルは短い検索名で統一（版表記の冗長さを避ける）
        nb["author_disp"] = info["r_author"] or b.get("author", "")
        nb["rating"] = RATINGS.get(b["slug"], 4.5)   # 編集部評価
        out.append(nb)
        print(f"  #{b['rank']:2} {b['slug']:18} cover={'Y' if info['cover'] else '-'} aff={'Y' if info['url'] else '-'}", file=sys.stderr)
        if have: time.sleep(1.0)
    return out


# ───────── HTML部品 ─────────
def esc(s): return html.escape(str(s or ""))
def amazon_search(t): return "https://www.amazon.co.jp/s?k=" + requests.utils.quote(t)


def _isbn13_to_10(i13):
    core = i13[3:12]
    s = sum((10 - idx) * int(c) for idx, c in enumerate(core))
    chk = (11 - (s % 11)) % 11
    return core + ("X" if chk == 10 else str(chk))


def amazon_product_url(b):
    """カバーURL中のISBN13からAmazon商品ページ直リンクを生成。取れなければ検索URLにフォールバック。"""
    m = re.search(r"(97[89]\d{10})", b.get("cover", "") or "")
    if m:
        return "https://www.amazon.co.jp/dp/" + _isbn13_to_10(m.group(1))
    return amazon_search(b["title"])


# もしもアフィリエイト経由のAmazonリンクに変換（環境変数で a_id / p_id / pc_id / pl_id を指定）
MOSHIMO_AID = os.environ.get("MOSHIMO_AMAZON_AID", "")
MOSHIMO_PID = os.environ.get("MOSHIMO_AMAZON_PID", "")
MOSHIMO_PCID = os.environ.get("MOSHIMO_AMAZON_PCID", "")
MOSHIMO_PLID = os.environ.get("MOSHIMO_AMAZON_PLID", "")
AMAZON_ASSOCIATE_TAG = os.environ.get("AMAZON_ASSOCIATE_TAG", "")


def has_amazon_affiliate():
    return bool((MOSHIMO_AID and MOSHIMO_PID and MOSHIMO_PCID and MOSHIMO_PLID) or AMAZON_ASSOCIATE_TAG)


def amazon_url(b):
    raw = amazon_product_url(b)
    if MOSHIMO_AID and MOSHIMO_PID and MOSHIMO_PCID and MOSHIMO_PLID:
        return (f"https://af.moshimo.com/af/c/click?a_id={MOSHIMO_AID}&p_id={MOSHIMO_PID}"
                f"&pc_id={MOSHIMO_PCID}&pl_id={MOSHIMO_PLID}&url=" + requests.utils.quote(raw, safe=""))
    if AMAZON_ASSOCIATE_TAG:
        sep = "&" if "?" in raw else "?"
        return raw + sep + urllib.parse.urlencode({"tag": AMAZON_ASSOCIATE_TAG})
    return ""


# もしもアフィリエイト経由の楽天市場リンク（提携済み・HTMLに出る公開アフィリID）
RAKUTEN_MOSHIMO = "https://af.moshimo.com/af/c/click?a_id=4575690&p_id=54&pc_id=54&pl_id=616&url="
def _rakuten_dest(b):
    """素の楽天商品URLを返す。楽天直アフィリリンク(hb.afl)なら pc= から商品URLを復元、無ければタイトル検索。"""
    u = b.get("url") or ""
    m = re.search(r"[?&]pc=([^&]+)", u)
    if m:
        return urllib.parse.unquote(m.group(1))
    if u.startswith("http") and "hb.afl.rakuten" not in u:
        return u
    return "https://search.rakuten.co.jp/search/mall/" + requests.utils.quote(b["q"]) + "/"
def rakuten_url(b): return RAKUTEN_MOSHIMO + requests.utils.quote(_rakuten_dest(b), safe="")


# もしもアフィリエイト経由のYahoo!ショッピングリンク（提携済み・HTMLに出る公開アフィリID）
YAHOO_MOSHIMO = "https://af.moshimo.com/af/c/click?a_id=5620985&p_id=1225&pc_id=1925&pl_id=18502&url="
def yahoo_search(t): return "https://shopping.yahoo.co.jp/search?p=" + requests.utils.quote(t)
def yahoo_url(b): return YAHOO_MOSHIMO + requests.utils.quote(yahoo_search(b["q"]), safe="")


def head(title, desc, path, extra_head=""):
    canon = f"{SITE}{path}"
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} | {SITE_NAME}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:image" content="{SITE}/assets/sheep-icon.png">
<meta property="article:modified_time" content="{TODAY.isoformat()}">
<link rel="canonical" href="{canon}">
<link rel="icon" type="image/png" href="/assets/sheep-icon.png">
<link rel="apple-touch-icon" href="/assets/sheep-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css?v={CSS_VER}">
{extra_head}
{adsense_head()}
{ga_head()}
</head>
<body>"""


def stars_html(rating):
    """5点満点の星評価。★のみ使用し、小数分はCSSで部分塗り（フォント依存なし）。"""
    pct = round(max(0, min(5, rating)) / 5 * 100, 1)
    return (f'<div class="bd-rating" aria-label="編集部評価 {rating} / 5">'
            f'<span class="bd-stars"><span class="bd-stars-fill" style="width:{pct}%"></span></span>'
            f'<span class="bd-rating-num">{rating}</span>'
            f'<span class="bd-rating-cap">編集部評価</span></div>')


def book_jsonld(b, path):
    """書籍ページの構造化データ（Book + 単一の編集部Review）。★リッチリザルト狙い。"""
    data = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": b["title"],
        "url": f"{SITE}{path}",
        "dateModified": TODAY.date().isoformat(),
        "review": {
            "@type": "Review",
            "author": {"@type": "Organization", "name": SITE_NAME},
            "dateModified": TODAY.date().isoformat(),
            "reviewRating": {"@type": "Rating", "ratingValue": b["rating"], "bestRating": 5, "worstRating": 1},
            "reviewBody": b["review"],
        },
    }
    if b.get("author_disp"):
        data["author"] = {"@type": "Person", "name": b["author_disp"]}
    if b.get("cover"):
        data["image"] = b["cover"]
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'


def header():
    cats = "".join(f'<a href="/{t["slug"]}/">{esc(t["name"])}</a>' for t in THEMES)
    return f"""<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/">
      <img class="brand-mark" src="/assets/sheep-icon.png" alt="{SITE_NAME}" width="40" height="50">
      <span class="brand-text">
        <span class="brand-name">{SITE_NAME}</span>
        <span class="brand-tagline">{SITE_TAGLINE}</span>
      </span>
    </a>
    <input type="checkbox" id="navToggle" class="nav-toggle" hidden>
    <label for="navToggle" class="nav-btn" aria-label="メニュー"><span></span><span></span><span></span></label>
    <nav class="gnav"><a href="/">ホーム</a><a href="/guide/">選び方ガイド</a><a href="/compare/first-investment-books/">本を比較</a><a href="/#categories">カテゴリ</a></nav>
  </div>
  <nav class="cat-bar"><div class="cat-bar-inner"><a href="/" class="cat-home">総合</a>{cats}</div></nav>
</header>"""


def breadcrumb(items):
    # items: list of (label, href or None)
    parts = []
    for label, href in items:
        if href:
            parts.append(f'<a href="{esc(href)}">{esc(label)}</a>')
        else:
            parts.append(f'<span>{esc(label)}</span>')
    return '<nav class="breadcrumb">' + ' <i>›</i> '.join(parts) + '</nav>'


def affiliate_disclosure():
    amazon = ""
    if has_amazon_affiliate():
        amazon = "Amazonのアソシエイトとして適格販売により収入を得ています。また"
    return (f"※当サイトは、{amazon}楽天アフィリエイト・もしもアフィリエイト等の"
            "アフィリエイトプログラムを利用しており、リンク経由でのご購入により"
            "運営者に紹介料が支払われる場合があります。")


def amazon_privacy_item():
    if not has_amazon_affiliate():
        return ""
    return "<li>当サイトは、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定された、Amazonアソシエイト・プログラムの参加者です。適格販売により収入を得ています。</li>"


def footer():
    cats = "".join(f'<a href="/{t["slug"]}/">{esc(t["name"])}</a>' for t in THEMES[:5])
    return f"""<footer class="site-footer">
  <div class="footer-inner">
    <p class="footer-brand"><img class="footer-mark" src="/assets/sheep-icon.png" alt="" width="28" height="35">{SITE_NAME}</p>
    <nav class="footer-nav"><a href="/">ホーム</a><a href="/guide/">選び方ガイド</a><a href="/compare/first-investment-books/">本を比較</a>{cats}</nav>
    <nav class="footer-nav"><a href="https://dashboard.stock-overflow24.com/">投資の砦</a><a href="https://yougo.stock-overflow24.com/">用語辞典</a><a href="/about/">運営者情報</a><a href="/contact/">お問い合わせ</a><a href="/privacy/">プライバシーポリシー</a></nav>
    <p class="footer-note">{esc(affiliate_disclosure())}</p>
    <p class="footer-note">※掲載内容は書籍の紹介であり、特定の投資・銘柄を推奨するものではありません。投資は自己責任で行ってください。</p>
    <p class="footer-copy">© 2026 {SITE_NAME}</p>
  </div>
</footer>
{ga_click_script()}
</body>
</html>"""


def cta(b, context="primary"):
    buttons = []
    aurl = amazon_url(b)
    if aurl:
        buttons.append(f'<a class="btn btn-amazon" href="{esc(aurl)}" target="_blank" rel="sponsored nofollow noopener" data-store="amazon" data-book="{esc(b["slug"])}" data-title="{esc(b["title"])}" data-cta="{esc(context)}" aria-label="{esc(b["title"])}をAmazonで見る">Amazon</a>')
    buttons.append(f'<a class="btn btn-rakuten" href="{esc(rakuten_url(b))}" target="_blank" rel="sponsored nofollow noopener" data-store="rakuten" data-book="{esc(b["slug"])}" data-title="{esc(b["title"])}" data-cta="{esc(context)}" aria-label="{esc(b["title"])}を楽天ブックスで見る">楽天ブックス</a>')
    buttons.append(f'<a class="btn btn-yahoo" href="{esc(yahoo_url(b))}" target="_blank" rel="sponsored nofollow noopener" data-store="yahoo" data-book="{esc(b["slug"])}" data-title="{esc(b["title"])}" data-cta="{esc(context)}" aria-label="{esc(b["title"])}をYahoo!ショッピングで見る">Yahoo!ショッピング</a>')
    return '<div class="book-cta" data-book="' + esc(b["slug"]) + '" data-cta="' + esc(context) + '">\n      ' + "\n      ".join(buttons) + "\n    </div>"


def store_choice_panel(b, context="shop_choice"):
    """購入先の迷いを減らすための小さな比較導線。価格断定はせず、用途で選ばせる。"""
    amazon = ""
    if has_amazon_affiliate():
        aurl = amazon_url(b)
        amazon = f"""<a class="shop-card shop-card-amazon" href="{esc(aurl)}" target="_blank" rel="sponsored nofollow noopener" data-store="amazon" data-book="{esc(b["slug"])}" data-title="{esc(b["title"])}" data-cta="{esc(context)}">
          <span class="shop-card-name">Amazon</span>
          <span class="shop-card-copy">普段Amazonで本を買う人向け。配送条件はリンク先で確認。</span>
        </a>"""
    amazon_line = amazon + "\n        " if amazon else ""
    return f"""<div class="shop-choice" aria-label="購入先の選び方">
      <div class="shop-choice-head">
        <span class="shop-choice-label">購入先の選び方</span>
        <p>使っているポイントや在庫状況で選んでください。</p>
      </div>
      <div class="shop-card-grid">
        {amazon_line}<a class="shop-card shop-card-rakuten" href="{esc(rakuten_url(b))}" target="_blank" rel="sponsored nofollow noopener" data-store="rakuten" data-book="{esc(b["slug"])}" data-title="{esc(b["title"])}" data-cta="{esc(context)}">
          <span class="shop-card-name">楽天ブックス</span>
          <span class="shop-card-copy">商品ページへ直接移動。楽天ポイントを使いたい人に。</span>
        </a>
        <a class="shop-card shop-card-yahoo" href="{esc(yahoo_url(b))}" target="_blank" rel="sponsored nofollow noopener" data-store="yahoo" data-book="{esc(b["slug"])}" data-title="{esc(b["title"])}" data-cta="{esc(context)}">
          <span class="shop-card-name">Yahoo!ショッピング</span>
          <span class="shop-card-copy">検索結果で価格・在庫を比較。PayPayを使う人に。</span>
        </a>
      </div>
      <p class="shop-choice-note">価格・送料・在庫・ポイント条件は変わるため、最終確認は各ショップで行ってください。</p>
    </div>"""


def cover_html(b, cls="book-cover"):
    if b.get("cover"):
        return f'<img class="{cls}" src="{esc(b["cover"])}" alt="{esc(b["title"])}の表紙" loading="lazy">'
    return f'<div class="{cls} book-cover--ph">{esc(b["title"])}</div>'


def book_card(b, show_rank=True):
    rank = b["rank"]
    rank_cls = f"book rank-{rank} is-top" if (show_rank and rank <= 3) else "book"
    rank_badge = f'<div class="book-rank"><span class="rank-num">{rank}</span></div>' if show_rank else ''
    tags = "".join(f'<span class="tag{" tag-gold" if i==0 else ""}">{esc(t)}</span>' for i, t in enumerate(b["tags"]))
    points = "".join(f"<li>{esc(p)}</li>" for p in b["points"])
    price = f'<span class="book-price">楽天価格 {b["price"]:,}円〜</span>' if b.get("price") else ""
    author = f'<p class="book-author">{esc(b["author_disp"])}</p>' if b.get("author_disp") else ""
    return f"""
      <article class="{rank_cls}">
        {rank_badge}
        <div class="book-coverwrap"><a href="/books/{b['slug']}/">{cover_html(b)}</a></div>
        <div class="book-body">
          <div class="book-tags">{tags}</div>
          <h3 class="book-title"><a href="/books/{b['slug']}/">{esc(b['title'])}</a></h3>
          {author}
          <p class="book-desc">{esc(b['desc'])}</p>
          <ul class="book-points">{points}</ul>
          {price}
          {cta(b, "ranking_card")}
          <p class="book-more"><a href="/books/{b['slug']}/">▶ この本のレビューを読む</a></p>
        </div>
      </article>"""


def book_grid_card(b):
    """flier風のカバー中心グリッドカード（クリックで個別ページへ）"""
    tag = f'<span class="grid-tag">{esc(b["tags"][0])}</span>' if b.get("tags") else ""
    author = f'<span class="grid-author">{esc(b["author_disp"])}</span>' if b.get("author_disp") else ""
    price = f'<span class="grid-price">楽天 {b["price"]:,}円〜</span>' if b.get("price") else ""
    return f"""<a class="grid-card" href="/books/{b['slug']}/">
        <span class="grid-cover-wrap">{cover_html(b, 'grid-cover')}</span>
        {tag}
        <span class="grid-title">{esc(b['title'])}</span>
        {author}
        {price}
      </a>"""


def hero_cover_stack(books):
    items = []
    for i, b in enumerate(sorted(books, key=lambda x: x["rank"])[:5], 1):
        if b.get("cover"):
            media = f'<img src="{esc(b["cover"])}" alt="{esc(b["title"])}の表紙" loading="eager">'
        else:
            media = f'<span>{esc(b["title"])}</span>'
        items.append(
            f'<a class="hero-book hero-book-{i}" href="/books/{b["slug"]}/" aria-label="{esc(b["title"])}のレビューを読む">{media}</a>'
        )
    return "".join(items)


def section_title(text, sub=""):
    s = f' <span class="section-sub">{esc(sub)}</span>' if sub else ""
    return f'<h2 class="section-title">{esc(text)}{s}</h2>'


# ───────── ページ生成 ─────────
def page_home(books):
    top = [b for b in books if b["rank"] <= 8]
    cards = "".join(book_card(b) for b in sorted(top, key=lambda x: x["rank"]))
    hero_books = hero_cover_stack(books)
    cat_cards = "".join(
        f'<a class="cat-card" href="/{t["slug"]}/"><span class="cat-card-name">{esc(t["name"])}</span>'
        f'<span class="cat-card-lead">{esc(t["lead"])}</span><span class="cat-card-go">この本を見る ›</span></a>'
        for t in THEMES)
    toc = "".join(f'<li><a href="/books/{b["slug"]}/"><span class="num">{b["rank"]}.</span>{esc(b["title"])}</a></li>' for b in sorted(top, key=lambda x: x["rank"]))
    related = """<div class="related-grid">
      <a class="related-card" href="https://dashboard.stock-overflow24.com/"><span class="related-body"><span class="related-name">投資の砦</span><span class="related-desc">日本株・米国株の急騰銘柄や決算速報がひと目で分かるダッシュボード。本で学んだら相場をのぞこう。</span><span class="related-go">ダッシュボードを見る ›</span></span></a>
      <a class="related-card" href="https://yougo.stock-overflow24.com/"><span class="related-body"><span class="related-name">やさしい投資用語辞典</span><span class="related-desc">PER・PBR・ROEって何？ 投資の専門用語をやさしく解説。分からない言葉が出たらここで。</span><span class="related-go">用語を調べる ›</span></span></a>
    </div>"""
    comparisons = "".join(
        f'<a class="compare-link-card" href="/compare/{p["slug"]}/">'
        f'<span>選び方・比較</span><strong>{esc(p["short"])}</strong>'
        f'<small>{esc(p["lead"])}</small><b>比較を見る ›</b></a>'
        for p in COMPARISON_PAGES)
    body = f"""
<section class="hero">
  <div class="hero-inner">
    <div class="hero-copy">
      <p class="hero-kicker">INVESTMENT BOOK GUIDE</p>
      <h1 class="hero-title">投資初心者が最初に読むべき<br><em>投資の名著</em></h1>
      <p class="hero-lead">「何から学べばいいのかわからない」迷いを、長く読み継がれてきた本でほどく。目的別に、最初の一冊と次の一冊を選べる編集ノートです。</p>
      <div class="hero-actions"><a class="hero-primary" href="#ranking">ランキングを見る</a><a class="hero-secondary" href="/guide/">読む順ガイド</a></div>
      <p class="hero-meta">UPDATED {UPDATED} / EDITED BY {SITE_NAME}</p>
    </div>
    <div class="hero-visual" aria-label="紹介している投資本の書影">
      <div class="hero-orbit">READ<br>BEFORE<br>INVEST</div>
      <div class="hero-shelf">{hero_books}</div>
    </div>
  </div>
</section>
<main class="container">
  {breadcrumb([("TOP", None)])}
  <section id="categories">
    {section_title("目的から探す", "あなたに合うテーマで")}
    <div class="cat-grid">{cat_cards}</div>
  </section>
  <nav class="toc" aria-label="目次">
    <p class="toc-title">総合ランキング（まず読むべき8冊）</p>
    <ul class="toc-list">{toc}</ul>
  </nav>
  <section id="ranking" class="ranking">
    {section_title("まず読むべき投資の名著", "総合ランキング8選")}
    {cards}
  </section>
  <section class="compare-home">
    {section_title("迷った2冊を比較する", "目的と読む順で選ぶ")}
    <div class="compare-link-grid">{comparisons}</div>
  </section>
  <section class="about-box">
    {section_title("このサイトについて")}
    <p>「{SITE_NAME}」は、投資を学びたい人が“最初の一冊”で迷わないように、長く読み継がれてきた定番の本を、目的別に厳選して紹介するサイトです。まずは気になった1冊から、あなたの投資の土台を作っていきましょう。</p>
  </section>
  <section>
    {section_title("投資をもっと深める", "姉妹サイト")}
    {related}
  </section>
</main>"""
    return head("投資初心者が最初に読むべき『投資の名著』8選", "投資を始めたい初心者がまず読むべき定番の名著を、初心者向け・NISA・インデックス・バフェット流・FIRE・不動産・米国株など目的別に厳選。選ぶ理由つきで紹介します。", "/") + header() + body + footer()


def page_theme(t, books):
    items = sorted([b for b in books if t["slug"] in b["themes"]], key=lambda x: x["rank"])
    cards = "".join(book_grid_card(b) for b in items)
    other = "".join(f'<a class="chip" href="/{o["slug"]}/">{esc(o["name"])}</a>' for o in THEMES if o["slug"] != t["slug"])
    guide = THEME_GUIDES[t["slug"]]
    guide_points = "".join(f"<li>{esc(p)}</li>" for p in guide["points"])
    body = f"""
<main class="container container--narrowtop">
  {breadcrumb([("TOP", "/"), (t["name"], None)])}
  <header class="page-head">
    <p class="hero-eyebrow">目的別おすすめ</p>
    <h1 class="page-title">{esc(t["name"])}の<br><em>おすすめ投資本</em></h1>
    <p class="page-lead">{esc(t["lead"])}</p>
    <p class="page-count">{len(items)}冊を厳選</p>
  </header>
  <section class="theme-guide" aria-labelledby="theme-guide-title">
    <div>
      <p class="theme-guide-label">このテーマの選び方</p>
      <h2 id="theme-guide-title">{esc(t["name"])}の本で確認したい3点</h2>
      <ul>{guide_points}</ul>
    </div>
    <aside>
      <strong>読む前の注意</strong>
      <p>{esc(guide["caution"])}</p>
      <a href="/guide/">投資本の読む順ガイドを見る ›</a>
    </aside>
  </section>
  <section class="book-grid">
    {cards if items else '<p>準備中です。</p>'}
  </section>
  <section class="about-box">
    {section_title("ほかのテーマも見る")}
    <div class="chip-row">{other}</div>
  </section>
</main>"""
    return head(f"{t['name']}のおすすめ投資本", f"{t['name']}の投資初心者・実践者に向けて、定番のおすすめ本を厳選。{t['lead']}", f"/{t['slug']}/") + header() + body + footer()


def comparison_details(slug):
    """各ページ固有の結論。ランキングの使い回しではなく、検索意図ごとに判断軸を変える。"""
    if slug == "first-investment-books":
        return dict(
            answer="迷ったら、家計やお金全体が不安なら『お金の大学』、短時間で投資の基本を知るなら『敗者のゲーム』、データまで含めて深く納得したいなら『ウォール街のランダム・ウォーカー』です。",
            axes=[("お金の大学", "家計・固定費から整える", "やさしい", "投資前の土台づくり"),
                  ("敗者のゲーム", "市場平均を選ぶ理由を知る", "標準", "短時間で投資の軸を作る"),
                  ("ウォール街のランダム・ウォーカー", "歴史とデータで深く学ぶ", "やや骨太", "長く使える理論を得る")],
            steps=["投資に回せる余裕資金を確認する", "長期・分散・低コストの意味を理解する", "制度や商品は公式の最新情報で確認して少額から始める"],
            caution="最初から3冊すべてを買う必要はありません。今の悩みに合う1冊を読み、次の疑問が出た時点で2冊目へ進む方が無駄がありません。",
        )
    if slug == "random-walker-vs-losers-game":
        return dict(
            answer="最初に結論だけつかみたい人は『敗者のゲーム』、結論の根拠を歴史・データまで深く理解したい人は『ウォール街のランダム・ウォーカー』が向いています。初心者が2冊読むなら、この順番が軽やかです。",
            axes=[("敗者のゲーム", "短く要点をつかむ", "標準", "市場に勝とうとしない考え方"),
                  ("ウォール街のランダム・ウォーカー", "根拠まで深く理解する", "やや骨太", "市場の歴史・理論・運用方法")],
            steps=["『敗者のゲーム』で市場平均を選ぶ理由をつかむ", "自分に合う考えだと感じたら『ランダム・ウォーカー』で根拠を補強する", "最後に日本の制度と低コスト商品の最新情報を確認する"],
            caution="両書とも、将来の利益や元本を保証する本ではありません。結論だけを銘柄推奨として受け取らず、値動きに耐えられる資産配分を別途考える必要があります。",
        )
    if slug == "nisa-books":
        return dict(
            answer="まったくの初心者は『お金の大学』で家計を整え、次に『ほったらかし投資術』で実践像をつかむ順番がおすすめです。すでに積立中なら『お金は寝かせて増やしなさい』で続け方を補強します。",
            axes=[("お金の大学", "家計と余裕資金", "やさしい", "投資前の準備"),
                  ("ほったらかし投資術", "商品選びと実践", "やさしい", "最初の運用方針"),
                  ("お金は寝かせて増やしなさい", "暴落時も続ける方法", "標準", "継続の仕組み"),
                  ("敗者のゲーム", "インデックスの理論", "標準", "運用方針への納得"),
                  ("新NISA関連の実践書", "制度と手続き", "やさしい", "最新制度の確認")],
            steps=["生活防衛資金と毎月の余裕額を決める", "長期・積立・分散とコストの意味を学ぶ", "金融庁・金融機関の公式情報で制度と対象商品を確認する"],
            caution="NISAは利益を保証する制度ではなく、投資元本を下回る可能性があります。制度・対象商品は書籍の発行後に変わるため、必ず金融庁の最新情報も併用してください。",
        )
    if slug == "index-reading-order":
        return dict(
            answer="挫折しにくい順番は、①家計の全体像、②短い理論書、③詳しい理論書、④コストの原点、⑤続け方です。全部読む必要はなく、理解できた段階で実践書へ移って構いません。",
            axes=[("お金の大学", "準備", "やさしい", "家計と余裕資金"),
                  ("敗者のゲーム", "入門理論", "標準", "市場平均を選ぶ理由"),
                  ("ウォール街のランダム・ウォーカー", "理論", "やや骨太", "歴史とデータ"),
                  ("インデックス投資は勝者のゲーム", "原点", "やや骨太", "低コストの重要性"),
                  ("お金は寝かせて増やしなさい", "実践", "標準", "積立を続ける方法")],
            steps=["入門書で投資に回せる金額を決める", "理論書を1冊読み、なぜ指数を選ぶのかを説明できるようにする", "実践書で暴落時にも続けるルールを決める"],
            caution="知識を増やし続けても、損失への耐性は自動では高まりません。読書と同時に、生活に影響しない少額で値動きを経験する方法も検討してください。",
        )
    return dict(
        answer="配当再投資の根拠を学ぶなら『株式投資の未来』、米国配当株の選び方なら『米国株で始める100万円からのセミリタイア投資術』、仕組み化を重視するなら『オートモードで月に18.5万円が入ってくる高配当株投資』が候補です。",
        axes=[("株式投資の未来", "長期データと理論", "やや骨太", "配当再投資の意味"),
              ("米国株で始める100万円からのセミリタイア投資術", "米国配当株の実践", "標準", "銘柄を見る視点"),
              ("オートモードで月に18.5万円が入ってくる高配当株投資", "運用の仕組み化", "やさしい", "ルールを作って続ける"),
              ("たぱぞう式 米国株投資", "米国株の全体像", "やさしい", "指数と個別株の整理")],
        steps=["配当の高さではなく、利益・キャッシュフロー・減配歴を見る", "国・業種・銘柄を分散し、税引後の受取額を確認する", "配当と値上がり益を含む総合的な成果で評価する"],
        caution="高い配当利回りは安全性の証明ではありません。業績悪化による減配や株価下落、米国株では為替と税金の影響もあります。",
    )


def page_comparison(p, books):
    by_slug = {b["slug"]: b for b in books}
    selected = [by_slug[s] for s in p["books"] if s in by_slug]
    d = comparison_details(p["slug"])
    rows = []
    for i, (name, purpose, level, role) in enumerate(d["axes"]):
        # axes は selected と同じ順番で定義。楽天側の版表記で書名が変わっても
        # 正しい個別レビューへリンクできるよう、slugで選んだ順序を正とする。
        match = selected[i] if i < len(selected) else None
        label = f'<a href="/books/{match["slug"]}/">{esc(name)}</a>' if match else esc(name)
        rows.append(f"<tr><th>{label}</th><td>{esc(purpose)}</td><td>{esc(level)}</td><td>{esc(role)}</td></tr>")
    step_items = "".join(f"<li><span>{i}</span><p>{esc(x)}</p></li>" for i, x in enumerate(d["steps"], 1))
    cards = "".join(book_grid_card(b) for b in selected)
    other = "".join(
        f'<a class="compare-link-card" href="/compare/{o["slug"]}/"><span>関連比較</span>'
        f'<strong>{esc(o["short"])}</strong><b>読む ›</b></a>'
        for o in COMPARISON_PAGES if o["slug"] != p["slug"])
    official = ""
    if p["slug"] == "nisa-books":
        official = """<aside class="official-note"><strong>制度は公式情報も確認</strong>
        <p>金融庁はNISAを長期・積立・分散投資による安定的な資産形成のための制度として案内しています。2024年からの新制度は恒久化され、非課税保有期間は無期限ですが、投資には元本割れの可能性があります。</p>
        <a href="https://www.fsa.go.jp/policy/nisa2/know/" target="_blank" rel="noopener">金融庁「NISAを知る」›</a>
        <a href="https://www.fsa.go.jp/policy/nisa2/invest/" target="_blank" rel="noopener">金融庁「資産形成の基本」›</a></aside>"""
    path = f"/compare/{p['slug']}/"
    body = f"""
<main class="container container--narrowtop">
  {breadcrumb([("TOP", "/"), ("投資本の選び方", "/guide/"), (p["title"], None)])}
  <article class="comparison">
    <header class="page-head comparison-head">
      <p class="hero-eyebrow">目的別・投資本比較</p>
      <h1 class="page-title">{esc(p["title"])}</h1>
      <p class="page-lead">{esc(p["lead"])}</p>
      <p class="hero-meta">UPDATED {UPDATED} / EDITED BY {SITE_NAME}</p>
    </header>
    <section class="comparison-answer">
      <span>先に結論</span>
      <p>{esc(d["answer"])}</p>
    </section>
    {section_title("違いを比較", "目的・難易度・役割")}
    <div class="compare-table-wrap"><table class="compare-table">
      <thead><tr><th>本</th><th>向いている目的</th><th>読みやすさ</th><th>この本の役割</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>
    {section_title("失敗しにくい選び方・読む順番")}
    <ol class="compare-steps">{step_items}</ol>
    <div class="review-caution"><strong>選ぶ前の注意</strong><p>{esc(d["caution"])}</p></div>
    {official}
    {section_title("今回比較した本", f"{len(selected)}冊")}
    <div class="book-grid compare-books">{cards}</div>
    <p class="comparison-disclosure">{esc(affiliate_disclosure())}</p>
    {section_title("ほかの比較も見る")}
    <div class="compare-link-grid">{other}</div>
  </article>
</main>"""
    return head(p["title"], p["lead"] + " 向いている人・読みやすさ・読む順番を編集部が比較します。", path) + header() + body + footer()


def book_detail_sections(b, rel):
    primary = THEME_NAME.get(b["themes"][0], "投資")
    theme_names = "・".join(THEME_NAME.get(th, th) for th in b["themes"])
    main_point = b["points"][0] if b.get("points") else b["desc"]
    second_point = b["points"][1] if len(b.get("points") or []) > 1 else b["who"]
    if rel:
        cmp = rel[0]
        compare = (f"同じ{primary}テーマで迷うなら、まず本書で軸を作り、次に"
                   f"『{cmp['title']}』を読むと理解がつながりやすくなります。")
    else:
        compare = f"{primary}の考え方を、短期の相場材料ではなく長く使える基礎として整理できる点が強みです。"
    if b["rank"] <= 5:
        order = "投資をこれから始める人が最初の数冊として読むのに向いています。細かい手法に進む前の土台づくりに使ってください。"
    elif "buffett" in b["themes"]:
        order = "インデックス投資や家計管理の入門書を読んだあと、個別株や企業分析に興味が出てきた段階で読むと吸収しやすいです。"
    elif "fire" in b["themes"]:
        order = "投資商品の選び方だけでなく、支出・働き方・人生設計まで考えたい段階で読むと効果的です。"
    else:
        order = "入門書を1冊読んだあと、自分が深掘りしたいテーマを決めるための2冊目以降に向いています。"
    caution = THEME_GUIDES[b["themes"][0]]["caution"]
    return f"""<h3 class="bd-subh" id="learn">この本で学べること</h3>
      <p>{esc(b["desc"])} 特に「{esc(main_point)}」「{esc(second_point)}」を押さえることで、{esc(primary)}の判断軸を作りやすくなります。</p>
      <h3 class="bd-subh" id="fit">向いている人・注意したい人</h3>
      <p>{esc(b["who"])}に向いています。一方で、すぐに儲かる銘柄名や短期売買のシグナルだけを探している人には物足りない可能性があります。</p>
      <h3 class="bd-subh" id="compare">他の投資本との違い</h3>
      <p>{esc(compare)} テーマとしては{esc(theme_names)}に近く、流行の投資ノウハウよりも長く使える考え方を得たい人に合います。</p>
      <h3 class="bd-subh" id="order">読む順番の目安</h3>
      <p>{esc(order)}</p>
      <div class="review-caution">
        <strong>このテーマを読むときの注意</strong>
        <p>{esc(caution)}</p>
      </div>"""


def review_meta(b):
    """レビューの責任主体・更新日・評価方法を本文上で見えるようにする。"""
    return f"""<aside class="review-meta" aria-label="レビュー情報">
      <div><span>編集・評価</span><strong>STOCK OVERFLOW 編集部</strong></div>
      <div><span>最終更新</span><strong>{esc(UPDATED)}</strong></div>
      <div><span>評価の考え方</span><strong>初心者への分かりやすさ・普遍性・実用性・注意点</strong></div>
      <p>★評価は販売サイトの口コミ平均ではなく、当サイト独自の推薦度です。評価方法は<a href="/about/#review-policy">運営・編集方針</a>で公開しています。</p>
    </aside>"""


def decision_panel(b, rel):
    primary = THEME_NAME.get(b["themes"][0], "投資")
    next_book = rel[0]["title"] if rel else "次の定番本"
    point_items = "".join(f"<li>{esc(p)}</li>" for p in b["points"][:2])
    if b["rank"] <= 3:
        lead = "最初の一冊で遠回りしたくない人は、この本からで問題ありません。"
    elif "nisa" in b["themes"]:
        lead = "新NISAや積立を始める前に、実際にどう続けるかまで確認したい人向けです。"
    elif "buffett" in b["themes"]:
        lead = "企業分析や個別株に進む前に、価格と価値を分けて考える軸を作りたい人向けです。"
    elif "fire" in b["themes"]:
        lead = "投資だけでなく、支出・働き方・人生設計まで一度に見直したい人向けです。"
    else:
        lead = f"{primary}をもう一段深く理解したい人に向いています。"
    return f"""<section class="decision-panel">
      <div class="decision-main">
        <span class="decision-label">迷ったらこの判断</span>
        <h2>{esc(b["title"])}を選ぶ理由</h2>
        <p>{esc(lead)} まず本書で軸を作り、必要なら『{esc(next_book)}』へ進むと理解がつながります。</p>
      </div>
      <ul class="decision-list">{point_items}</ul>
    </section>"""


def purchase_box(b):
    return f"""<section class="purchase-box" id="purchase">
      <div class="purchase-copy">
        <span class="purchase-label">読むならここから</span>
        <h2>{esc(b["title"])}を購入する</h2>
        <p>レビューを読んで「今の自分に合う」と感じたら、在庫と価格を確認してください。迷う時間を長くするより、1冊読んで投資判断の軸を作るほうが早いです。</p>
      </div>
      {cta(b, "review_end")}
    </section>"""


def page_book(b, books):
    # related: same-theme books (excluding self), up to 4
    rel = []
    for o in books:
        if o["slug"] == b["slug"]:
            continue
        if set(o["themes"]) & set(b["themes"]):
            rel.append(o)
    rel = sorted(rel, key=lambda x: x["rank"])[:4]
    rel_cards = "".join(
        f'<a class="mini-card" href="/books/{o["slug"]}/">{cover_html(o, "mini-cover")}<span class="mini-title">{esc(o["title"])}</span></a>'
        for o in rel)
    theme_links = " ".join(f'<a class="chip" href="/{th}/">{esc(THEME_NAME.get(th, th))}</a>' for th in b["themes"])
    tags = "".join(f'<span class="tag{" tag-gold" if i==0 else ""}">{esc(t)}</span>' for i, t in enumerate(b["tags"]))
    points = "".join(f"<li>{esc(p)}</li>" for p in b["points"])
    price = f'<span class="book-price">楽天価格 {b["price"]:,}円〜</span>' if b.get("price") else ""
    author = f'<p class="bd-author">{esc(b["author_disp"])}</p>' if b.get("author_disp") else ""
    primary_theme = b["themes"][0]
    body = f"""
<main class="container container--narrowtop">
  {breadcrumb([("TOP", "/"), (THEME_NAME.get(primary_theme, "投資本"), f"/{primary_theme}/"), (b["title"], None)])}
  <article class="book-detail">
    <div class="bd-head">
      <div class="bd-coverwrap">{cover_html(b, "bd-cover")}</div>
      <div class="bd-meta">
        <div class="book-tags">{tags}</div>
        <h1 class="bd-title">{esc(b["title"])}</h1>
        {author}
        {stars_html(b["rating"])}
        {price}
        <p class="bd-who"><span>こんな人におすすめ</span>{esc(b["who"])}</p>
        {cta(b, "book_hero")}
      </div>
    </div>
    {decision_panel(b, rel)}
    <nav class="article-toc" aria-label="この記事の目次">
      <strong>このページで分かること</strong>
      <a href="#review">編集部レビュー</a>
      <a href="#learn">学べること</a>
      <a href="#fit">向いている人・注意点</a>
      <a href="#compare">類書との違い</a>
      <a href="#purchase">購入先</a>
    </nav>
    {review_meta(b)}
    <section class="bd-review">
      <h2 class="section-title" id="review">どんな本？ <span class="section-sub">編集部レビュー</span></h2>
      <p>{esc(b["review"])}</p>
      <h3 class="bd-subh">要点を先に確認</h3>
      <ul class="book-points bd-points">{points}</ul>
      {book_detail_sections(b, rel)}
      <div class="bd-theme-links">関連テーマ：{theme_links}</div>
    </section>
    {purchase_box(b)}
  </article>
  <section class="about-box">
    {section_title("あわせて読みたい")}
    <div class="mini-grid">{rel_cards}</div>
  </section>
</main>"""
    path = f"/books/{b['slug']}/"
    return head(f"{b['title']}｜要点と感想・どんな人におすすめ？", f"{b['title']}（{b['author_disp']}）のレビュー。{b['desc']} {b['who']}に。", path, extra_head=book_jsonld(b, path)) + header() + body + footer()


def page_guide(books):
    # original guidance content
    beginner_books = sorted([b for b in books if "beginner" in b["themes"]], key=lambda x: x["rank"])[:3]
    blist = "".join(f'<li><a href="/books/{b["slug"]}/">{esc(b["title"])}</a> — {esc(b["who"])}</li>' for b in beginner_books)
    stores = "Amazon／楽天ブックス／Yahoo!ショッピング" if has_amazon_affiliate() else "楽天ブックス／Yahoo!ショッピング"
    comparison_links = "".join(
        f'<li><a href="/compare/{p["slug"]}/">{esc(p["title"])}</a> — {esc(p["lead"])}</li>'
        for p in COMPARISON_PAGES)
    body = f"""
<main class="container container--narrowtop">
  {breadcrumb([("TOP", "/"), ("投資本の選び方・読む順ガイド", None)])}
  <header class="page-head">
    <p class="hero-eyebrow">はじめての人へ</p>
    <h1 class="page-title">投資本の<br><em>選び方・読む順ガイド</em></h1>
    <p class="page-lead">「どれから読めばいい？」に編集部が答えます。レベル別の読む順と、本を選ぶときの注意点をまとめました。</p>
  </header>
  <article class="guide">
    {section_title("読む順番の目安", "初心者→実践")}
    <ol class="guide-steps">
      <li><strong>STEP1 マインドと全体像</strong>：まずお金との向き合い方と全体像を。「お金の大学」「金持ち父さん貧乏父さん」など。</li>
      <li><strong>STEP2 なぜインデックスか</strong>：「敗者のゲーム」「ウォール街のランダム・ウォーカー」で“市場全体を買う”理由を理解。</li>
      <li><strong>STEP3 手を動かす</strong>：「ほったらかし投資術」「お金は寝かせて増やしなさい」で口座・銘柄・続け方を実践。</li>
      <li><strong>STEP4 深める</strong>：興味の出た方向（米国株／バフェット流／不動産／FIRE）の専門書へ。</li>
    </ol>
    {section_title("本を選ぶときの3つの注意点")}
    <ul class="guide-notes">
      <li><strong>原理原則の本を優先する</strong>：具体的すぎる手法本は情報が古くなりがち。長く使える考え方の本から。</li>
      <li><strong>煽りに注意</strong>：「絶対儲かる」系より、リスクも正直に書いている本を選ぶ。</li>
      <li><strong>レベルに合わせる</strong>：いきなり古典（賢明なる投資家など）に挑むより、入門→実践→古典の順が挫折しにくい。</li>
    </ul>
    {section_title("まず最初の1冊なら")}
    <ul class="guide-first">{blist}</ul>
    {section_title("目的別に本を比較する")}
    <ul class="guide-first comparison-guide-links">{comparison_links}</ul>
    {section_title("よくある疑問")}
    <dl class="guide-faq">
      <div><dt>最初から何冊も買う必要はありますか？</dt><dd>必要ありません。全体像をつかむ本を1冊読み、次に知りたいテーマが見えてから2冊目を選ぶ方が無駄がありません。</dd></div>
      <div><dt>古い名著でも読む価値はありますか？</dt><dd>長期・分散・コスト・企業価値などの原則は今も役立ちます。一方、NISA・税制・商品名などは変わるため、公式の最新情報と併用してください。</dd></div>
      <div><dt>ランキング1位が全員に最適ですか？</dt><dd>いいえ。ランキングは初心者への分かりやすさと普遍性を重視した目安です。目的別カテゴリと「向いている人」も合わせて選んでください。</dd></div>
    </dl>
    <p class="guide-cta-note">気になった本は各ページの「{stores}」からチェックできます。</p>
  </article>
</main>"""
    return head("投資本の選び方・読む順ガイド", "投資の本をどれから読めばいい？ レベル別の読む順番と、本を選ぶときの注意点を初心者向けにやさしく解説します。", "/guide/") + header() + body + footer()


def page_about():
    body = f"""
<main class="container container--narrowtop">
  {breadcrumb([("TOP", "/"), ("運営者情報", None)])}
  <header class="page-head">
    <p class="hero-eyebrow">このサイトについて</p>
    <h1 class="page-title">運営者情報</h1>
    <p class="page-lead">「{esc(SITE_NAME)}」は、投資のはじめの一冊を探す人のために、定番の投資本を編集部の視点でレビュー・ランキングするサイトです。</p>
  </header>
  <article class="guide">
    {section_title("サイトの目的")}
    <p>投資を始めたいけれど「何から読めばいいか分からない」という人に向けて、世代を超えて読み継がれてきた投資の名著を、目的別（初心者／NISA／インデックス／バリュー投資／FIRE／不動産／米国株／高配当）に整理して紹介しています。各書籍のレビュー・要点・ランキング・★評価は、出版社の紹介文を転載せず、編集部が実際に内容を踏まえて作成したオリジナルです。</p>
    {section_title("運営者")}
    <ul class="guide-notes">
      <li><strong>サイト名</strong>：{esc(SITE_NAME)}（stock-overflow24.com）</li>
      <li><strong>運営</strong>：STOCK OVERFLOW 編集部</li>
      <li><strong>運営開始</strong>：2026年</li>
      <li><strong>連絡先</strong>：<a href="mailto:{esc(CONTACT_EMAIL)}">{esc(CONTACT_EMAIL)}</a>（詳しくは<a href="/contact/">お問い合わせ</a>ページ）</li>
    </ul>
    <section id="review-policy">
    {section_title("編集・評価方針", "信頼できる情報のために")}
    <ul class="guide-notes">
      <li><strong>オリジナルの内容</strong>：レビュー・要点・おすすめ理由はすべて編集部が独自に執筆しています。</li>
      <li><strong>中立性</strong>：報酬の有無で評価をゆがめず、メリットだけでなく注意点も正直に記載します。</li>
      <li><strong>4つの評価軸</strong>：初心者への分かりやすさ、長く使える普遍性、行動につなげやすい実用性、リスクや限界の説明を確認します。</li>
      <li><strong>★評価の意味</strong>：販売サイトの口コミ平均ではなく、上記4軸に基づく当サイト独自の推薦度です。</li>
      <li><strong>更新</strong>：書籍情報、制度、価格、リンクを定期的に見直し、各レビューに最終更新日を表示します。</li>
      <li><strong>訂正</strong>：誤りや古い情報が見つかった場合は修正します。ご指摘は<a href="/contact/">お問い合わせ</a>から受け付けています。</li>
    </ul>
    </section>
    {section_title("姉妹サイト")}
    <ul class="guide-first">
      <li><a href="https://dashboard.stock-overflow24.com/">投資の砦</a> — 日本株・米国株の急騰銘柄や決算速報がひと目で分かるダッシュボード。</li>
      <li><a href="https://yougo.stock-overflow24.com/">やさしい投資用語辞典</a> — PER・PBR・ROEなど、投資の専門用語をやさしく解説。</li>
    </ul>
    <p class="guide-cta-note">広告掲載・アフィリエイトの方針については<a href="/privacy/">プライバシーポリシー</a>をご覧ください。</p>
  </article>
</main>"""
    return head("運営者情報", f"{SITE_NAME}（stock-overflow24.com）の運営者情報・編集方針について。投資の名著を編集部の視点でレビュー・ランキングしています。", "/about/") + header() + body + footer()


def page_contact():
    body = f"""
<main class="container container--narrowtop">
  {breadcrumb([("TOP", "/"), ("お問い合わせ", None)])}
  <header class="page-head">
    <p class="hero-eyebrow">ご連絡はこちら</p>
    <h1 class="page-title">お問い合わせ</h1>
    <p class="page-lead">サイトの内容に関するご指摘、掲載・取材・広告のご相談などは、下記メールアドレスまでお気軽にご連絡ください。</p>
  </header>
  <article class="guide">
    {section_title("連絡先")}
    <p class="contact-mail"><a href="mailto:{esc(CONTACT_EMAIL)}">{esc(CONTACT_EMAIL)}</a></p>
    {section_title("お問い合わせ前のお願い")}
    <ul class="guide-notes">
      <li><strong>返信について</strong>：内容を確認のうえ、通常2〜3営業日以内にご返信します。お急ぎの場合もメールにてお願いいたします。</li>
      <li><strong>個別の投資助言はできません</strong>：当サイトは書籍の紹介を行うものであり、特定の銘柄・商品の売買を推奨するものではありません。投資判断はご自身の責任でお願いします。</li>
      <li><strong>お預かりした情報</strong>：いただいたメールアドレス・お名前は返信の目的にのみ使用します。詳しくは<a href="/privacy/">プライバシーポリシー</a>をご覧ください。</li>
    </ul>
    <p class="guide-cta-note">運営者・サイトの方針については<a href="/about/">運営者情報</a>をご覧ください。</p>
  </article>
</main>"""
    return head("お問い合わせ", f"{SITE_NAME}へのお問い合わせはこちら。サイト内容のご指摘・掲載や広告のご相談はメールでお受けしています。", "/contact/") + header() + body + footer()


def page_privacy():
    amazon_li = amazon_privacy_item()
    body = f"""
<main class="container container--narrowtop">
  {breadcrumb([("TOP", "/"), ("プライバシーポリシー", None)])}
  <header class="page-head">
    <p class="hero-eyebrow">個人情報の取り扱い</p>
    <h1 class="page-title">プライバシーポリシー</h1>
    <p class="page-lead">{esc(SITE_NAME)}（以下「当サイト」）における、個人情報の取り扱い・広告・免責事項について定めます。</p>
  </header>
  <article class="guide">
    {section_title("個人情報の利用目的")}
    <p>当サイトでは、お問い合わせの際にお名前・メールアドレス等の個人情報をご登録いただく場合があります。これらの情報は、ご質問への回答や必要な情報をご連絡する目的でのみ利用し、ご本人の同意なく第三者に開示・提供することはありません（法令に基づく場合を除く）。</p>
    {section_title("アクセス解析ツールについて")}
    <p>当サイトでは、サイトの利用状況を把握するためにGoogleが提供する「Googleアナリティクス（GA4）」を利用しています。このツールはCookieを使用してトラフィックデータを収集しますが、個人を特定する情報は含まれません。Cookieはブラウザの設定で無効にできます。データ収集の仕組みについては<a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener nofollow">Googleのポリシーと規約</a>をご確認ください。</p>
    {section_title("アフィリエイトプログラムについて")}
    <ul class="guide-notes">
{amazon_li}
      <li>当サイトは、楽天アフィリエイトをはじめとする各種アフィリエイトプログラム（ASP：もしもアフィリエイト等）にも参加しており、リンク経由でのご購入・お申し込みにより運営者に紹介料が支払われる場合があります。</li>
      <li>第三者配信の広告サービスを利用する場合、広告事業者がCookie等を用いて利用者の興味に応じた広告を表示することがあります。</li>
    </ul>
    {section_title("免責事項")}
    <ul class="guide-notes">
      <li>当サイトの掲載内容は書籍の紹介・情報提供を目的としたものであり、特定の投資・銘柄・金融商品の売買を推奨・勧誘するものではありません。投資はご自身の判断と責任において行ってください。</li>
      <li>掲載情報（価格・在庫・書籍情報等）の正確性には努めていますが、その完全性・最新性を保証するものではありません。リンク先の外部サイトで提供される情報・サービスについては、当サイトは責任を負いかねます。</li>
    </ul>
    {section_title("著作権について")}
    <p>当サイトに掲載されている文章・レビュー等のコンテンツの著作権は、当サイトまたは正当な権利者に帰属します。無断での転載・複製はご遠慮ください。書影・書籍情報は各出版社・提供元に帰属します。</p>
    {section_title("プライバシーポリシーの変更")}
    <p>当サイトは、法令の変更や運営方針の見直しに応じて、本ポリシーの内容を予告なく変更することがあります。変更後の内容は、当ページに掲載した時点で効力を生じるものとします。</p>
    {section_title("お問い合わせ")}
    <p>本ポリシーに関するお問い合わせは、<a href="mailto:{esc(CONTACT_EMAIL)}">{esc(CONTACT_EMAIL)}</a>（<a href="/contact/">お問い合わせ</a>ページ）までご連絡ください。</p>
    <p class="guide-cta-note">制定日：2026年6月5日</p>
  </article>
</main>"""
    return head("プライバシーポリシー", f"{SITE_NAME}のプライバシーポリシー。個人情報の取り扱い、Googleアナリティクス、Amazonアソシエイト・楽天等のアフィリエイト、免責事項について。", "/privacy/") + header() + body + footer()


# ───────── 出力 ─────────
def write(path, html_str):
    full = os.path.join(HERE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(html_str)


HERE = os.path.dirname(__file__)


def main():
    global CSS_VER
    import hashlib
    try:
        CSS_VER = hashlib.md5(open(os.path.join(HERE, "style.css"), "rb").read()).hexdigest()[:8]
    except Exception:
        CSS_VER = UPDATED.replace(".", "")
    books = build_books()
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "books.json"), "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)

    write("index.html", page_home(books))
    write("guide/index.html", page_guide(books))
    write("about/index.html", page_about())
    write("contact/index.html", page_contact())
    write("privacy/index.html", page_privacy())
    for t in THEMES:
        write(f"{t['slug']}/index.html", page_theme(t, books))
    for b in books:
        write(f"books/{b['slug']}/index.html", page_book(b, books))
    for p in COMPARISON_PAGES:
        write(f"compare/{p['slug']}/index.html", page_comparison(p, books))

    # sitemap.xml（全ページ）
    urls = ([ "/", "/guide/", "/about/", "/contact/", "/privacy/" ]
            + [f"/{t['slug']}/" for t in THEMES]
            + [f"/books/{b['slug']}/" for b in books]
            + [f"/compare/{p['slug']}/" for p in COMPARISON_PAGES])
    lastmod = SITEMAP_LASTMOD
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        pr = "1.0" if u == "/" else ("0.8" if u.count("/") == 2 else "0.6")
        sm.append(f"  <url><loc>{SITE}{u}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>{pr}</priority></url>")
    sm.append("</urlset>\n")
    write("sitemap.xml", "\n".join(sm))

    n_pages = 5 + len(THEMES) + len(books) + len(COMPARISON_PAGES)
    print(f"[build] {len(books)}冊 / {n_pages}ページ生成（トップ・ガイド・運営者・問合せ・規約・カテゴリ{len(THEMES)}・個別{len(books)}・比較{len(COMPARISON_PAGES)}）", file=sys.stderr)


if __name__ == "__main__":
    main()

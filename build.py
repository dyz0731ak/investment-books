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
import os, sys, json, html, re, time, shutil
import requests

API = "https://openapi.rakuten.co.jp/services/api/BooksBook/Search/20170404"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://stock-overflow24.com/", "Origin": "https://stock-overflow24.com"}
SITE = "https://stock-overflow24.com"
SITE_NAME = "迷える子羊たちの株ノート"
SITE_TAGLINE = "迷える子羊たちへ。投資の“はじめの一冊”を。"
UPDATED = "2026.06.01"
CSS_VER = "1"  # style.css のキャッシュバスター（main内でハッシュに更新）
GA_ID = os.environ.get("GA4_ID", "")  # GA4測定ID（環境変数。未設定なら計測タグは出力されない）


def ga_head():
    if not GA_ID:
        return ""
    return f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>"""


def ga_click_script():
    # アフィリンク(楽天/Amazon)のクリックをGA4イベントとして計測（gtag未読込なら何もしない）
    return """<script>
document.addEventListener('click',function(e){var a=e.target.closest?e.target.closest('a.btn-amazon,a.btn-rakuten'):null;
if(a&&typeof gtag==='function'){gtag('event','affiliate_click',{store:a.classList.contains('btn-amazon')?'amazon':'rakuten',link_url:a.href,page:location.pathname});}},true);
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
        out.append(nb)
        print(f"  #{b['rank']:2} {b['slug']:18} cover={'Y' if info['cover'] else '-'} aff={'Y' if info['url'] else '-'}", file=sys.stderr)
        if have: time.sleep(1.0)
    return out


# ───────── HTML部品 ─────────
def esc(s): return html.escape(str(s or ""))
def amazon_search(t): return "https://www.amazon.co.jp/s?k=" + requests.utils.quote(t)
def rakuten_url(b): return b.get("url") or ("https://search.rakuten.co.jp/search/mall/" + requests.utils.quote(b["q"]) + "/")


def head(title, desc, path):
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
<link rel="canonical" href="{canon}">
<link rel="icon" type="image/png" href="/assets/sheep-icon.png">
<link rel="apple-touch-icon" href="/assets/sheep-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css?v={CSS_VER}">
{ga_head()}
</head>
<body>"""


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
    <nav class="gnav"><a href="/">ホーム</a><a href="/guide/">選び方ガイド</a><a href="/#categories">カテゴリ</a></nav>
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


def footer():
    cats = "".join(f'<a href="/{t["slug"]}/">{esc(t["name"])}</a>' for t in THEMES[:5])
    return f"""<footer class="site-footer">
  <div class="footer-inner">
    <p class="footer-brand"><img class="footer-mark" src="/assets/sheep-icon.png" alt="" width="28" height="35">{SITE_NAME}</p>
    <nav class="footer-nav"><a href="/">ホーム</a><a href="/guide/">選び方ガイド</a>{cats}</nav>
    <nav class="footer-nav"><a href="https://dashboard.stock-overflow24.com/">投資の砦</a><a href="https://yougo.stock-overflow24.com/">用語辞典</a><a href="#">お問い合わせ</a><a href="#">プライバシーポリシー</a></nav>
    <p class="footer-note">※当サイトはアフィリエイトプログラム（楽天アフィリエイト・Amazonアソシエイト等）を利用しています。リンク経由のご購入で運営者に紹介料が支払われる場合があります。</p>
    <p class="footer-note">※掲載内容は書籍の紹介であり、特定の投資・銘柄を推奨するものではありません。投資は自己責任で行ってください。</p>
    <p class="footer-copy">© 2026 {SITE_NAME}</p>
  </div>
</footer>
{ga_click_script()}
</body>
</html>"""


def cta(b):
    return f"""<div class="book-cta">
      <a class="btn btn-amazon" href="{esc(amazon_search(b['title']))}" target="_blank" rel="sponsored nofollow noopener">Amazonで見る</a>
      <a class="btn btn-rakuten" href="{esc(rakuten_url(b))}" target="_blank" rel="sponsored nofollow noopener">楽天ブックスで見る</a>
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
          {cta(b)}
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


def section_title(text, sub=""):
    s = f' <span class="section-sub">{esc(sub)}</span>' if sub else ""
    return f'<h2 class="section-title">{esc(text)}{s}</h2>'


# ───────── ページ生成 ─────────
def page_home(books):
    top = [b for b in books if b["rank"] <= 8]
    cards = "".join(book_card(b) for b in sorted(top, key=lambda x: x["rank"]))
    cat_cards = "".join(
        f'<a class="cat-card" href="/{t["slug"]}/"><span class="cat-card-name">{esc(t["name"])}</span>'
        f'<span class="cat-card-lead">{esc(t["lead"])}</span><span class="cat-card-go">この本を見る ›</span></a>'
        for t in THEMES)
    toc = "".join(f'<li><a href="/books/{b["slug"]}/"><span class="num">{b["rank"]}.</span>{esc(b["title"])}</a></li>' for b in sorted(top, key=lambda x: x["rank"]))
    related = """<div class="related-grid">
      <a class="related-card" href="https://dashboard.stock-overflow24.com/"><span class="related-body"><span class="related-name">投資の砦</span><span class="related-desc">日本株・米国株の急騰銘柄や決算速報がひと目で分かるダッシュボード。本で学んだら相場をのぞこう。</span><span class="related-go">ダッシュボードを見る ›</span></span></a>
      <a class="related-card" href="https://yougo.stock-overflow24.com/"><span class="related-body"><span class="related-name">やさしい投資用語辞典</span><span class="related-desc">PER・PBR・ROEって何？ 投資の専門用語をやさしく解説。分からない言葉が出たらここで。</span><span class="related-go">用語を調べる ›</span></span></a>
    </div>"""
    body = f"""
<section class="hero">
  <div class="hero-inner">
    <p class="hero-eyebrow">編集部が選ぶ・投資のバイブル</p>
    <h1 class="hero-title">投資初心者が最初に読むべき<br><em>『投資の名著』8選</em></h1>
    <p class="hero-lead">「投資を始めたいけれど、何から学べばいいのかわからない…」——そんな<strong>迷える子羊</strong>のあなたへ。世界中の投資家に長く読み継がれてきた<strong>定番の名著だけ</strong>を、目的別に厳選しました。</p>
    <div class="hero-rule"></div>
    <p class="hero-meta">更新日 {UPDATED} ・ {SITE_NAME}編集部</p>
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
    body = f"""
<main class="container container--narrowtop">
  {breadcrumb([("TOP", "/"), (t["name"], None)])}
  <header class="page-head">
    <p class="hero-eyebrow">目的別おすすめ</p>
    <h1 class="page-title">{esc(t["name"])}の<br><em>おすすめ投資本</em></h1>
    <p class="page-lead">{esc(t["lead"])}</p>
    <p class="page-count">{len(items)}冊を厳選</p>
  </header>
  <section class="book-grid">
    {cards if items else '<p>準備中です。</p>'}
  </section>
  <section class="about-box">
    {section_title("ほかのテーマも見る")}
    <div class="chip-row">{other}</div>
  </section>
</main>"""
    return head(f"{t['name']}のおすすめ投資本", f"{t['name']}の投資初心者・実践者に向けて、定番のおすすめ本を厳選。{t['lead']}", f"/{t['slug']}/") + header() + body + footer()


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
        {price}
        <p class="bd-who"><span>こんな人におすすめ</span>{esc(b["who"])}</p>
        {cta(b)}
      </div>
    </div>
    <section class="bd-review">
      {section_title("どんな本？", "編集部レビュー")}
      <p>{esc(b["review"])}</p>
      <h3 class="bd-subh">この本で得られること</h3>
      <ul class="book-points bd-points">{points}</ul>
      <div class="bd-theme-links">関連テーマ：{theme_links}</div>
      {cta(b)}
    </section>
  </article>
  <section class="about-box">
    {section_title("あわせて読みたい")}
    <div class="mini-grid">{rel_cards}</div>
  </section>
</main>"""
    return head(f"{b['title']}｜要点と感想・どんな人におすすめ？", f"{b['title']}（{b['author_disp']}）のレビュー。{b['desc']} {b['who']}に。", f"/books/{b['slug']}/") + header() + body + footer()


def page_guide(books):
    # original guidance content
    beginner_books = sorted([b for b in books if "beginner" in b["themes"]], key=lambda x: x["rank"])[:3]
    blist = "".join(f'<li><a href="/books/{b["slug"]}/">{esc(b["title"])}</a> — {esc(b["who"])}</li>' for b in beginner_books)
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
    <p class="guide-cta-note">気になった本は各ページの「Amazonで見る／楽天ブックスで見る」からチェックできます。</p>
  </article>
</main>"""
    return head("投資本の選び方・読む順ガイド", "投資の本をどれから読めばいい？ レベル別の読む順番と、本を選ぶときの注意点を初心者向けにやさしく解説します。", "/guide/") + header() + body + footer()


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
    for t in THEMES:
        write(f"{t['slug']}/index.html", page_theme(t, books))
    for b in books:
        write(f"books/{b['slug']}/index.html", page_book(b, books))

    # sitemap.xml（全ページ）
    urls = ["/", "/guide/"] + [f"/{t['slug']}/" for t in THEMES] + [f"/books/{b['slug']}/" for b in books]
    lastmod = UPDATED.replace(".", "-")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        pr = "1.0" if u == "/" else ("0.8" if u.count("/") == 2 else "0.6")
        sm.append(f"  <url><loc>{SITE}{u}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>{pr}</priority></url>")
    sm.append("</urlset>\n")
    write("sitemap.xml", "\n".join(sm))

    n_pages = 2 + len(THEMES) + len(books)
    print(f"[build] {len(books)}冊 / {n_pages}ページ生成（トップ・ガイド・カテゴリ{len(THEMES)}・個別{len(books)}）", file=sys.stderr)


if __name__ == "__main__":
    main()

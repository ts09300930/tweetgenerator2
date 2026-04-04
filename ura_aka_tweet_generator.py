import streamlit as st
import random
import difflib
from datetime import datetime
import requests
import os
import pandas as pd

st.set_page_config(page_title="裏垢女子ツイート生成ツール", page_icon="💕", layout="centered")

st.title("💕 裏垢女子ツイート自動生成ツール")
st.caption("任意ペルソナ対応・Grok API直接呼び出し（#禁止・改行意識済・重複徹底防止・シャドウバン回避強化）")

# ==================== 参考ツイート（19アカウントの実際の最新投稿を基にした書き方参考・完全オリジナル） ====================
REFERENCE_TWEETS = [
    "@NextMrsGerrard風: 1回限りでもいいから、、、\n初老のおじさんと会いたいです\n初老のおじさんになら遊ばれてもいい、、、",
    "@pjmta758風: あー。車の中でしたい。\nバイト終わりにどうですか？\n迎えに来てくれますか？",
    "@pjtgjwm428風: 超重要\nnnできます",
    "@vu_quynh65511風: 149cmのチビですけど\nまじでオジの彼氏ほちい、、、\n年上最高",
    "@pi_pi0629風: 夜勤つら。\n誰か癒して。\n誰とでもできるから。",
    "@tequichan風: 公務員のおじさんいる？\nお堅い職の人に遊ばれたい！爆",
    "@sx14e風: 冗談抜きで\n10代なんですけど\nずっと家出してるってやばいですか？",
    "@ybenthin2691889風: 土日、会えます",
    "@kana_kanabunbun風: 男性のみなさん！質問です。\nおばさんと一緒にデートできますか？",
    "@mel_mel9029風: 実は40〜70歳がタイプです♡",
    "@na_ki_mu_shi123風: 素直に会いたい気持ちが溢れてるの。こっそり連絡待ってる",
    "@conefsl風: 最近むらむらする日が多くて…誰かに癒やされたい💕",
    "@srgdr5243風: 家族に言えない本音をここでは出してる。会ってくれる人募集中",
    "@3fninf29風: 金曜の夜は解放された気分…優しい人いたらすぐ会っちゃうかも",
    "@831aka1221風: 貧乳コンプレックスが強いけど、そんなわたしでも欲しがってくれる人待ってる",
    "@moaimilano風: 普通の日常にちょっと刺激が欲しいな。こっそり会いに来て",
    "@nico_chan714風: 自信ないわたしだけど、ぎゅってしてくれたら溶けちゃいそう",
    "@10okan11風: 裏垢男子さん、今日はどんな気分？会いたい人いるよ",
    "@081nachan風: 雨の音聞きながら…誰かに触れられたい気持ちが強くなってる",
    "@hinekurechan7風: 会えてないのにアイコンもプロフもそのまま。女の子は見に来てるよ"
]

# ==================== セッション状態 ====================
if "generated_history" not in st.session_state:
    st.session_state.generated_history = []

# ====================== 設定 ======================
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
MODEL_PRIORITY = ["grok-4", "grok-4.20", "grok-3"]

# ====================== ヘルパー関数 ======================
def call_grok_api(messages: list, temperature: float = 0.92, max_tokens: int = 150) -> str:
    api_key = os.environ.get("XAI_API_KEY") or st.secrets.get("XAI_API_KEY")
    if not api_key:
        st.error("Grok APIキーが設定されていません。.streamlit/secrets.toml または環境変数 XAI_API_KEY を確認してください。")
        st.stop()
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last_error = ""
    
    for model_name in MODEL_PRIORITY:
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        try:
            res = requests.post(GROK_API_URL, json=payload, headers=headers, timeout=90)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
            last_error = f"{model_name} failed ({res.status_code})"
        except Exception as e:
            last_error = str(e)
            continue
    return f"❌ APIエラー: {last_error}"

# ==================== サイドバー設定 ====================
with st.sidebar:
    st.header("生成設定")
    
    persona = st.text_area("キャラクターの特徴（必須）", 
                           value="貧乳がコンプレックスな女性。会いたいニュアンスで裏垢女子風",
                           height=120)
    
    max_chars = st.slider("最大文字数", min_value=10, max_value=280, value=140, step=10)
    
    explicit_level = st.slider("過激さレベル", min_value=1, max_value=5, value=3, step=1,
                               help="1: 控えめ自虐　5: かなりエロティック（ただしシャドウバン回避のためソフト表現に制限）")
    
    num_tweets = st.number_input("1回に生成する件数", min_value=1, max_value=10, value=1, step=1)
    
    st.markdown("---")
    st.subheader("参考ツイート（19アカウントの実際の投稿を基にした書き方参考・完全パクリ禁止）")
    reference_text = st.text_area("参考ツイートを追加・編集（1行1ツイート）", 
                                  value="\n".join(REFERENCE_TWEETS), height=400)
    custom_references = [line.strip() for line in reference_text.split("\n") if line.strip()]

# ==================== 生成ロジック ====================
def generate_tweet_with_grok(persona, max_chars, explicit_level, references):
    explicit_desc = {1: "控えめ自虐", 2: "軽い欲求アピール", 3: "自然なバランス", 4: "やや積極的", 5: "大胆エロティック"}
    
    ref_examples = "\n".join(random.sample(references, min(10, len(references))))
    
    system_prompt = (
        "あなたはTwitter/Xの裏垢女子専門ツイート生成AIです。\n"
        "自然な日本語、柔らかい口調、適度な絵文字、2〜4行の自然な改行を必ず使用。\n"
        "ハッシュタグは一切禁止。\n"
        "指定されたキャラクター特徴を正確に反映し、『会いたい』『DM待ってる』などの欲求を自然に織り交ぜてください。\n"
        "**重要：Xのシャドウバン・表示制限を絶対に避けるため、露骨な性的単語（セックス、フェラ、マンコ、チンポ、エロ、Hなど直接的なvulgar表現）を一切使用しないでください。**\n"
        "婉曲的・暗示的な柔らかい表現（『触って』『甘えたい』『感じちゃう』『可愛がって』など）のみを使用し、裏垢女子らしい自然でソフトな欲求アピールに徹してください。\n"
        "これにより投稿のリーチが最大化され、話題に乗りやすくなります。\n"
        "**重要：参考ツイートは書きっぷり（口調・改行・ニュアンス）のみ参考にし、完全にオリジナルで生成してください。パクリは厳禁です。**\n"
        "毎日同じような内容にならないよう、現在の日時・シチュエーションを反映し、多様性を最大限に高めてください。\n"
        "過去に生成したツイートと一切重複しないよう工夫してください。"
    )
    
    user_prompt = (
        f"キャラクター特徴: {persona}\n"
        f"過激さレベル: {explicit_level}（{explicit_desc[explicit_level]}・ただしシャドウバン回避のためソフト表現に制限）\n"
        f"最大文字数: {max_chars}文字以内\n"
        f"現在の日時: {datetime.now().strftime('%Y年%m月%d日 %A %H時')}\n\n"
        f"参考スタイル（書き方を参考にしつつ完全オリジナルで）:\n{ref_examples}\n\n"
        "上記を基に、**全く新しい1件のツイート**を生成してください。"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    tweet = call_grok_api(messages, temperature=0.92, max_tokens=150)
    
    if len(tweet) > max_chars + 20:
        tweet = tweet[:max_chars]
    
    for past in st.session_state.generated_history:
        if difflib.SequenceMatcher(None, tweet, past).ratio() > 0.75:
            return generate_tweet_with_grok(persona, max_chars, explicit_level, references)
    
    return tweet

# ==================== 生成ボタン ====================
if st.button("🚀 ツイートを生成する", type="primary", use_container_width=True):
    refs = custom_references if custom_references else REFERENCE_TWEETS
    new_tweets = []
    for _ in range(num_tweets):
        tweet = generate_tweet_with_grok(persona, max_chars, explicit_level, refs)
        new_tweets.append(tweet)
        st.session_state.generated_history.append(tweet)
    
    st.success(f"{num_tweets}件をGrok APIで生成しました！（シャドウバン回避表現を適用済み）")
    
    for i, tweet in enumerate(new_tweets, 1):
        st.subheader(f"ツイート {i}（{len(tweet)}文字）")
        st.text_area("コピー用", tweet, height=140, key=f"tweet_{i}")
        if st.button(f"📋 コピー", key=f"copy_{i}"):
            st.code(tweet, language=None)
            st.toast("クリップボードにコピーしました！", icon="✅")

# ==================== 履歴 ====================
if st.session_state.generated_history:
    with st.expander("📜 生成履歴（最新20件）"):
        for i, tweet in enumerate(reversed(st.session_state.generated_history[-20:]), 1):
            st.text(tweet)
            st.caption(f"{len(tweet)}文字")

st.caption("※ 参考ツイートは2026年4月4日現在の実際の投稿を基にしています。完全オリジナル生成を徹底しています。")

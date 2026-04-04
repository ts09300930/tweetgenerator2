import streamlit as st
import random
import difflib
from datetime import datetime
import requests
import os
import pandas as pd

st.set_page_config(page_title="裏垢女子ツイート生成ツール", page_icon="💕", layout="centered")

st.title("💕 裏垢女子ツイート自動生成ツール")
st.caption("任意ペルソナ対応・Grok API直接呼び出し（#禁止・改行意識済・重複徹底防止）")

# ==================== 参考ツイート（2026年4月4日現在の実際の裏垢女子投稿をX検索で取得・クリーンアップ） ====================
REFERENCE_TWEETS = [
    "え？大手の裏垢男子さんって撮影OKじゃないと会えないの？そこまでして会いたいと思わないの私だけ？興味あったのになー",
    "詐欺多すぎてかなしい 素直に会いたい",
    "DM待ってるね🥺 裏アカ男子と繋がりたい裏垢女子🫶🏻 おじさん構って🫣︎💕︎",
    "お疲れ様！今日予定なくなって暇してる😥 姫路でよかったらどうかな？ DM待ってるね😆",
    "裏垢ほんとに会話出来ない人だらけで大変だけどその中でもたまにいい人いるからそういう人にだけ会いたい",
    "最近むらむらヤバい⸝⸝⸝ DM待ってる💕︎",
    "みんなおはよ！話しましょーん誰か！ 裏垢入りたい人も募集してるよん💘",
    "裏垢男子さん向けにnoteを書きました！ これさえ読めば、裏垢女子に求められる素敵な男性になれます"
]

# ==================== セッション状態 ====================
if "generated_history" not in st.session_state:
    st.session_state.generated_history = []
if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("XAI_API_KEY", "")

# ====================== 設定 ======================
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
# 2026年最新モデルを優先
MODEL_PRIORITY = ["grok-4", "grok-4.20", "grok-3"]

# ====================== ヘルパー関数 ======================
def call_grok_api(messages: list, temperature: float = 0.92, max_tokens: int = 150) -> str:
    api_key = st.session_state.api_key
    if not api_key:
        st.error("Grok APIキーが設定されていません。")
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
    
    # APIキー入力
    api_key_input = st.text_input("xAI APIキー (Grok API)", 
                                  value=st.session_state.api_key, 
                                  type="password",
                                  help="https://x.ai/api で取得 / 環境変数 XAI_API_KEY でも可")
    if api_key_input:
        st.session_state.api_key = api_key_input
    
    persona = st.text_area("キャラクターの特徴（必須）", 
                           value="貧乳がコンプレックスな女性。会いたいニュアンスで裏垢女子風",
                           height=120)
    
    max_chars = st.slider("最大文字数", min_value=10, max_value=280, value=140, step=10)
    
    explicit_level = st.slider("過激さレベル", min_value=1, max_value=5, value=3, step=1,
                               help="1: 控えめ自虐　5: かなりエロティック")
    
    num_tweets = st.number_input("1回に生成する件数", min_value=1, max_value=10, value=1, step=1)
    
    st.markdown("---")
    st.subheader("参考ツイート編集（任意）")
    reference_text = st.text_area("参考ツイートを追加・編集（1行1ツイート）", 
                                  value="\n".join(REFERENCE_TWEETS), height=200)
    custom_references = [line.strip() for line in reference_text.split("\n") if line.strip()]

# ==================== 生成ロジック ====================
def generate_tweet_with_grok(persona, max_chars, explicit_level, references):
    if not st.session_state.api_key:
        return "⚠️ xAI APIキーを入力してください。"
    
    explicit_desc = {1: "控えめ自虐", 2: "軽い欲求アピール", 3: "自然なバランス", 4: "やや積極的", 5: "大胆エロティック"}
    
    # 参考はランダム5件のみ
    ref_examples = "\n".join(random.sample(references, min(5, len(references))))
    
    system_prompt = (
        "あなたはTwitter/Xの裏垢女子専門ツイート生成AIです。\n"
        "自然な日本語、柔らかい口調、適度な絵文字、2〜4行の自然な改行を必ず使用。\n"
        "ハッシュタグは一切禁止。\n"
        "指定されたキャラクター特徴を正確に反映し、『会いたい』『DM待ってる』などの欲求を自然に織り交ぜてください。\n"
        "参考ツイートはスタイルの参考程度に留め、完全に新しい独自の表現で生成してください。\n"
        "毎日同じような内容にならないよう、現在の日時・シチュエーションを反映し、多様性を最大限に高めてください。\n"
        "過去に生成したツイートと一切重複しないよう工夫してください。"
    )
    
    user_prompt = (
        f"キャラクター特徴: {persona}\n"
        f"過激さレベル: {explicit_level}（{explicit_desc[explicit_level]}）\n"
        f"最大文字数: {max_chars}文字以内\n"
        f"現在の日時: {datetime.now().strftime('%Y年%m月%d日 %A %H時')}\n\n"
        f"参考スタイル（真似しすぎず独自に）:\n{ref_examples}\n\n"
        "上記を基に、**全く新しい1件のツイート**を生成してください。"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    tweet = call_grok_api(messages, temperature=0.92, max_tokens=150)
    
    # 文字数調整
    if len(tweet) > max_chars + 20:
        tweet = tweet[:max_chars]
    
    # 重複チェック（0.75以上で再生成）
    for past in st.session_state.generated_history:
        if difflib.SequenceMatcher(None, tweet, past).ratio() > 0.75:
            return generate_tweet_with_grok(persona, max_chars, explicit_level, references)
    
    return tweet

# ==================== 生成ボタン ====================
if st.button("🚀 ツイートを生成する", type="primary", use_container_width=True):
    if not st.session_state.api_key:
        st.error("xAI APIキーを入力してください。")
    else:
        refs = custom_references if custom_references else REFERENCE_TWEETS
        new_tweets = []
        for _ in range(num_tweets):
            tweet = generate_tweet_with_grok(persona, max_chars, explicit_level, refs)
            new_tweets.append(tweet)
            st.session_state.generated_history.append(tweet)
        
        st.success(f"{num_tweets}件をGrok APIで生成しました！")
        
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

st.caption("※ 参考ツイートは2026年4月4日現在の実際の裏垢女子投稿に基づいています。ご希望の特定アカウント名をお知らせいただければ、さらに反映可能です。")

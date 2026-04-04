import streamlit as st
import random
import difflib
from datetime import datetime
import requests
import os
import pandas as pd
import re

st.set_page_config(page_title="裏垢女子ツイート自動生成ツール", page_icon="💕", layout="centered")

st.title("💕 裏垢女子ツイート自動生成ツール")
st.caption("任意ペルソナ対応・口調指定・フォーマット傾向指定（#禁止・シャドウバン回避強化）")

# ==================== 参考アカウント一覧 ====================
REFERENCE_ACCOUNTS = [
    "NextMrsGerrard", "pjmta758", "pjtgjwm428", "vu_quynh65511", "pi_pi0629",
    "tequichan", "sx14e", "ybenthin2691889", "kana_kanabunbun", "mel_mel9029",
    "na_ki_mu_shi123", "conefsl", "srgdr5243", "3fninf29", "831aka1221",
    "moaimilano", "nico_chan714", "10okan11", "081nachan"
]

# ==================== セッション状態 ====================
if "generated_history" not in st.session_state:
    st.session_state.generated_history = []

# ====================== 設定 ======================
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
MODEL_PRIORITY = ["grok-4", "grok-4.20", "grok-3"]

# ====================== ヘルパー関数 ======================
def call_grok_api(messages: list, temperature: float = 0.85, max_tokens: int = 120) -> str:
    api_key = os.environ.get("XAI_API_KEY") or st.secrets.get("XAI_API_KEY")
    if not api_key:
        st.error("Grok APIキーが設定されていません。.streamlit/secrets.toml または環境変数 XAI_API_KEY を確認してください。")
        st.stop()
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last_error = ""
    for model_name in MODEL_PRIORITY:
        payload = {"model": model_name, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
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
                           height=100)
    
    # 口調タイプ
    tone_options = [
        "熟女系", "ギャル系", "清楚系", "ドS系", "女子大生風",
        "不思議ちゃん系", "甘えん坊系", "クール系", "おっとり系",
        "元気系", "病み系", "ツンデレ系", "お姉さん系", "妹系", "カスタム"
    ]
    tone_type = st.selectbox("口調タイプ", tone_options, index=2)
    if tone_type == "カスタム":
        custom_tone = st.text_input("カスタム口調を入力", value="清楚で甘えん坊な感じ")
        tone_display = custom_tone
    else:
        tone_display = tone_type
    
    # フォーマット傾向
    format_options = [
        "デフォルト（ランダム）",
        "自虐スタート型",
        "日常/状況スタート型",
        "甘え/ため息スタート型",
        "質問終わり型（どこ住みですか？など）",
        "直接呼びかけ型"
    ]
    format_type = st.selectbox("フォーマット傾向", format_options, index=0)
    
    apply_prob = st.slider("フォーマット適用確率 (%)", min_value=0, max_value=100, value=25, step=5)
    
    max_chars = st.slider("最大文字数", min_value=10, max_value=280, value=140, step=10)
    
    explicit_level = st.slider("過激さレベル", min_value=1, max_value=5, value=3, step=1)
    
    num_tweets = st.number_input("1回に生成する件数", min_value=1, max_value=10, value=1, step=1)

# ==================== 生成ロジック ====================
def generate_tweet_with_grok(persona, max_chars, explicit_level, tone_display, format_type, apply_prob):
    explicit_desc = {1: "控えめ自虐", 2: "軽い欲求アピール", 3: "自然なバランス", 4: "やや積極的", 5: "大胆エロティック"}
    
    use_format = random.random() * 100 < apply_prob
    
    # 口調に応じた絵文字ルール（熟女系などは♡を完全に禁止）
    mature_tones = ["熟女系", "お姉さん系", "ドS系", "クール系"]
    if tone_display in mature_tones or (tone_display == "カスタム" and any(t in tone_display for t in mature_tones)):
        emoji_rule = "**絵文字について：ハート♡や可愛らしい絵文字は一切使用しないでください。熟女らしい落ち着いた表現に徹してください。**"
    else:
        emoji_rule = "**絵文字について：ハート♡は過剰に使用せず、1ツイートに0〜1個程度に制限してください。**"
    
    system_prompt = (
        "あなたはTwitter/Xの裏垢女子専門ツイート生成AIです。\n"
        "自然な日本語、柔らかい口調を使用。\n"
        "ハッシュタグは一切禁止。\n"
        f"**口調タイプ**: {tone_display}（この口調を徹底してください）\n"
        f"**フォーマット傾向**: {'指定されたフォーマットを適用' if use_format else '通常'}（{format_type}）\n"
        "指定されたキャラクター特徴と口調を正確に反映し、『会いたい』『DM待ってる』などの欲求を自然に織り交ぜてください。\n"
        "**重要：Xのシャドウバン回避のため、露骨な性的単語は一切使用しない。**\n"
        f"{emoji_rule}\n"
        "生成するツイートは厳密に{max_chars}文字以内に収めてください。\n"
        "改行は自然な文の区切りで1〜2箇所程度に留めてください。\n"
        "参考アカウントの最新投稿は書きっぷり（口調・改行・ニュアンス）のみ参考にし、完全にオリジナルで生成してください。パクリは厳禁です。\n"
        "毎日同じような内容にならないよう、現在の日時・シチュエーションを反映してください。"
    )
    
    user_prompt = (
        f"キャラクター特徴: {persona}\n"
        f"口調タイプ: {tone_display}\n"
        f"フォーマット傾向: {format_type}（適用確率{apply_prob}%で適用）\n"
        f"過激さレベル: {explicit_level}（{explicit_desc[explicit_level]}）\n"
        f"最大文字数: **厳密に{max_chars}文字以内**\n"
        f"現在の日時: {datetime.now().strftime('%Y年%m月%d日 %A %H時')}\n"
        f"参考アカウント（最新投稿の書き方を参考に）：{', '.join(REFERENCE_ACCOUNTS)}\n\n"
        "上記を基に、**全く新しい1件のツイート**を生成してください。"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    for attempt in range(3):
        tweet = call_grok_api(messages, temperature=0.85, max_tokens=120)
        
        if len(tweet) > max_chars:
            tweet = tweet[:max_chars]
        
        tweet = re.sub(r'\n{2,}', '\n', tweet.strip())
        lines = tweet.split('\n')
        if len(lines) > 3:
            tweet = ' '.join(lines[:2]) + '\n' + ' '.join(lines[2:])
        
        duplicate = any(difflib.SequenceMatcher(None, tweet, past).ratio() > 0.75 
                       for past in st.session_state.generated_history)
        if not duplicate and len(tweet) <= max_chars:
            return tweet
    
    return tweet[:max_chars]

# ==================== 生成ボタン ====================
if st.button("🚀 ツイートを生成する", type="primary", use_container_width=True):
    new_tweets = []
    for _ in range(num_tweets):
        tweet = generate_tweet_with_grok(persona, max_chars, explicit_level, tone_display, format_type, apply_prob)
        new_tweets.append(tweet)
        st.session_state.generated_history.append(tweet)
    
    st.success(f"{num_tweets}件をGrok APIで生成しました！（口調:{tone_display}・フォーマット:{format_type} {apply_prob}%適用）")
    
    for i, tweet in enumerate(new_tweets, 1):
        st.subheader(f"ツイート {i}（{len(tweet)}文字）")
        st.text_area("コピー用", tweet, height=120, key=f"tweet_{i}")
        if st.button(f"📋 コピー", key=f"copy_{i}"):
            st.code(tweet, language=None)
            st.toast("クリップボードにコピーしました！", icon="✅")

# ==================== 履歴 ====================
if st.session_state.generated_history:
    with st.expander("📜 生成履歴（最新20件）"):
        for i, tweet in enumerate(reversed(st.session_state.generated_history[-20:]), 1):
            st.text(tweet)
            st.caption(f"{len(tweet)}文字")

st.caption("※ 19アカウントの最新投稿を毎回参考に分析して生成しています（パクリ厳禁）。熟女系・お姉さん系・ドS系・クール系では♡を完全に禁止しました。")

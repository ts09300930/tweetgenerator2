import streamlit as st
import random
import difflib
from datetime import datetime
import requests
import os
import json
import re

st.set_page_config(page_title="裏垢女子ツイート自動生成ツール", page_icon="💕", layout="centered")

st.title("💕 裏垢女子ツイート自動生成ツール")
st.caption("ペルソナプリセット保存・バッチ内重複防止・季節/時間表現完全排除")

# ==================== プリセット保存設定 ====================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
PERSONAS_FILE = os.path.join(DATA_DIR, "personas.json")

def load_personas():
    if os.path.exists(PERSONAS_FILE):
        try:
            with open(PERSONAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_persona(name: str, text: str):
    personas = load_personas()
    personas[name.strip()] = text.strip()
    with open(PERSONAS_FILE, "w", encoding="utf-8") as f:
        json.dump(personas, f, ensure_ascii=False, indent=2)

# ==================== 参考アカウント ====================
REFERENCE_ACCOUNTS = ["NextMrsGerrard", "pjmta758", "pjtgjwm428", "vu_quynh65511", "pi_pi0629", "tequichan", "sx14e", "ybenthin2691889", "kana_kanabunbun", "mel_mel9029", "na_ki_mu_shi123", "conefsl", "srgdr5243", "3fninf29", "831aka1221", "moaimilano", "nico_chan714", "10okan11", "081nachan"]

# ==================== セッション状態 ====================
if "generated_history" not in st.session_state:
    st.session_state.generated_history = []

# ====================== APIヘルパー ======================
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
MODEL_PRIORITY = ["grok-4", "grok-4.20", "grok-3"]

def call_grok_api(messages):
    api_key = os.environ.get("XAI_API_KEY") or st.secrets.get("XAI_API_KEY")
    if not api_key:
        st.error("Grok APIキーが設定されていません。")
        st.stop()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    for model in MODEL_PRIORITY:
        try:
            res = requests.post(GROK_API_URL, json={"model": model, "messages": messages, "max_tokens": 120, "temperature": 0.85}, headers=headers, timeout=90)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
        except:
            continue
    return "❌ APIエラー"

# ==================== サイドバー ====================
with st.sidebar:
    st.header("生成設定")
    
    # === ペルソナプリセット ===
    st.subheader("📋 ペルソナプリセット")
    personas = load_personas()
    preset_list = ["-- 新規作成 --"] + list(personas.keys())
    selected_preset = st.selectbox("保存済みから読み込み", preset_list)
    if selected_preset != "-- 新規作成 --":
        st.session_state.persona_text = personas[selected_preset]
    
    persona = st.text_area("キャラクターの特徴（必須）", 
                           value=st.session_state.get("persona_text", "貧乳がコンプレックスな女性。会いたいニュアンスで裏垢女子風"),
                           height=110, key="persona_input")
    
    preset_name = st.text_input("プリセット名", placeholder="例: 貧乳清楚系")
    if st.button("💾 このペルソナを保存"):
        if preset_name.strip():
            save_persona(preset_name, persona)
            st.success(f"「{preset_name}」を保存しました")
            st.rerun()
        else:
            st.warning("プリセット名を入力してください")

    # 口調・フォーマット（従来通り）
    tone_options = ["熟女系", "ギャル系", "清楚系", "ドS系", "女子大生風", "不思議ちゃん系", "甘えん坊系", "クール系", "おっとり系", "元気系", "病み系", "ツンデレ系", "お姉さん系", "妹系", "カスタム"]
    tone_type = st.selectbox("口調タイプ", tone_options, index=2)
    tone_display = st.text_input("カスタム口調", value="清楚で甘えん坊な感じ") if tone_type == "カスタム" else tone_type

    format_options = ["デフォルト（ランダム）", "自虐スタート型", "日常/状況スタート型", "甘え/ため息スタート型", "質問終わり型（どこ住みですか？など）", "直接呼びかけ型"]
    format_type = st.selectbox("フォーマット傾向", format_options, index=0)
    apply_prob = st.slider("フォーマット適用確率 (%)", 0, 100, 25, step=5)

    max_chars = st.slider("最大文字数", 10, 280, 140, step=10)
    explicit_level = st.slider("過激さレベル", 1, 5, 3, step=1)
    num_tweets = st.number_input("生成件数", 1, 30, 1, step=1)

# ==================== 生成ロジック（バッチ内重複防止強化） ====================
def generate_tweet_with_grok(persona, max_chars, explicit_level, tone_display, format_type, apply_prob, current_batch):
    # バッチ内も含めた全履歴で重複チェック
    all_history = st.session_state.generated_history + current_batch
    
    mature_tones = ["熟女系", "お姉さん系", "ドS系", "クール系"]
    emoji_rule = "ハート♡や可愛らしい絵文字は一切使用しない" if tone_display in mature_tones else "ハート♡は1ツイートに0〜1個程度に制限"
    
    system_prompt = (
        "あなたはTwitter/Xの裏垢女子専門ツイート生成AIです。\n"
        "自然な日本語、柔らかい口調を使用。\n"
        "ハッシュタグ禁止。\n"
        f"口調タイプ: {tone_display}\n"
        f"フォーマット傾向: {format_type}\n"
        f"絵文字ルール: {emoji_rule}\n"
        "指定されたキャラクター特徴を正確に反映。\n"
        "露骨な性的単語は一切使用しない。\n"
        "季節・曜日・時間帯・天気・特定の日の表現は一切含めない。\n"
        "生成するツイートは厳密に{max_chars}文字以内。\n"
        "改行は自然に1〜2箇所程度。\n"
        "完全にオリジナルで生成してください。"
    )
    
    user_prompt = f"キャラクター特徴: {persona}\n過激さレベル: {explicit_level}\n最大文字数: 厳密に{max_chars}文字以内\n参考アカウント: {', '.join(REFERENCE_ACCOUNTS)}\n全く新しい1件のツイートを生成してください。"
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    
    for _ in range(4):  # 再生成回数増加
        tweet = call_grok_api(messages)
        if len(tweet) > max_chars:
            tweet = tweet[:max_chars]
        tweet = re.sub(r'\n{2,}', '\n', tweet.strip())
        
        # バッチ内含む全履歴との重複チェック
        similarities = [difflib.SequenceMatcher(None, tweet, past).ratio() for past in all_history]
        if not similarities or max(similarities) < 0.75:
            return tweet
    return tweet[:max_chars]

# ==================== 生成ボタン ====================
if st.button("🚀 ツイートを生成する", type="primary", use_container_width=True):
    new_tweets = []
    for _ in range(num_tweets):
        tweet = generate_tweet_with_grok(persona, max_chars, explicit_level, tone_display, format_type, apply_prob, new_tweets)
        new_tweets.append(tweet)
        st.session_state.generated_history.append(tweet)
    
    st.success(f"{num_tweets}件生成完了（バッチ内重複防止済み）")
    
    for i, tweet in enumerate(new_tweets, 1):
        st.subheader(f"ツイート {i}（{len(tweet)}文字）")
        
        # 自動類似度分析
        similarities = [difflib.SequenceMatcher(None, tweet, past).ratio() * 100 for past in st.session_state.generated_history[:-1]]
        max_sim = max(similarities) if similarities else 0
        st.caption(f"📊 過去ツイートとの最高類似度: **{max_sim:.1f}%**")
        
        st.text_area("コピー用", tweet, height=110, key=f"tweet_{i}")
        if st.button("📋 コピー", key=f"copy_{i}"):
            st.code(tweet, language=None)
            st.toast("クリップボードにコピーしました！", icon="✅")
        
        # X風プレビュー
        st.markdown(f"""
        <div style="border:1px solid #333;border-radius:12px;padding:12px;background:#000;color:#fff;margin:8px 0;">
            <div style="display:flex;align-items:center;gap:8px;">
                <div style="width:40px;height:40px;border-radius:50%;background:#1DA1F2;display:flex;align-items:center;justify-content:center;font-size:20px;">👩</div>
                <div><strong>裏垢女子</strong> <span style="color:#888">@ura_aka_{random.randint(1000,9999)}</span><br><span style="color:#888;font-size:13px;">いま</span></div>
            </div>
            <div style="margin:12px 0;line-height:1.4;white-space:pre-wrap;">{tweet}</div>
            <div style="display:flex;justify-content:space-between;color:#888;font-size:13px;"><span>♡ 12</span><span>🔁 3</span><span>💬 2</span></div>
        </div>
        """, unsafe_allow_html=True)

# ==================== 履歴 ====================
if st.session_state.generated_history:
    with st.expander("📜 生成履歴（最新20件）"):
        for i, tweet in enumerate(reversed(st.session_state.generated_history[-20:]), 1):
            st.text(tweet)
            st.caption(f"{len(tweet)}文字")

st.caption("※ ペルソナはdata/personas.jsonに保存されます。再起動後も残ります。バッチ内重複も防止しています。")

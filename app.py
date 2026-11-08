import os

import streamlit as st
from groq import Groq
import re

st.set_page_config(
    page_title="Chat Bot",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------- Settings you can edit ----------
# Groq models are tried in this order. If one fails, the next one is used.
GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
]
TEMPERATURE = 0.4

BASE_PROMPT = (
    "The users are school students below 10th class. Use simple words and "
    "short, clear answers."
)

MODES = {
    "General assistant": {
        "prompt": (
            "You are a clear, friendly assistant. Answer in plain language and keep "
            "answers concise. Use short lists or steps only when they help. "
            "If a request is ambiguous, ask one short clarifying question."
        ),
        "starters": [
            "Explain something simply",
            "Help me write an email",
            "Plan my week",
            "Give me a quick summary of a topic",
        ],
    },
    "Tax helper (Pakistan)": {
        "prompt": (
            "You are a tax assistant for Pakistan. Explain income tax, NTN registration, "
            "return filing, withholding tax, and FBR/IRIS procedures in simple language. "
            "Give practical steps. Tax rules and rates change often, so remind the user to "
            "confirm current rates and deadlines with FBR or a tax professional when it matters."
        ),
        "starters": [
            "How do I get an NTN?",
            "Who must file an income tax return?",
            "What is the difference between filer and non-filer?",
            "What documents do I need to file a return?",
        ],
    },
    "Study buddy": {
        "prompt": (
            "You are a patient study buddy. Explain concepts in simple English with one "
            "short example, then check understanding with a quick question. "
            "Offer mock questions when asked."
        ),
        "starters": [
            "Quiz me on a topic",
            "Explain a concept with an example",
            "Make short revision notes",
            "Give me 5 practice questions",
        ],
    },
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
    color-scheme: dark;
    --bg: #080d18;
    --panel: #111b2b;
    --border: #2a3b52;
    --text: #e8eef7;
    --muted: #9aabc0;
    --accent: #2dd4bf;
    --accent-2: #6366f1;
}

html, body, .stApp, button, input, textarea, select {
    font-family: 'Manrope', sans-serif !important;
}

/* Background */
.stApp {
    background:
        radial-gradient(ellipse at 80% -10%, rgba(45,212,191,.14), transparent 40%),
        radial-gradient(ellipse at 0% 100%, rgba(99,102,241,.10), transparent 40%),
        var(--bg);
    color: var(--text);
}

/* Header: transparent, hide Deploy + menu */
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
.stDeployButton, [data-testid="manage-app-button"],
[class*="viewerBadge"], #MainMenu, footer {
    display: none !important;
    visibility: hidden !important;
}

/* Settings button (opens the left panel) */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--accent) !important;
    transition: all .2s ease;
}
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="collapsedControl"] button:hover {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(45,212,191,.15);
}

/* Slow slide-in for the left panel */
[data-testid="stSidebar"] {
    transition: transform .6s ease, margin-left .6s ease, width .6s ease,
                min-width .6s ease !important;
}

.block-container {
    max-width: 900px;
    padding: 1.5rem 1.5rem 9rem !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e1726, #0a111d);
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--text) !important; }

/* Dropdowns (fixes the white boxes) */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {
    background: var(--panel) !important;
    border-color: var(--border) !important;
    border-radius: 10px !important;
}
[data-baseweb="select"] div,
[data-baseweb="select"] span,
[data-baseweb="select"] svg {
    color: var(--text) !important;
    fill: var(--text) !important;
}
[data-baseweb="popover"] ul,
[data-baseweb="popover"] [data-baseweb="menu"] {
    background: var(--panel) !important;
}
[data-baseweb="popover"] li:hover { background: #173044 !important; }

/* Chat messages */
[data-testid="stChatMessage"] {
    background: rgba(17,27,43,.7);
    border: 1px solid rgba(52,70,94,.55);
    border-radius: 18px;
    padding: 14px 18px;
    margin-bottom: 14px;
    backdrop-filter: blur(6px);
    animation: fade-up .3s ease-out;
}
/* User message looks different */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg, rgba(45,212,191,.16), rgba(45,212,191,.05));
    border-color: rgba(45,212,191,.35);
}
[data-testid="stChatMessage"] p {
    color: var(--text);
    line-height: 1.75;
    overflow-wrap: anywhere;
}

/* Avatars: match the theme */
[data-testid="stChatMessageAvatarUser"],
[data-testid="chatAvatarIcon-user"] {
    background: #334155 !important;
    border-radius: 12px !important;
}
[data-testid="stChatMessageAvatarAssistant"],
[data-testid="chatAvatarIcon-assistant"] {
    background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
    border-radius: 12px !important;
}

/* Bottom bar (fixes the white strip) */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"] {
    background: transparent !important;
}
[data-testid="stBottom"] > div {
    background: linear-gradient(to top, var(--bg) 70%, transparent) !important;
    padding-bottom: 34px !important;
}

/* Chat input */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div {
    background: var(--panel) !important;
    border-radius: 16px !important;
}
[data-testid="stChatInput"] {
    border: 1px solid var(--border) !important;
    box-shadow: 0 8px 30px rgba(0,0,0,.35);
    transition: border-color .2s, box-shadow .2s;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(45,212,191,.15), 0 8px 30px rgba(0,0,0,.35);
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #f1f5f9 !important;
    -webkit-text-fill-color: #f1f5f9 !important;
    caret-color: var(--accent) !important;
    font-size: 15px !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
    -webkit-text-fill-color: #94a3b8 !important;
    opacity: 1 !important;
}
[data-testid="stChatInput"] button {
    background: var(--accent) !important;
    color: #042f2e !important;
    border-radius: 10px !important;
    transition: transform .15s ease;
}
[data-testid="stChatInput"] button:hover { transform: scale(1.08); }
[data-testid="stChatInput"] button:disabled {
    background: #1b2a3f !important;
    color: #64748b !important;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: .7rem .9rem;
    transition: all .2s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: #173044;
    color: #fff;
    border-color: var(--accent);
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(45,212,191,.15);
}

/* App title + footer */
.app-title {
    text-align: center;
    font-size: clamp(1.8rem, 5vw, 2.6rem);
    font-weight: 800;
    letter-spacing: -.03em;
    background: linear-gradient(90deg, #f1f5f9, var(--accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: fade-up .5s ease-out;
}
.app-sub {
    text-align: center;
    color: var(--muted);
    margin: .2rem 0 1.2rem;
    animation: fade-up .7s ease-out;
}
.app-footer {
    position: fixed;
    left: 0; right: 0; bottom: 0;
    z-index: 999;
    text-align: center;
    padding: 6px 10px;
    font-size: 12.5px;
    color: var(--muted);
    background: var(--bg);
    border-top: 1px solid var(--border);
}
.app-footer b { color: var(--accent); }

/* Selected subject button */
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--accent), #14b8a6) !important;
    color: #042f2e !important;
    border-color: transparent !important;
    font-weight: 700;
}

/* Welcome screen */
.empty-title {
    font-size: clamp(2rem, 5vw, 3rem);
    font-weight: 800;
    letter-spacing: -.04em;
    margin: 1.5rem 0 .5rem;
    background: linear-gradient(90deg, #f1f5f9, var(--accent));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: fade-up .5s ease-out;
}
.empty-sub {
    color: var(--muted);
    margin-bottom: 1.5rem;
    line-height: 1.7;
    animation: fade-up .7s ease-out;
}

/* Typing dots */
.typing { display: flex; gap: 6px; padding: 6px 2px; }
.typing span {
    width: 8px; height: 8px;
    background: var(--accent);
    border-radius: 50%;
    animation: bounce 1.2s infinite ease-in-out;
}
.typing span:nth-child(2) { animation-delay: .15s; }
.typing span:nth-child(3) { animation-delay: .3s; }

/* Thin scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-thumb { background: #26364b; border-radius: 8px; }

@keyframes fade-up {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: .4; }
    40%           { transform: translateY(-6px); opacity: 1; }
}

/* Mobile */
@media (max-width: 768px) {
    .block-container { padding: 1rem .8rem 8rem !important; }
    .app-footer { font-size: 11.5px; }
    [data-testid="stChatMessage"] { padding: 11px 12px; border-radius: 14px; }
    [data-testid="stChatInput"] textarea { font-size: 14px !important; }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)
st.markdown(
    '<div class="app-footer">Developed by <b>GBHSS Sultan Kot</b></div>',
    unsafe_allow_html=True,
)


# ---------- API keys ----------
def get_key(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name)


# ---------- Input and output guardrails ----------
GUARDRAIL_REPLY = (
    "Sorry, I can't help with that request. "
    "Please ask something safe and constructive."
)

UNSAFE_PATTERNS = [
    r"\bhow\s+to\s+(?:kill|murder|poison)\s+(?:someone|somebody|a person|myself)\b",
    r"\b(?:make|build|create)\s+(?:a\s+)?(?:bomb|explosive)\b",
    r"\b(?:write|send|make)\s+(?:a\s+)?death\s+threat\b",
    r"\bhow\s+can\s+i\s+(?:hurt|kill|attack)\s+(?:someone|somebody)\b",
    r"\b(?:help|teach|show)\s+me\s+to\s+(?:kill|murder|poison)\b",
]

def trips_guardrail(text):
    """Basic pattern-based check for clearly harmful requests or responses."""
    text = text.lower()
    return any(re.search(pattern, text) for pattern in UNSAFE_PATTERNS)


# ---------- State ----------
st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending", None)

# ---------- Left panel (opens with the settings button) ----------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    mode = st.radio("Assistant", list(MODES))
    st.divider()
    if st.button("🗑️ New chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    if st.session_state.messages:
        transcript = "\n\n".join(
            f"{'You' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in st.session_state.messages
        )
        st.download_button("⬇️ Download chat", transcript, "chat.txt", use_container_width=True)

# ---------- Header ----------
st.markdown('<div class="app-title">🎓 Chat Bot</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">Your friendly study helper</div>', unsafe_allow_html=True)

# ---------- Groq client ----------
api_key = get_key("GROQ_API_KEY")
if not api_key:
    st.error("GROQ_API_KEY not found. Add it to .streamlit/secrets.toml (or Streamlit Secrets).")
    st.stop()
client = Groq(api_key=api_key)

# ---------- Get the new prompt (typed or from a starter button) ----------
prompt = st.chat_input("Type your message")
if st.session_state.pending:
    prompt, st.session_state.pending = st.session_state.pending, None
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

# ---------- Empty state ----------
if not st.session_state.messages:
    st.markdown('<div class="empty-title">How can I help?</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="empty-sub">{mode}. Pick a starter or type below.</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, starter in enumerate(MODES[mode]["starters"]):
        if cols[i % 2].button(starter, key=f"starter_{i}", use_container_width=True):
            st.session_state.pending = starter
            st.rerun()

# ---------- Chat history ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- Stream the reply ----------
def stream_reply(model):
    system = (
        BASE_PROMPT + "\n\n" + MODES[mode]["prompt"]
        + "\n\nSafety and scope rules: Do not provide instructions for threats, "
          "violence, or harmful wrongdoing, and never give adult content. "
          "Politely refuse such requests and offer a safe alternative. "
          "In Tax helper mode, redirect unrelated questions to Pakistani tax "
          "topics. In Study buddy mode, redirect unrelated questions to "
          "learning and study topics."
    )
    history = st.session_state.messages
    stream = client.chat.completions.create(
        model=model, max_tokens=1500, temperature=TEMPERATURE, stream=True,
        messages=[{"role": "system", "content": system}] + history,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def generate_reply():
    """Try each Groq model in order. If one fails, use the next one."""
    last_error = None
    for model in GROQ_MODELS:
        try:
            text = "".join(stream_reply(model))
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            if not text:
                raise ValueError("Empty reply")
            return text
        except Exception as e:
            last_error = e
            if "401" in str(e) or "authentication" in str(e).lower():
                break  # a wrong key will fail on every model
    raise last_error


if prompt:
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown(
            '<div class="typing"><span></span><span></span><span></span></div>',
            unsafe_allow_html=True,
        )
        try:
            # Input guardrail: block clearly harmful requests before calling a model.
            if trips_guardrail(prompt):
                reply = GUARDRAIL_REPLY
            else:
                reply = generate_reply()
                # Output guardrail: replace clearly harmful generated content.
                if trips_guardrail(reply):
                    reply = GUARDRAIL_REPLY

            placeholder.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            placeholder.empty()
            st.session_state.messages.pop()
            text = str(e)
            if "401" in text or "authentication" in text.lower():
                st.error("Groq rejected your API key. Check GROQ_API_KEY and try again.")
            elif "429" in text or "rate limit" in text.lower():
                st.error("Too many requests right now. Wait a moment and send your message again.")
            else:
                st.error(f"Something went wrong: {text}")
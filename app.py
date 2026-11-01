import os

import anthropic
import streamlit as st
from groq import Groq
import re

st.set_page_config(page_title="Assistant", page_icon="💬", layout="centered")

# ---------- Settings you can edit ----------
PROVIDERS = {
    "Claude": {
        "secret": "ANTHROPIC_API_KEY",
        "models": {
            "Fast": "claude-haiku-5-5",
            "Balanced": "claude-sonnet-5-5",
            "Most capable": "claude-opus-5-5",
        },
        "default": 1,
    },
    "Groq": {
        "secret": "GROQ_API_KEY",
        "models": {
            "GPT-OSS 20B": "openai/gpt-oss-20b",
            "GPT-OSS 120B": "openai/gpt-oss-120b",
            "Qwen 3.8 27B": "qwen/qwen3.8-27b",
        },
        "default": 0,
    },
}

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
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap');

html, body, .stApp, button, input, textarea { font-family: 'Manrope', sans-serif; }

#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

.block-container { max-width: 760px; padding-top: 2.2rem; padding-bottom: 7rem; }

[data-testid="stChatMessage"] {
    border-radius: 16px;
    padding: 14px 18px;
    margin-bottom: 10px;
    background: transparent;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #DCEFEB;
}
[data-testid="stChatMessage"] p { line-height: 1.65; }

[data-testid="stChatInput"] { border-radius: 14px; }

.stButton > button {
    border-radius: 12px;
    border: 1px solid #CFDAD8;
    padding: 0.7rem 0.9rem;
    text-align: left;
    font-weight: 500;
    transition: border-color .15s ease, background .15s ease;
}
.stButton > button:hover { border-color: #0F766E; background: #F0F8F6; color: #0F766E; }

.empty-title { font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; margin: 1.5rem 0 .2rem; }
.empty-sub { color: #5B6B69; margin-bottom: 1.4rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


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
    r"\\bhow\\s+to\\s+(?:kill|murder|poison)\\s+(?:someone|somebody|a person|myself)\\b",
    r"\\b(?:make|build|create)\\s+(?:a\\s+)?(?:bomb|explosive)\\b",
    r"\\b(?:write|send|make)\\s+(?:a\\s+)?death\\s+threat\\b",
    r"\\bhow\\s+can\\s+i\\s+(?:hurt|kill|attack)\\s+(?:someone|somebody)\\b",
    r"\\b(?:help|teach|show)\\s+me\\s+to\\s+(?:kill|murder|poison)\\b",
]

def trips_guardrail(text):
    """Basic pattern-based check for clearly harmful requests or responses."""
    text = text.lower()
    return any(re.search(pattern, text) for pattern in UNSAFE_PATTERNS)


# ---------- State ----------
st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending", None)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### Settings")
    mode = st.selectbox("Assistant", list(MODES))
    available = [p for p, c in PROVIDERS.items() if get_key(c["secret"])]
    provider = st.selectbox("Provider", available or list(PROVIDERS))
    cfg = PROVIDERS[provider]
    model_label = st.selectbox("Model", list(cfg["models"]), index=cfg["default"])
    temperature = st.slider("Creativity", 0.0, 1.0, 0.5, 0.1)
    st.divider()
    if st.button("New chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    if st.session_state.messages:
        transcript = "\n\n".join(
            f"{'You' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in st.session_state.messages
        )
        st.download_button("Download chat", transcript, "chat.txt", use_container_width=True)

# ---------- Provider client ----------
api_key = get_key(cfg["secret"])
if not api_key:
    st.error(f"{cfg['secret']} not found. Add it to .streamlit/secrets.toml (or Streamlit Secrets), or pick another provider in the sidebar.")
    st.stop()
client = anthropic.Anthropic(api_key=api_key) if provider == "Claude" else Groq(api_key=api_key)

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
def stream_reply():
    model = cfg["models"][model_label]
    system = (
        MODES[mode]["prompt"]
        + "\\n\\nSafety and scope rules: Do not provide instructions for threats, "
          "violence, or harmful wrongdoing. Politely refuse such requests and "
          "offer a safe alternative. In Tax helper mode, redirect unrelated "
          "questions to Pakistani tax topics. In Study buddy mode, redirect "
          "unrelated questions to learning and study topics."
    )
    history = st.session_state.messages
    if provider == "Claude":
        with client.messages.stream(
            model=model, max_tokens=1500, temperature=temperature,
            system=system, messages=history,
        ) as stream:
            yield from stream.text_stream
    else:
        stream = client.chat.completions.create(
            model=model, max_tokens=1500, temperature=temperature, stream=True,
            messages=[{"role": "system", "content": system}] + history,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


if prompt:
    with st.chat_message("assistant"):
        try:
            # Input guardrail: block clearly harmful requests before calling a model.
            if trips_guardrail(prompt):
                reply = GUARDRAIL_REPLY
            else:
                # Collect the generated text, check it, then display it.
                # This ensures an unsafe response is not shown before checking.
                reply = "".join(stream_reply())

                # Output guardrail: replace clearly harmful generated content.
                if trips_guardrail(reply):
                    reply = GUARDRAIL_REPLY

            st.markdown(reply)
            st.session_state.messages.append(
                {"role": "assistant", "content": reply}
            )
        except Exception as e:
            st.session_state.messages.pop()
            text = str(e)
            if "401" in text or "authentication" in text.lower():
                st.error(f"{provider} rejected your API key. Check {cfg['secret']} and try again.")
            elif "429" in text or "rate" in text.lower():
                st.error("Too many requests right now. Wait a moment and send your message again.")
            else:
                st.error(f"Something went wrong: {text}")

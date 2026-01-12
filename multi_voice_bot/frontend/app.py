import streamlit as st
import speech_recognition as sr
import requests
from gtts import gTTS
import os
import pygame
import tempfile

# Config
st.set_page_config(page_title="Voice Chatbot", layout="wide", initial_sidebar_state="expanded")

# Session state setup
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "recording" not in st.session_state:
    st.session_state.recording = False
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "language" not in st.session_state:
    st.session_state.language = "English"
if "previous_language" not in st.session_state:
    st.session_state.previous_language = "English"
if "last_processed_input" not in st.session_state:
    st.session_state.last_processed_input = ""
if "clear_input_flag" not in st.session_state:
    st.session_state.clear_input_flag = False
if "audio_data" not in st.session_state:
    st.session_state.audio_data = None

# Clear input at the top if flag is set
if st.session_state.clear_input_flag:
    if "user_input_key" in st.session_state:
        st.session_state.user_input_key = ""
    st.session_state.user_input = ""
    st.session_state.last_processed_input = ""
    st.session_state.clear_input_flag = False

# Sidebar
model_choice = st.sidebar.selectbox("Choose a model:", ["llama3.2:3b", ""])
if not model_choice:
    model_choice = "llama3.2:3b"
language_choice = st.sidebar.selectbox("Choose language:", ["English", "Hindi", "Telugu"])
# Detect language change mid-conversation
language_changed = language_choice != st.session_state.previous_language and st.session_state.chat_history
if language_changed:
    st.warning("You're changing your language. This may affect the conversation.")
    col_confirm, col_new = st.columns(2)
    with col_confirm:
        if st.button("OK to Continue"):
            st.session_state.language = language_choice
            st.session_state.previous_language = language_choice
            st.rerun()
    with col_new:
        if st.button("Start New Chat"):
            st.session_state.chat_history = []
            st.session_state.language = language_choice
            st.session_state.previous_language = language_choice
            st.rerun()
else:
    st.session_state.language = language_choice
st.sidebar.markdown("### 🎤 Voice-based Multilingual Chatbot")
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []
    st.session_state.user_input = ""
    st.session_state.last_processed_input = ""
    st.session_state.clear_input_flag = True
    st.rerun()

# Backend URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/chat")

recognizer = sr.Recognizer()
microphone = sr.Microphone()

# Text-to-Speech (now called only on button click)
def speak(text, lang_code):
    try:
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        tts = gTTS(text, lang=lang_code)
        tts.save(path)
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.8)
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(40)
        pygame.mixer.quit()
        os.remove(path)
    except Exception as e:
        st.error(f"🗣️ TTS Error: {e}. Falling back to text-only.")

# Recognize voice (IMPROVED: Longer noise adjust, dynamic threshold, more retries)
def start_listening():
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1.0)  # IMPROVED: Longer noise adjust
        recognizer.energy_threshold = 300  # IMPROVED: Lower threshold for sensitivity (adjust based on env)
        recognizer.dynamic_energy_threshold = True  # IMPROVED: Auto-adjust to noise
        st.toast("🎙️ Listening... Speak now", icon="🎤")
        try:
            audio = recognizer.listen(source, timeout=30, phrase_time_limit=60)
            return audio
        except sr.WaitTimeoutError:
            st.warning("⏱️ Listening timed out. No speech detected.")
        except Exception as e:
            st.error(f"🎤 Mic error: {e}")
    return None

def transcribe_audio(audio, retries=3):  # IMPROVED: Increased retries
    for attempt in range(retries):
        if audio:
            st.toast("✅ Processing speech...", icon="🔄")
            try:
                return recognizer.recognize_google(audio, language=get_lang_code(st.session_state.language))
            except sr.UnknownValueError:
                st.warning(f"❌ Could not understand audio (attempt {attempt+1}/{retries}).")
            except Exception as e:
                st.error(f"🎤 Recognition error: {e}")
    return ""

# Language code mapping
def get_lang_code(lang_name):
    return {"English": "en", "Hindi": "hi", "Telugu": "te"}.get(lang_name, "en")

# Title
st.title(f"🤖 Multilingual Voice Assistant Chatbot")

# Input at top
col1, col2 = st.columns([0.1, 0.9])
with col1:
    mic_label = "Stop 🎤" if st.session_state.recording else "🎤"
    if st.button(mic_label, use_container_width=True):
        if not st.session_state.recording:
            st.session_state.recording = True
            st.session_state.audio_data = start_listening()
            st.rerun()
        else:
            st.session_state.recording = False
            transcript = transcribe_audio(st.session_state.audio_data)
            st.session_state.audio_data = None
            if transcript:
                st.session_state.user_input = transcript
                if "user_input_key" in st.session_state:
                    st.session_state.user_input_key = transcript
            st.rerun()

# Input box
if "user_input_key" not in st.session_state:
    st.session_state.user_input_key = ""
user_input = col2.text_input("Type your question or use mic...", value=st.session_state.user_input_key, key="user_input_key")

# Process input if present
if user_input.strip() and user_input.strip() != st.session_state.last_processed_input:
    if user_input.lower().strip() == "exit":
        st.success("Session ended. Goodbye! 👋")
        st.session_state.chat_history = []
        st.session_state.clear_input_flag = True
        st.rerun()
    else:
        st.session_state.last_processed_input = user_input.strip()
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("🤖 Thinking..."):
            try:
                payload = {
                    "model": model_choice,
                    "messages": st.session_state.chat_history,
                    "language": st.session_state.language
                }
                headers = {"Content-Type": "application/json"}
                response = requests.post(BACKEND_URL, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                result = response.json()
                reply = result.get("answer", "Sorry, I didn't get that.")
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                # REMOVED: Automatic speak
            except requests.exceptions.Timeout:
                st.error("⚠️ Request timed out (504). Try a simpler query or check the backend.")
            except requests.exceptions.RequestException as e:
                st.error(f"⚠️ Backend connection failed: {e}. Is the server running?")
            except Exception as e:
                st.error(f"⚠️ Unexpected error: {e}")
        st.session_state.clear_input_flag = True
        st.session_state.user_input = ""
        st.rerun()

# Reset mic input
if st.session_state.user_input:
    st.session_state.user_input = ""

# Chat history at bottom
chat_container = st.container(height=400)
with chat_container:
    for idx, msg in enumerate(st.session_state.chat_history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":  # NEW: Read Aloud button for assistant messages
                if st.button("🔊", key=f"read_aloud_{idx}"):
                    speak(msg["content"], get_lang_code(st.session_state.language))

# Auto-scroll JS
st.components.v1.html(
    """
    <script>
        var chat = window.parent.document.querySelectorAll('[kind="container"]')[0];
        if (chat) {
            chat.scrollTop = chat.scrollHeight;
        }
    </script>
    """,
    height=0,
)


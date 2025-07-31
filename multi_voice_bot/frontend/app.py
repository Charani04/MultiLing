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
if "clear_input" not in st.session_state:
    st.session_state.clear_input = False
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "language" not in st.session_state:
    st.session_state.language = "English"

# Sidebar
model_choice = st.sidebar.selectbox("Choose a model:", ["llama3.2-vision:11b", "qwen2.5-coder:0.5b"])
language_choice = st.sidebar.selectbox("Choose language:", ["English", "Hindi", "Telugu"])
st.session_state.language = language_choice
st.sidebar.markdown("### 🎤 Voice-based Multilingual Chatbot")
st.sidebar.markdown("---")

# Backend URL
BACKEND_URL = "http://localhost:8000/chat"

recognizer = sr.Recognizer()
microphone = sr.Microphone()

# Text-to-Speech
def speak(text, lang_code):
    try:
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        tts = gTTS(text, lang=lang_code)
        tts.save(path)

        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(40)

        pygame.mixer.quit()
        os.remove(path)
    except Exception as e:
        st.error(f"🗣️ TTS Error: {e}")

# Recognize voice
def listen_and_transcribe():
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        st.toast("🎙️ Listening... Speak now", icon="🎤")
        try:
            audio = recognizer.listen(source, timeout=40, phrase_time_limit=40)
            st.toast("✅ Processing speech...", icon="🔄")
            return recognizer.recognize_google(audio, language=get_lang_code(language_choice))
        except sr.UnknownValueError:
            st.warning("❌ Could not understand audio.")
        except sr.WaitTimeoutError:
            st.warning("⏱️ Listening timed out.")
        except Exception as e:
            st.error(f"🎤 Mic error: {e}")
    return ""

# Language code mapping
def get_lang_code(lang_name):
    return {
        "English": "en",
        "Hindi": "hi",
        "Telugu": "te"
    }.get(lang_name, "en")

# Title
st.title("🤖 Multilingual Voice Assistant Chatbot")

# Display chat history
with st.container():
    for role, msg in st.session_state.chat_history:
        st.chat_message(role).write(msg)

# Columns for mic + input
col1, col2 = st.columns([0.1, 0.9])
with col1:
    if st.button("🎤", use_container_width=True):
        if not st.session_state.recording:
            st.session_state.recording = True
            transcript = listen_and_transcribe()
            if transcript:
                st.session_state.user_input = transcript
            st.session_state.recording = False
        else:
            st.session_state.recording = False
            st.toast("⛔ Stopped", icon="🛑")

input_value = "" if st.session_state.clear_input else st.session_state.user_input

# Input box
user_input = st.text_input("Type your question or use mic...", value=input_value, key="user_input")

# If user inputs something
if user_input.strip():
    if user_input.lower().strip() == "exit":
        st.success("Session ended. Goodbye! 👋")
        st.session_state.chat_history.clear()
        st.session_state.clear_input = True
    else:
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("🤖 Thinking..."):
                try:
                    payload = {
                        "model": model_choice,
                        "messages": [
                            {"role": "user", "content": user_input}
                        ],
                        "language": st.session_state.language
                    }
                    headers = {"Content-Type": "application/json"}
                    response = requests.post(BACKEND_URL, json=payload, headers=headers)

                    if response.status_code == 200:
                        result = response.json()
                        reply = result.get("answer", "Sorry, I didn't get that.")
                        st.session_state.chat_history.append(("assistant", reply))
                        st.write(reply)
                        speak(reply, get_lang_code(st.session_state.language))
                    else:
                        st.error(f"❌ Model Error {response.status_code}")
                except Exception as e:
                    st.error(f"⚠️ Request failed: {e}")
        st.session_state.clear_input = True

# Reset flag after input processed
if st.session_state.clear_input:
    st.session_state.clear_input = False

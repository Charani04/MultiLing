from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from langdetect import detect
from deep_translator import GoogleTranslator
import uvicorn

app = FastAPI()

class ChatRequest(BaseModel):
    model: str
    messages: list  # list of dicts [{"role": "user", "content": "..."}]
    language: str   # "english", "hindi", "telugu"

def translate(text, target_lang):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        return text  # fallback: return original if translation fails

@app.post("/chat")
def chat(request: ChatRequest):
    model = request.model
    messages = request.messages
    user_lang = request.language.lower()

    # Language mapping
    lang_map = {
        "english": "en",
        "hindi": "hi",
        "telugu": "te"
    }

    # Translate user message to English for model input
    original_msg = messages[-1]["content"]
    target_input_lang = lang_map.get(user_lang, "en")
    if target_input_lang != "en":
        messages[-1]["content"] = translate(original_msg, "en")

    # Prepare payload for local model
    payload = {
        "model": model,
        "messages": messages
    }
    try:
        response = requests.post("http://localhost:11434/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Translate reply back to original language if needed
        if target_input_lang != "en":
            reply = translate(reply, target_input_lang)

        return {"answer": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

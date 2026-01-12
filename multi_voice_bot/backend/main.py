import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from deep_translator import GoogleTranslator
from langdetect import detect  # ENHANCEMENT: For auto-detection fallback
import uvicorn
from fastapi.middleware.cors import CORSMiddleware  # ENHANCEMENT: CORS for production

app = FastAPI()

# ENHANCEMENT: Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    model: str
    messages: list  # ENHANCEMENT: Full chat history [{"role": "user/assistant", "content": "..."}]
    language: str  # "English", "Hindi", "Telugu"

def translate(text, target_lang):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception:
        return text  # Fallback

@app.post("/chat")
def chat(request: ChatRequest):
    model = request.model
    messages = request.messages
    user_lang = request.language.lower()
    lang_map = {"english": "en", "hindi": "hi", "telugu": "te"}
    target_lang = lang_map.get(user_lang, "en")

    # ENHANCEMENT: Translate ALL messages to English for LLM context
    translated_messages = []
    for msg in messages:
        content = msg["content"]
        # Auto-detect if needed (fallback)
        detected_lang = detect(content) if content else "en"
        if detected_lang != "en":
            content = translate(content, "en")
        translated_messages.append({"role": msg["role"], "content": content})

    payload = {"model": model, "messages": translated_messages}
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")  # ENHANCEMENT: Env var

    try:
        response = requests.post(ollama_url, json=payload)
        response.raise_for_status()
        data = response.json()
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        # Translate reply back if needed
        if target_lang != "en":
            reply = translate(reply, target_lang)
        return {"answer": reply}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

# import os
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import requests
# from deep_translator import GoogleTranslator
# from langdetect import detect
# import uvicorn
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import StreamingResponse

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# class ChatRequest(BaseModel):
#     model: str
#     messages: list
#     language: str

# def translate(text, target_lang):
#     try:
#         return GoogleTranslator(source='auto', target=target_lang).translate(text)
#     except Exception:
#         return text

# @app.post("/chat")
# def chat(request: ChatRequest):
#     model = request.model
#     messages = request.messages
#     user_lang = request.language.lower()
#     lang_map = {"english": "en", "hindi": "hi", "telugu": "te"}
#     target_lang = lang_map.get(user_lang, "en")

#     translated_messages = []
#     for msg in messages:
#         content = msg["content"]
#         detected_lang = detect(content) if content else "en"
#         if detected_lang != "en":
#             content = translate(content, "en")
#         translated_messages.append({"role": msg["role"], "content": content})

#     payload = {"model": model, "messages": translated_messages}
#     ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")

#     try:
#         response = requests.post(ollama_url, json=payload, stream=True)
#         response.raise_for_status()

#         def generate():
#             reply = ""
#             for chunk in response.iter_content(chunk_size=512):
#                 if chunk:
#                     chunk_str = chunk.decode('utf-8')
#                     reply += chunk_str
#                     yield chunk_str
#             if target_lang != "en":
#                 translated_reply = translate(reply, target_lang)
#                 yield translated_reply

#         return StreamingResponse(generate(), media_type="text/event-stream")
#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail=f"Ollama error: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
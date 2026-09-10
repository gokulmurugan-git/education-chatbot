import os
import uuid
from datetime import datetime, timezone

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIREBASE_KEY_FILE = os.getenv("FIREBASE_KEY_FILE", "firebase_key.json")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY is not configured.")

db = None
try:
    if not firebase_admin._apps and os.path.exists(FIREBASE_KEY_FILE):
        cred = credentials.Certificate(FIREBASE_KEY_FILE)
        firebase_admin.initialize_app(cred)
        print("Firebase connected successfully.")
    elif not os.path.exists(FIREBASE_KEY_FILE):
        print(f"WARNING: Firebase key file not found: {FIREBASE_KEY_FILE}")
    if firebase_admin._apps:
        db = firestore.client()
except Exception as e:
    print("Firebase connection error:", e)

MODEL_NAME = "gemini-2.0-flash"

SYSTEM_PROMPT = """
You are EduBot AI, an intelligent educational assistant.
Help students with programming, AI, ML, DL, Data Science, Computer Science,
mathematics, engineering subjects, exams, assignments, projects, viva and
interview preparation.

Explain concepts simply and accurately. Give examples when useful.
For programming questions provide clean runnable code and explain it.
For 2-mark questions keep answers concise. For 13/15/16-mark questions,
provide structured detailed answers. If unsure, clearly say so.
Never expose API keys or secret credentials.
"""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "gemini": bool(GEMINI_API_KEY),
        "firebase": db is not None
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        message = str(data.get("message", "")).strip()
        session_id = str(data.get("session_id", "")).strip()
        history = data.get("history", [])

        if not message:
            return jsonify({"success": False, "error": "Please enter a message."}), 400

        if not GEMINI_API_KEY:
            return jsonify({
                "success": False,
                "error": "GEMINI_API_KEY is not configured. Add it to .env."
            }), 500

        if not session_id:
            session_id = str(uuid.uuid4())

        conversation = SYSTEM_PROMPT + "\n\n"
        for item in history[-12:]:
            role = item.get("role", "")
            text = item.get("text", "")
            if not text:
                continue
            if role == "user":
                conversation += f"Student: {text}\n"
            elif role == "assistant":
                conversation += f"EduBot AI: {text}\n"

        conversation += f"Student: {message}\nEduBot AI:"

        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(conversation)
        answer = response.text.strip() if response and response.text else \
            "Sorry, I could not generate a response. Please try again."

        if db is not None:
            try:
                db.collection("edubot_chats").add({
                    "session_id": session_id,
                    "user_message": message,
                    "assistant_message": answer,
                    "created_at": datetime.now(timezone.utc)
                })
            except Exception as firebase_error:
                print("Firebase save error:", firebase_error)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "answer": answer
        })
    except Exception as e:
        print("Chat error:", e)
        return jsonify({
            "success": False,
            "error": "Something went wrong while contacting EduBot AI."
        }), 500

@app.route("/api/save-session", methods=["POST"])
def save_session():
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        messages = data.get("messages", [])

        if not session_id:
            return jsonify({"success": False, "error": "Session ID is required."}), 400

        if db is not None:
            db.collection("edubot_sessions").document(session_id).set({
                "session_id": session_id,
                "messages": messages,
                "updated_at": datetime.now(timezone.utc)
            }, merge=True)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete-session", methods=["POST"])
def delete_session():
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        if db is not None and session_id:
            db.collection("edubot_sessions").document(session_id).delete()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("           EduBot AI Chatbot")
    print("=" * 55)
    print("Gemini API:", "Configured" if GEMINI_API_KEY else "Not Configured")
    print("Firebase:", "Connected" if db else "Not Connected")
    print("=" * 55 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=True)

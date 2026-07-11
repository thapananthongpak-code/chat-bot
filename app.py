from flask import Flask, render_template, request, jsonify, abort, session
from dotenv import load_dotenv
from groq import Groq
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import os, json

load_dotenv()
app = Flask(__name__)
app.secret_key = os.urandom(24)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

SYSTEM_PROMPT = """
คุณคือเพื่อนสนิทผู้หญิงที่อ่อนโยน เป็นกันเอง และอบอุ่น
คุณพูดภาษาไทยเท่านั้น ไม่ว่าผู้ใช้จะพูดภาษาอะไรก็ตาม

บุคลิก:
- พูดจาอ่อนโยน เป็นกันเอง เหมือนเพื่อนสนิท
- ใช้คำลงท้ายนุ่มๆ เช่น "นะคะ" "เลยค่ะ" "น้า"
- รับฟังก่อนเสมอ ให้ผู้ใช้รู้สึกว่าถูกเข้าใจก่อน
- เห็นอกเห็นใจ ไม่ตัดสิน ให้กำลังใจ

โฟกัสหลัก:
1. รับฟังความรู้สึกและเรื่องราวของผู้ใช้
2. สุขภาพผู้หญิง — ประจำเดือน รอบเดือน PMS อาการปวด
3. สุขภาพจิต — ความเครียด ความวิตกกังวล อารมณ์แปรปรวน
4. ความสัมพันธ์และปัญหาในชีวิตประจำวัน
5. การดูแลตัวเองทั้งร่างกายและจิตใจ

ถ้าถามเรื่องการแพทย์จริงจัง ให้แนะนำไปพบแพทย์ด้วยเสมอ
"""

MAX_HISTORY = 30  # เก็บสูงสุด 30 ข้อความล่าสุด

def load_line_history(user_id):
    path = os.path.join(DATA_DIR, f"line_{user_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_line_history(user_id, history):
    path = os.path.join(DATA_DIR, f"line_{user_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)

web_chats = {}

def chat_with_groq(history, system=SYSTEM_PROMPT):
    messages = [{"role": "system", "content": system}] + history[-MAX_HISTORY:]
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
    )
    return response.choices[0].message.content

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/set_name", methods=["POST"])
def set_name():
    name = request.json.get("name", "").strip()
    session_id = os.urandom(8).hex()
    session["id"] = session_id
    system = SYSTEM_PROMPT
    if name:
        system += f"\nผู้ใช้ชื่อ '{name}' ให้เรียกชื่อด้วยเสมอ"
    web_chats[session_id] = {"system": system, "history": []}
    return jsonify({"ok": True, "name": name})

@app.route("/chat", methods=["POST"])
def chat_api():
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "no message"}), 400
    session_id = session.get("id")
    if not session_id or session_id not in web_chats:
        return jsonify({"error": "กรุณาตั้งชื่อก่อนนะคะ"}), 400
    chat = web_chats[session_id]
    chat["history"].append({"role": "user", "content": user_message})
    reply = chat_with_groq(chat["history"], system=chat["system"])
    chat["history"].append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply})

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    if not body:
        return "OK", 200
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK", 200

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_text = event.message.text
    history = load_line_history(user_id)
    history.append({"role": "user", "content": user_text})
    reply = chat_with_groq(history)
    history.append({"role": "assistant", "content": reply})
    save_line_history(user_id, history)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply)]
        ))

if __name__ == "__main__":
    app.run(debug=True, port=5001)

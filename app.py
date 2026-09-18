from flask import Flask, render_template, request, jsonify, abort, Response, stream_with_context, send_file
from dotenv import load_dotenv
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import os, json, re
from datetime import datetime, timezone

import knowledge_base as kb

load_dotenv()
app = Flask(__name__)

# Dataset-only mode: no generative client, prompt, or environment override.
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET") or "disabled-local-web-only")

# บน Vercel ระบบไฟล์เป็น read-only ยกเว้น /tmp การเขียนที่อื่นจะทำให้แอปพังตั้งแต่ import
ON_SERVERLESS = bool(os.getenv("VERCEL"))
DATA_DIR = os.getenv("DATA_DIR") or (
    "/tmp/ch-bot-data" if ON_SERVERLESS else os.path.join(os.path.dirname(__file__), "data")
)
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError as exc:
    print(f"[!] สร้างโฟลเดอร์เก็บประวัติไม่ได้ ({exc}) — บอทจะทำงานต่อได้แต่ไม่จำบทสนทนา LINE")

MAX_HISTORY = 30  # เก็บสูงสุด 30 ข้อความล่าสุด

CHAT_ID_RE = re.compile(r"^[0-9a-f]{8,32}$")


def chat_path(chat_id):
    """สร้าง path ของไฟล์ประวัติ — ตรวจรูปแบบ id ก่อนเสมอ กัน path traversal
    (เช่น chat_id = '../../etc/passwd' จะเขียนทับไฟล์นอกโฟลเดอร์ได้)"""
    if not chat_id or not CHAT_ID_RE.match(chat_id):
        return None
    return os.path.join(DATA_DIR, f"web_{chat_id}.json")


def load_web_chat(chat_id):
    path = chat_path(chat_id)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def save_web_chat(chat_id, name, history):
    path = chat_path(chat_id)
    if not path:
        return False
    title = next((m["content"] for m in history if m["role"] == "user"), "แชทใหม่")
    payload = {
        "id": chat_id,
        "name": name,
        "title": title[:60],
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "history": history[-MAX_HISTORY:],
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except OSError as exc:
        print(f"[!] บันทึกประวัติแชทเว็บไม่ได้: {exc}")
        return False


def load_line_history(user_id):
    path = os.path.join(DATA_DIR, f"line_{user_id}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        # ไม่มีไฟล์ อ่านไม่ได้ หรือไฟล์เสีย — เริ่มบทสนทนาใหม่ ดีกว่าปล่อยให้ 500
        return []

def save_line_history(user_id, history):
    path = os.path.join(DATA_DIR, f"line_{user_id}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[!] บันทึกประวัติ LINE ไม่ได้: {exc}")

def clean_history(raw):
    """กรองประวัติที่รับมาจากเบราว์เซอร์ ให้เหลือเฉพาะรูปแบบที่ API ยอมรับ"""
    if not isinstance(raw, list):
        return []
    return [
        {"role": m.get("role"), "content": str(m.get("content") or "")[:8000]}
        for m in (raw or [])[-MAX_HISTORY:]
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
    ]


def stream_reply(history, system=None):
    """Extract stored content without a generative model."""
    yield kb.answer_from_dataset(history)


def chat_with_ai(history, system=None):
    return kb.answer_from_dataset(history)


@app.route("/")
def index():
    return render_template("index.html", handbook_pages=kb.DOCUMENT_META.get("expected_pages", "—"))

@app.get("/handbook.pdf")
def handbook_pdf():
    return send_file(os.path.join(app.root_path, "output/pdf/sql_database_handbook_th.pdf"), mimetype="application/pdf")

@app.get("/handbook.md")
def handbook_markdown():
    return send_file(os.path.join(kb.KNOWLEDGE_DIR, "sql_handbook_th.md"), as_attachment=True)

@app.get("/knowledge/topics")
def knowledge_topics():
    return jsonify([entry["topic"] for entry in kb.ENTRIES])

@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    """ส่งคำตอบแบบทยอยทีละส่วน ให้ผู้ใช้เห็นตัวอักษรไหลออกมาทันที
    ใช้ text/plain แบบ chunked ไม่ต้องพึ่ง SSE ให้ยุ่งยาก"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or not isinstance(payload.get("message"), str):
        return jsonify({"error": "ข้อความต้องเป็นข้อความตัวอักษร"}), 400
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "ยังไม่ได้พิมพ์คำถามครับ"}), 400

    chat_id = (payload.get("chat_id") or "").strip()
    saved = None
    name = (payload.get("name") or "").strip()[:30] or (saved.get("name") if saved else "")
    history = clean_history(payload.get("history"))
    history = history + [{"role": "user", "content": user_message}]

    def generate():
        collected = []
        for piece in stream_reply(history):
            collected.append(piece)
            yield piece
        reply = "".join(collected)
        if reply:
            save_web_chat(chat_id, name, history + [{"role": "assistant", "content": reply}])

    return Response(stream_with_context(generate()),
                    mimetype="text/plain; charset=utf-8",
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@app.route("/chats/<chat_id>", methods=["DELETE"])
def chat_delete(chat_id):
    path = chat_path(chat_id)
    if not path:
        return jsonify({"error": "รหัสแชทไม่ถูกต้อง"}), 400
    try:
        os.remove(path)
    except OSError:
        pass  # ไม่มีไฟล์อยู่แล้วก็ถือว่าลบสำเร็จ
    return jsonify({"ok": True})


def to_line_text(text):
    """LINE ไม่เรนเดอร์ Markdown จึงถอดบล็อกโค้ด/ตัวหนาออกก่อนส่ง"""
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"^\s*\|[\s|:-]+\|\s*$", "", text, flags=re.M)  # เส้นคั่นตาราง |---|---|
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)               # หัวข้อ ## ###
    text = re.sub(r"^\s*[-*]{3,}\s*$", "", text, flags=re.M)         # เส้นคั่น ---
    text = text.replace("`", "").replace("**", "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:4900]  # ข้อความเดียวของ LINE ยาวได้ไม่เกิน 5000 ตัวอักษร


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
    reply = chat_with_ai(history)
    history.append({"role": "assistant", "content": reply})
    save_line_history(user_id, history)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=to_line_text(reply))]
        ))

if __name__ == "__main__":
    app.run(debug=True, port=5001)

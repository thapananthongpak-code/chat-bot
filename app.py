from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import os, json, re, hashlib
from datetime import datetime, timezone

import knowledge_base as kb

app = Flask(__name__)

# บน Vercel ระบบไฟล์เป็น read-only ยกเว้น /tmp การเขียนที่อื่นจะทำให้แอปพังตั้งแต่ import
ON_SERVERLESS = bool(os.getenv("VERCEL"))
DATA_DIR = os.getenv("DATA_DIR") or (
    "/tmp/ch-bot-data" if ON_SERVERLESS else os.path.join(os.path.dirname(__file__), "data")
)
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError as exc:
    print(f"[!] สร้างโฟลเดอร์เก็บประวัติไม่ได้ ({exc}) — บอทจะทำงานต่อได้แต่ไม่เก็บสำเนาแชตฝั่งเซิร์ฟเวอร์")

MAX_HISTORY = 30  # เก็บสูงสุด 30 ข้อความล่าสุด

CHAT_ID_RE = re.compile(r"^[0-9a-f]{8,32}$")


def chat_path(chat_id):
    """สร้าง path ของไฟล์ประวัติ — ตรวจรูปแบบ id ก่อนเสมอ กัน path traversal
    (เช่น chat_id = '../../etc/passwd' จะเขียนทับไฟล์นอกโฟลเดอร์ได้)"""
    if not chat_id or not CHAT_ID_RE.match(chat_id):
        return None
    return os.path.join(DATA_DIR, f"web_{chat_id}.json")


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


def clean_history(raw):
    """กรองประวัติที่รับมาจากเบราว์เซอร์ ให้เหลือเฉพาะรูปแบบที่ API ยอมรับ"""
    if not isinstance(raw, list):
        return []
    return [
        {"role": m.get("role"), "content": str(m.get("content") or "")[:8000]}
        for m in (raw or [])[-MAX_HISTORY:]
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
    ]


def stream_reply(history):
    """Extract stored content without a generative model."""
    yield kb.answer_from_dataset(history)


def page_version():
    """เวอร์ชันหน้าเว็บ = hash ของเนื้อหา templates/index.html (ไม่ใช้เวลาไฟล์ เพราะตอน deploy อาจถูกตั้งใหม่)
    แท็บที่เปิดค้างไว้ก่อนอัปเดตจะรู้ตัวว่าเก่า (เช่นเก่ากว่าฟีเจอร์รูป) แล้วขึ้นให้รีเฟรช"""
    try:
        with open(os.path.join(app.root_path, "templates", "index.html"), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:12]
    except OSError:
        return ""


@app.route("/")
def index():
    response = app.make_response(render_template("index.html", page_version=page_version()))
    response.headers["Cache-Control"] = "no-cache"   # รีเฟรชแล้วได้หน้าล่าสุดเสมอ
    return response

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

    chat_id = str(payload.get("chat_id") or "").strip()
    name = str(payload.get("name") or "").strip()[:30]
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
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache",
                             "X-Page-Version": page_version()})


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


if __name__ == "__main__":
    app.run(debug=True, port=5001)

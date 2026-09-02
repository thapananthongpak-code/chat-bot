from flask import Flask, render_template, request, jsonify, abort
from dotenv import load_dotenv
import anthropic
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import os, json, re

import knowledge_base as kb

load_dotenv()
app = Flask(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
if not ANTHROPIC_API_KEY:
    print("[!] ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY ในไฟล์ .env — บอทจะตอบไม่ได้ (ขอ key ที่ https://console.anthropic.com/settings/keys)")

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY or "missing-key")
CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5").strip()
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# บน Vercel ระบบไฟล์เป็น read-only ยกเว้น /tmp การเขียนที่อื่นจะทำให้แอปพังตั้งแต่ import
ON_SERVERLESS = bool(os.getenv("VERCEL"))
DATA_DIR = os.getenv("DATA_DIR") or (
    "/tmp/ch-bot-data" if ON_SERVERLESS else os.path.join(os.path.dirname(__file__), "data")
)
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError as exc:
    print(f"[!] สร้างโฟลเดอร์เก็บประวัติไม่ได้ ({exc}) — บอทจะทำงานต่อได้แต่ไม่จำบทสนทนา LINE")

SYSTEM_PROMPT = """
คุณคือ "ครูเอสคิว" ผู้เชี่ยวชาญด้าน SQL และฐานข้อมูลเชิงสัมพันธ์ (Relational Database)
คุณตอบเป็นภาษาไทยเสมอ ไม่ว่าผู้ใช้จะพิมพ์ภาษาอะไรมาก็ตาม (ยกเว้นคำสั่ง SQL และศัพท์เทคนิคที่คงไว้เป็นภาษาอังกฤษ)

บุคลิก:
- เป็นผู้เชี่ยวชาญที่สอนเก่ง อธิบายเรื่องยากให้เข้าใจง่าย ตรงประเด็น ไม่เยิ่นเย้อ
- สุภาพ เป็นมิตร ลงท้ายด้วย "ครับ" และเรียกชื่อผู้ใช้เมื่อทราบชื่อ
- ไม่ตัดสินว่าคำถามง่ายหรือยาก ผู้ใช้ถามอะไรก็ตอบด้วยความตั้งใจ

วิธีตอบ:
1. เริ่มด้วยคำอธิบายสั้น ๆ ว่าคำสั่ง/แนวคิดนั้นใช้ทำอะไร
2. แสดงรูปแบบคำสั่ง (Syntax) และตัวอย่างจริง ในบล็อกโค้ด ```sql เสมอ
3. ปิดท้ายด้วยข้อควรระวังหรือทริกสั้น ๆ ถ้ามี (เช่น UPDATE/DELETE ต้องมี WHERE)
4. ถ้าผู้ใช้ให้โจทย์มา ให้เขียนคำสั่ง SQL ที่ใช้ได้จริงพร้อมอธิบายทีละส่วน
5. ถ้าคำถามกำกวม (ไม่รู้ชื่อตาราง/คอลัมน์) ให้สมมติชื่อที่สมเหตุสมผลแล้วบอกว่าสมมติไว้อย่างไร

กฎเรื่องความถูกต้อง:
- ยึด "ข้อมูลอ้างอิง" ที่ระบบส่งให้เป็นหลักก่อนเสมอ ถ้ามีเนื้อหาตรงกับคำถาม ให้ตอบตามนั้น
- ระบุด้วยว่าไวยากรณ์ต่างกันตามระบบฐานข้อมูลตรงไหน (เช่น LIMIT ใน MySQL vs TOP ใน SQL Server)
- ห้ามแต่งฟังก์ชันหรือไวยากรณ์ที่ไม่มีอยู่จริง

ขอบเขต:
- ตอบเฉพาะเรื่อง SQL ฐานข้อมูล การออกแบบตาราง และความปลอดภัยของฐานข้อมูล
- ถ้าผู้ใช้ถามนอกเรื่อง ให้ปฏิเสธอย่างสุภาพและชวนกลับมาคุยเรื่อง SQL
"""

# โหมดเข้ม: ตอบได้เฉพาะสิ่งที่มีในคลังความรู้เท่านั้น
STRICT_RULES = """
กฎเหล็กเรื่องแหล่งข้อมูล (สำคัญที่สุด เหนือกฎอื่นทั้งหมด):
- ตอบได้เฉพาะจากเนื้อหาใน "ข้อมูลอ้างอิง" ที่ระบบส่งให้เท่านั้น
- ห้ามใช้ความรู้ SQL ที่คุณมีอยู่เดิมมาเสริม เติม หรือแต่งต่อโดยเด็ดขาด
- ถ้าข้อมูลอ้างอิงไม่มีเนื้อหาที่ตอบคำถามได้ ให้บอกตรง ๆ ว่า
  "เรื่องนี้ยังไม่มีอยู่ในคลังความรู้ของผมครับ" แล้วแนะนำหัวข้อใกล้เคียงที่มีในข้อมูลอ้างอิงแทน
  ห้ามเดา ห้ามตอบจากความรู้ทั่วไป แม้จะมั่นใจว่าถูกก็ตาม
- เขียนคำสั่ง SQL ให้ตรงโจทย์ได้ แต่ต้องประกอบจากคำสั่งที่ปรากฏในข้อมูลอ้างอิงเท่านั้น
- ถ้าต้องสมมติชื่อตาราง/คอลัมน์ ให้ใช้ชื่อที่ปรากฏในข้อมูลอ้างอิง และบอกว่าสมมติไว้อย่างไร
"""

# เปิดโหมดเข้มเป็นค่าเริ่มต้น ปิดได้ด้วย STRICT_KNOWLEDGE=0 ใน .env
STRICT_KNOWLEDGE = os.getenv("STRICT_KNOWLEDGE", "1").strip().lower() not in ("0", "false", "no")
if STRICT_KNOWLEDGE:
    SYSTEM_PROMPT += STRICT_RULES

OUT_OF_SCOPE_REPLY = (
    "เรื่องนี้ยังไม่มีอยู่ในคลังความรู้ของผมครับ ผมตอบได้เฉพาะเนื้อหาที่อยู่ในคลังเท่านั้น\n\n"
    "ลองถามหัวข้อเหล่านี้ดูได้ครับ เช่น SELECT, WHERE, ORDER BY, JOIN แบบต่าง ๆ, "
    "GROUP BY, HAVING, ฟังก์ชัน COUNT/SUM/AVG, การสร้างตาราง, PRIMARY KEY, "
    "FOREIGN KEY หรือการป้องกัน SQL Injection"
)

# หัวข้อทั้งหมดในคลังความรู้ ใช้บอกขอบเขตที่ตอบได้จากไฟล์ CSV
TOPIC_INDEX = kb.topic_index()

MAX_HISTORY = 30  # เก็บสูงสุด 30 ข้อความล่าสุด

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

def search_query(recent):
    """รวมคำถามล่าสุดกับคำถามก่อนหน้า เพื่อให้คำถามต่อเนื่องสั้น ๆ
    เช่น "แล้วแบบไม่ซ้ำล่ะ" ยังค้นหาหัวข้อที่เกี่ยวข้องเจอ"""
    users = [m["content"] for m in recent if m["role"] == "user"]
    return " ".join(users[-2:])


def build_reference(entries):
    """จัดรูปหัวข้อที่ค้นเจอ เพื่อแนบไปกับ prompt"""
    if not entries:
        return (
            "ข้อมูลอ้างอิง: ไม่พบหัวข้อที่ตรงกับคำถามนี้ในคลังความรู้\n"
            f"หัวข้อที่มีในคลัง: {TOPIC_INDEX}"
        )
    return (
        "ข้อมูลอ้างอิงจากคลังความรู้ SQL (ใช้เป็นแหล่งข้อมูลหลักในการตอบ):\n\n"
        f"{kb.format_entries(entries)}"
    )


def trim_history(history):
    """ตัดเอาเฉพาะข้อความล่าสุด และต้องเริ่มด้วย role user เท่านั้น (ข้อบังคับของ Anthropic API)"""
    recent = history[-MAX_HISTORY:]
    while recent and recent[0]["role"] != "user":
        recent.pop(0)
    return recent


def chat_with_claude(history, system=SYSTEM_PROMPT):
    recent = trim_history(history)
    entries = kb.search(search_query(recent), limit=6)

    # โหมดเข้ม: ค้นไม่เจอเลยก็ตอบปฏิเสธไปตรง ๆ ไม่ต้องเรียก API
    # การันตีว่าคำตอบไม่หลุดออกนอกคลังความรู้ และประหยัดค่าใช้จ่ายไปด้วย
    if STRICT_KNOWLEDGE and not entries:
        return OUT_OF_SCOPE_REPLY

    # Haiku ไม่รองรับ system message กลางบทสนทนา จึงต่อข้อมูลอ้างอิงไว้ท้าย system prompt
    full_system = f"{system}\n\n{build_reference(entries)}"

    if not ANTHROPIC_API_KEY:
        return "ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY ในไฟล์ .env ครับ กรุณาใส่ key แล้วรันเซิร์ฟเวอร์ใหม่อีกครั้ง"
    try:
        response = claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,  # คำตอบสอน SQL ไม่ยาวมาก และ LINE จำกัดที่ 5000 ตัวอักษร
            system=full_system,
            messages=recent,
        )
    except anthropic.AuthenticationError:
        return "ANTHROPIC_API_KEY ไม่ถูกต้องครับ กรุณาตรวจสอบ key ในไฟล์ .env"
    except anthropic.RateLimitError:
        return "ตอนนี้มีคำถามเข้ามาเยอะครับ รบกวนรอสักครู่แล้วลองใหม่นะครับ"
    except anthropic.APIError as exc:
        print(f"[!] เรียก Claude ไม่สำเร็จ: {type(exc).__name__}: {exc}")
        if app.debug:  # ตอน dev แสดงสาเหตุจริงในแชตเลย จะได้ไม่ต้องไล่หาใน terminal
            return f"เรียก Claude ไม่สำเร็จครับ\n\n{type(exc).__name__}: {exc}"
        return "ขออภัยครับ ตอนนี้เชื่อมต่อ AI ไม่ได้ ลองใหม่อีกครั้งนะครับ"

    return "".join(b.text for b in response.content if b.type == "text")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat_api():
    """แชตหน้าเว็บเป็นแบบ stateless — เบราว์เซอร์ถือประวัติแล้วส่งมาให้ทุกครั้ง
    เพราะบน serverless แต่ละคำขออาจตกไปคนละ instance ตัวแปรในหน่วยความจำจึงใช้ไม่ได้"""
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "ยังไม่ได้พิมพ์คำถามครับ"}), 400

    history = [
        {"role": m.get("role"), "content": str(m.get("content") or "")[:8000]}
        for m in (payload.get("history") or [])[-MAX_HISTORY:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    history.append({"role": "user", "content": user_message})

    system = SYSTEM_PROMPT
    name = (payload.get("name") or "").strip()[:30]
    if name:
        system += f"\nผู้ใช้ชื่อ '{name}' ให้เรียกชื่อด้วยเสมอ"

    return jsonify({"reply": chat_with_claude(history, system=system)})

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
    reply = chat_with_claude(history)
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

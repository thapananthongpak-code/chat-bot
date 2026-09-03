from flask import Flask, render_template, request, jsonify, abort
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors as genai_errors
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import os, json, re
from datetime import datetime, timezone

import knowledge_base as kb

load_dotenv()
app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

if not GEMINI_API_KEY:
    print("[!] ยังไม่ได้ตั้งค่า GEMINI_API_KEY ในไฟล์ .env — บอทจะตอบไม่ได้ "
          "(ขอ key ฟรีที่ https://aistudio.google.com/apikey)")

# สร้าง client ครั้งเดียวตอนเริ่ม ถ้าสร้างใหม่ทุกคำขอจะโดนปิดตัวเองระหว่างทาง
gemini = genai.Client(api_key=GEMINI_API_KEY or "missing-key")
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
- สุภาพ เป็นมิตร ลงท้ายด้วย "ครับ" ทุกครั้ง ห้ามใช้ "ค่ะ" หรือ "คะ" เด็ดขาด
  และเรียกชื่อผู้ใช้เมื่อทราบชื่อ
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

กฎการยกตัวอย่างและการขยายความ (ห้ามละเมิด):
- ยกได้เฉพาะตัวอย่างที่ปรากฏในช่อง "ตัวอย่าง" หรือ "รูปแบบคำสั่ง" ของข้อมูลอ้างอิงเท่านั้น
- ห้ามคิดตัวอย่างเพิ่มเองเด็ดขาด แม้จะถูกต้องตามหลัก SQL ก็ตาม
- ถ้าช่องใดเขียนว่าไม่มีข้อมูลในคลังความรู้ ให้ข้ามส่วนนั้นไปเลย ห้ามเติมให้
  เช่น ถ้าไม่มีตัวอย่าง ก็ไม่ต้องมีหัวข้อ "ตัวอย่าง" ในคำตอบ
- ห้ามเพิ่มหัวข้อ "ข้อควรระวัง" "ทริก" หรือคำอธิบายผลลัพธ์ ถ้าเนื้อหานั้นไม่ได้อยู่ในข้อมูลอ้างอิง
- เรียบเรียงถ้อยคำให้อ่านง่ายได้ แต่ห้ามเพิ่มข้อเท็จจริงใหม่ที่ไม่มีในข้อมูลอ้างอิง
- ตอบสั้นกระชับตามปริมาณข้อมูลที่มีจริง ไม่ต้องพยายามเขียนให้ยาว

กฎเหล็กข้อสุดท้าย — ความยาวคำตอบต้องสมดุลกับข้อมูลที่มี:
- ถ้าข้อมูลอ้างอิงเรื่องนั้นมีแค่ 1-2 ประโยค คำตอบก็ต้องสั้นประมาณนั้น
  ห้ามขยายเป็นหลายย่อหน้าเด็ดขาด
- ห้ามแตกเป็นรายการ bullet หรือหัวข้อย่อย ถ้าข้อมูลอ้างอิงไม่ได้แจกแจงไว้แบบนั้น
  เช่น ถ้าไฟล์เขียนว่า "ใช้จัดการฐานข้อมูล" ห้ามแตกเป็น ดึง/เพิ่ม/แก้ไข/ลบ เอง
- ห้ามใช้อุปมาอุปไมยหรือคำเปรียบเทียบที่ไม่มีในข้อมูลอ้างอิง
  (เช่น "เหมือนภาษาที่ใช้สนทนากับฐานข้อมูล")
- ห้ามสรุปหรืออนุมานต่อจากข้อมูลอ้างอิง ให้ยึดตามที่เขียนไว้เท่านั้น
  เช่น ถ้าไฟล์บอกว่า MySQL เป็นตัวอย่างของ RDBMS ห้ามสรุปเองว่า "SQL ใช้ได้กับทุกตัว"
- ห้ามใส่อีโมจิ
- ก่อนตอบทุกครั้ง ให้ตรวจทุกประโยคว่าหาที่มาในข้อมูลอ้างอิงได้จริง
  ประโยคไหนหาไม่เจอ ให้ตัดทิ้ง
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


def list_web_chats():
    """รายการแชทที่บันทึกไว้ เรียงจากคุยล่าสุดก่อน"""
    items = []
    try:
        names = os.listdir(DATA_DIR)
    except OSError:
        return items
    for filename in names:
        if not (filename.startswith("web_") and filename.endswith(".json")):
            continue
        data = load_web_chat(filename[4:-5])
        if data:
            items.append({
                "id": data.get("id"),
                "title": data.get("title") or "แชทใหม่",
                "updated": data.get("updated") or "",
                "count": len(data.get("history") or []),
            })
    items.sort(key=lambda c: c["updated"], reverse=True)
    return items


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
    return [
        {"role": m.get("role"), "content": str(m.get("content") or "")[:8000]}
        for m in (raw or [])[-MAX_HISTORY:]
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and m.get("content")
    ]


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
    """ตัดเอาเฉพาะข้อความล่าสุด และต้องเริ่มด้วย role user เท่านั้น (ข้อบังคับของ Gemini API)"""
    recent = history[-MAX_HISTORY:]
    while recent and recent[0]["role"] != "user":
        recent.pop(0)
    return recent


def chat_with_ai(history, system=SYSTEM_PROMPT):
    recent = trim_history(history)
    entries = kb.search(search_query(recent), limit=6)

    # โหมดเข้ม: ค้นไม่เจอเลยก็ตอบปฏิเสธไปตรง ๆ ไม่ต้องเรียก API
    # การันตีว่าคำตอบไม่หลุดออกนอกคลังความรู้ และประหยัดโควตาไปด้วย
    if STRICT_KNOWLEDGE and not entries:
        return OUT_OF_SCOPE_REPLY

    if not GEMINI_API_KEY:
        return "ยังไม่ได้ตั้งค่า GEMINI_API_KEY ในไฟล์ .env ครับ กรุณาใส่ key แล้วรันเซิร์ฟเวอร์ใหม่อีกครั้ง"

    # Gemini ไม่รองรับ system message กลางบทสนทนา จึงต่อข้อมูลอ้างอิงไว้ท้าย system prompt
    full_system = f"{system}\n\n{build_reference(entries)}"
    # Gemini เรียกฝั่งผู้ช่วยว่า "model" ไม่ใช่ "assistant"
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in recent
    ]

    try:
        response = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=full_system,
                max_output_tokens=2048,  # คำตอบสอน SQL ไม่ยาวมาก และ LINE จำกัดที่ 5000 ตัวอักษร
                temperature=0.3,  # ต่ำไว้ เพราะต้องเรียบเรียงตามไฟล์ ไม่ใช่คิดเอง
                # ไม่ได้ใช้ tool ปิดไว้กัน warning รก log
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
    except genai_errors.ClientError as exc:
        print(f"[!] เรียก Gemini ไม่สำเร็จ: {exc}")
        detail, code = str(exc), getattr(exc, "code", None)
        if code == 429:
            return "โควตาฟรีของ Gemini เต็มชั่วคราวครับ รบกวนรอสักครู่แล้วลองใหม่นะครับ"
        if "API_KEY_INVALID" in detail or "API key not valid" in detail:
            return "GEMINI_API_KEY ไม่ถูกต้องครับ กรุณาตรวจสอบ key ในไฟล์ .env"
        if code == 404:
            return (f"ไม่พบโมเดล '{GEMINI_MODEL}' ครับ อาจถูกเปลี่ยนชื่อหรือ key ยังเข้าไม่ถึง\n"
                    "ลองเปลี่ยนค่า GEMINI_MODEL ใน .env เป็นรุ่นอื่น เช่น gemini-3.5-flash-lite")
        return _fail_message(exc)
    except Exception as exc:
        print(f"[!] เรียก Gemini ไม่สำเร็จ: {type(exc).__name__}: {exc}")
        return _fail_message(exc)

    text = (response.text or "").strip()
    if text:
        return text
    # Gemini คืนข้อความว่างได้เมื่อโดนตัวกรองความปลอดภัยหรือชนเพดาน token
    print(f"[!] Gemini คืนข้อความว่าง: {getattr(response, 'prompt_feedback', None)}")
    return "ขออภัยครับ ผมตอบคำถามนี้ไม่ได้ ลองถามใหม่อีกแบบได้ไหมครับ"


def _fail_message(exc):
    if app.debug:  # ตอน dev แสดงสาเหตุจริงในแชตเลย จะได้ไม่ต้องไล่หาใน terminal
        return f"เรียก AI ไม่สำเร็จครับ\n\n{type(exc).__name__}: {exc}"
    return "ขออภัยครับ ตอนนี้เชื่อมต่อ AI ไม่ได้ ลองใหม่อีกครั้งนะครับ"


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat_api():
    """เก็บประวัติเป็นไฟล์ JSON ใน data/ ถ้าส่ง chat_id มา
    ถ้าเขียนไฟล์ไม่ได้ (เช่นบน Vercel) จะถอยไปใช้ประวัติที่เบราว์เซอร์ส่งมาแทน"""
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "ยังไม่ได้พิมพ์คำถามครับ"}), 400

    chat_id = (payload.get("chat_id") or "").strip()
    name = (payload.get("name") or "").strip()[:30]

    saved = load_web_chat(chat_id)
    if saved:
        history = saved.get("history") or []
        name = name or saved.get("name") or ""
    else:
        history = clean_history(payload.get("history"))

    history = history + [{"role": "user", "content": user_message}]

    system = SYSTEM_PROMPT
    if name:
        system += f"\nผู้ใช้ชื่อ '{name}' ให้เรียกชื่อด้วยเสมอ"

    reply = chat_with_ai(history, system=system)
    history.append({"role": "assistant", "content": reply})
    stored = save_web_chat(chat_id, name, history)

    return jsonify({"reply": reply, "chat_id": chat_id, "stored": stored})


@app.route("/chats", methods=["GET"])
def chats_list():
    return jsonify({"chats": list_web_chats()})


@app.route("/chats/<chat_id>", methods=["GET"])
def chat_get(chat_id):
    data = load_web_chat(chat_id)
    if not data:
        return jsonify({"error": "ไม่พบแชทนี้"}), 404
    return jsonify(data)


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

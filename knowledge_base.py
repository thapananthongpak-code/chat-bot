"""โหลดชุดข้อมูลความรู้ SQL จากไฟล์ CSV แล้วค้นหาหัวข้อที่เกี่ยวข้องกับคำถามผู้ใช้"""

import csv
import os
import re

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

# คอลัมน์ในไฟล์ CSV: หัวข้อ (Topic), คำอธิบาย (Description), คำสั่ง SQL (Syntax), ตัวอย่าง (Example)
_EMPTY = {"", "-", "–", "—"}

# คำภาษาอังกฤษที่พบบ่อยจนไม่ช่วยแยกแยะหัวข้อ
_STOPWORDS = {"sql", "table", "column", "name", "value", "data", "the", "how", "what", "is", "in", "of", "to"}

# วลีภาษาไทยที่เป็นคำถาม/คำเชื่อม ตัดทิ้งก่อนสร้าง n-gram ไม่งั้นทุกหัวข้อจะได้คะแนนเท่ากันหมด
_TH_NOISE = [
    "คืออะไร", "คือ", "อะไรบ้าง", "อะไร", "ยังไงบ้าง", "ยังไง", "อย่างไร",
    "ช่วยอธิบาย", "อธิบาย", "ช่วยบอก", "ช่วย", "หน่อย", "ขอตัวอย่าง",
    "ตัวอย่าง", "อยากรู้", "อยากทราบ", "เรื่อง", "ครับ", "ค่ะ", "คะ", "นะ",
    "แล้ว", "และ", "หรือ", "ที่", "ให้", "ได้", "การ", "ของ", "แบบ", "ทำ", "ใช้",
]


# คนไทยถามด้วยคำธรรมดา แต่หัวข้อในไฟล์เป็นศัพท์อังกฤษ ตารางนี้เชื่อมสองฝั่งเข้าหากัน
# ระบบให้คะแนนคำอังกฤษที่ตรงกับหัวข้อสูงสุด การเติมคำอังกฤษให้จึงช่วยการค้นหาได้มาก
_ALIASES = {
    "sum": ("ผลรวม", "ยอดรวม", "รวมยอด", "บวกกัน", "รวมทั้งหมด", "ซื้อรวม", "ขายรวม"),
    "group by": ("จัดกลุ่ม", "แต่ละกลุ่ม", "แยกตาม", "จัดหมวด", "ต่อกลุ่ม"),
    "having": ("กรองหลังจัดกลุ่ม", "กลุ่มที่มากกว่า", "กลุ่มที่เกิน"),
    "count": ("นับจำนวน", "มีกี่", "จำนวนแถว", "นับ"),
    "avg": ("ค่าเฉลี่ย", "เฉลี่ย"),
    "max": ("มากสุด", "สูงสุด"),
    "min": ("น้อยสุด", "ต่ำสุด"),
    "order by": ("เรียงลำดับ", "จัดเรียง", "เรียงจาก", "มากไปน้อย", "น้อยไปมาก"),
    "where": ("กรองข้อมูล", "เฉพาะที่", "เงื่อนไข"),
    "join": ("เชื่อมตาราง", "รวมตาราง", "ต่อตาราง", "สองตาราง", "หลายตาราง", "ตารางมาต่อ"),
    "distinct": ("ไม่ซ้ำ", "ไม่ให้ซ้ำ", "ซ้ำกัน"),
    "like": ("ค้นหาคำ", "ขึ้นต้นด้วย", "ลงท้ายด้วย", "มีคำว่า"),
    "between": ("อยู่ระหว่าง", "ช่วงตั้งแต่", "ตั้งแต่ถึง"),
    "insert": ("เพิ่มข้อมูล", "บันทึกข้อมูล", "ใส่ข้อมูล"),
    "update": ("แก้ไขข้อมูล", "อัปเดต", "เปลี่ยนข้อมูล"),
    "delete": ("ลบข้อมูล", "ลบแถว", "เอาข้อมูลออก"),
    "limit": ("จำกัดจำนวน", "เอาแค่", "กี่อันแรก"),
    "primary key": ("คีย์หลัก", "รหัสประจำ"),
    "foreign key": ("คีย์นอก", "เชื่อมความสัมพันธ์"),
    "index": ("ทำให้เร็วขึ้น", "ค้นหาเร็ว", "ดัชนี"),
    "sql injection": ("แฮก", "โจมตี", "เจาะระบบ", "ความปลอดภัย", "ป้องกันการโจมตี"),
    "view": ("ตารางเสมือน", "มุมมอง"),
    "null": ("ค่าว่าง", "ไม่มีค่า"),
}


def _alias_words(text):
    """หาคำอังกฤษที่ควรใช้ค้นหาเพิ่ม จากคำไทยที่ผู้ใช้พิมพ์"""
    found = set()
    for english, thai_terms in _ALIASES.items():
        if any(t in text for t in thai_terms):
            found.update(english.split())
    return found


def _clean(value):
    value = (value or "").strip()
    return "" if value in _EMPTY else value


def _load_file(path):
    entries = []
    # utf-8-sig เพื่อตัด BOM ที่ติดมากับไฟล์ CSV จาก Excel
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            values = list(row.values())
            topic = _clean(values[0] if values else "")
            if not topic:
                continue
            entries.append({
                "topic": topic,
                "description": _clean(values[1] if len(values) > 1 else ""),
                "syntax": _clean(values[2] if len(values) > 2 else ""),
                "example": _clean(values[3] if len(values) > 3 else ""),
                "source": os.path.basename(path),
            })
    return entries


_MD_FENCE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)


def _md_code(text):
    """ดึงเนื้อในบล็อกโค้ด ```...``` ถ้าไม่มีก็ใช้ข้อความดิบ"""
    m = _MD_FENCE.search(text)
    return (m.group(1) if m else text).strip()


def _md_prose(text):
    """ตัดเส้นคั่นแนวนอน (--- หรือ ***) ทิ้ง ไม่งั้นเส้นคั่นของหัวข้อถัดไป
    จะถูกดูดมาอยู่ท้ายคำอธิบายของหัวข้อก่อนหน้า"""
    text = re.sub(r"^[ \t]*(-{3,}|\*{3,}|_{3,})[ \t]*$", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _load_md(path):
    """อ่านไฟล์ Markdown ตามข้อตกลง:
    `## หัวข้อ` = 1 หัวข้อ, ข้อความถัดมา = คำอธิบาย,
    `### รูปแบบคำสั่ง` = Syntax, `### ตัวอย่าง` = Example"""
    raw = open(path, encoding="utf-8").read()
    parts = re.split(r"^##[ \t]+(?!#)(.+?)[ \t]*$", raw, flags=re.M)
    entries = []
    for i in range(1, len(parts) - 1, 2):
        topic = _clean(parts[i])
        if not topic:
            continue
        segs = re.split(r"^###[ \t]+(.+?)[ \t]*$", parts[i + 1], flags=re.M)
        named = {segs[j].strip().lower(): segs[j + 1] for j in range(1, len(segs) - 1, 2)}
        syntax = example = ""
        for key, body in named.items():
            if "รูปแบบ" in key or "syntax" in key:
                syntax = syntax or _md_code(body)
            elif "ตัวอย่าง" in key or "example" in key:
                example = example or _md_code(body)
        entries.append({
            "topic": topic,
            "description": _clean(_md_prose(segs[0])),
            "syntax": _clean(syntax),
            "example": _clean(example),
            "source": os.path.basename(path),
        })
    return entries


def load_entries():
    entries = []
    if not os.path.isdir(KNOWLEDGE_DIR):
        return entries
    for filename in sorted(os.listdir(KNOWLEDGE_DIR)):
        lower = filename.lower()
        if lower.endswith(".csv"):
            entries.extend(_load_file(os.path.join(KNOWLEDGE_DIR, filename)))
        elif lower.endswith(".md"):
            entries.extend(_load_md(os.path.join(KNOWLEDGE_DIR, filename)))
    for entry in entries:
        entry["_haystack"] = " ".join([
            entry["topic"], entry["description"], entry["syntax"], entry["example"]
        ]).lower()
    return entries


ENTRIES = load_entries()

_WORD_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_THAI_RE = re.compile(r"[฀-๿]+")


def _strip_thai_noise(text):
    for phrase in _TH_NOISE:
        text = text.replace(phrase, " ")
    return text


def _thai_ngrams(text, sizes=(4, 3)):
    """ภาษาไทยไม่มีช่องว่างระหว่างคำ จึงใช้ n-gram ระดับตัวอักษรแทนการตัดคำ"""
    grams = set()
    for chunk in _THAI_RE.findall(_strip_thai_noise(text)):
        for size in sizes:
            if len(chunk) < size:
                continue
            for i in range(len(chunk) - size + 1):
                grams.add(chunk[i:i + size])
    return grams


def _score(entry, words, grams, is_definition=False):
    topic = entry["topic"].lower()
    score = 0.0
    # ถ้าผู้ใช้ถามเชิงนิยาม ให้หัวข้อทฤษฎี ("... คืออะไร?") ขึ้นก่อนหัวข้อคำสั่ง
    if is_definition and "คืออะไร" in topic:
        score += 2.5
    for word in words:
        if word in topic:
            score += 10.0
        elif word in entry["_haystack"]:
            score += 2.0
    if grams:
        topic_hits = sum(1 for g in grams if g in topic)
        body_hits = sum(1 for g in grams if g in entry["_haystack"])
        # หารด้วยจำนวน n-gram ทั้งหมด เพื่อไม่ให้คำถามยาวได้เปรียบเกินไป
        score += 8.0 * topic_hits / len(grams)
        score += 3.0 * body_hits / len(grams)
    return score


def search(query, limit=6, min_score=1.0):
    """คืนรายการหัวข้อที่เกี่ยวข้องกับคำถามมากที่สุด"""
    if not query or not ENTRIES:
        return []
    lowered = query.lower()
    words = {w for w in _WORD_RE.findall(lowered) if len(w) > 1 and w not in _STOPWORDS}
    words |= _alias_words(lowered)
    grams = _thai_ngrams(lowered)
    is_definition = any(k in lowered for k in ("คืออะไร", "หมายถึง", "what is"))
    scored = [(_score(e, words, grams, is_definition), e) for e in ENTRIES]
    ranked = sorted([p for p in scored if p[0] > 0], key=lambda p: p[0], reverse=True)

    strong = [e for s, e in ranked if s >= min_score]
    if strong:
        return strong[:limit]
    # ไม่มีหัวข้อไหนถึงเกณฑ์ แต่ยังพอมีที่เกี่ยวข้องบ้าง — ส่งอันที่ใกล้ที่สุดให้โมเดลตัดสินเอง
    # กันคำถาม SQL จริง ๆ ที่ใช้คำไม่ตรงกับในไฟล์ โดนปฏิเสธทั้งที่ตอบได้
    return [e for _, e in ranked[:3]]


# บอกให้ชัดว่าช่องไหนไม่มีข้อมูล ไม่งั้นโมเดลจะเข้าใจว่าไม่ได้ส่งมาแล้วแต่งเติมเอง
_MISSING = "(ไม่มีข้อมูลส่วนนี้ในคลังความรู้ ห้ามแต่งขึ้นเอง)"


def format_entries(entries):
    blocks = []
    for entry in entries:
        blocks.append("\n".join([
            f"### {entry['topic']}",
            f"คำอธิบาย: {entry['description'] or _MISSING}",
            f"รูปแบบคำสั่ง: {entry['syntax'] or _MISSING}",
            f"ตัวอย่าง: {entry['example'] or _MISSING}",
        ]))
    return "\n\n".join(blocks)


def topic_index():
    """รายชื่อหัวข้อทั้งหมดในคลังความรู้ ใช้บอกขอบเขตที่ตอบได้"""
    return " | ".join(e["topic"] for e in ENTRIES)


def build_context(query, limit=6):
    entries = search(query, limit=limit)
    if not entries:
        return ""
    return format_entries(entries)

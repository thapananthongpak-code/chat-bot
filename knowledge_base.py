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


def load_entries():
    entries = []
    if not os.path.isdir(KNOWLEDGE_DIR):
        return entries
    for filename in sorted(os.listdir(KNOWLEDGE_DIR)):
        if filename.lower().endswith(".csv"):
            entries.extend(_load_file(os.path.join(KNOWLEDGE_DIR, filename)))
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
    grams = _thai_ngrams(lowered)
    is_definition = any(k in lowered for k in ("คืออะไร", "หมายถึง", "what is"))
    scored = [(_score(e, words, grams, is_definition), e) for e in ENTRIES]
    scored = [(s, e) for s, e in scored if s >= min_score]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [e for _, e in scored[:limit]]


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

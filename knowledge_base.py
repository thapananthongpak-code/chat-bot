"""โหลดตำราฐานข้อมูล (Markdown ที่แปลงจาก PDF) แล้วค้นหาหัวข้อที่เกี่ยวข้องกับคำถามผู้ใช้"""

import csv
import os
import re
import hashlib
import json

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "output/pdf/manifest.json")
DATASET_ERROR = ""
DOCUMENT_META = {}

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
    "ความแตกต่าง", "แตกต่าง", "ต่างกัน", "เปรียบเทียบ", "ไหม", "กับ",
]


# คนไทยถามด้วยคำธรรมดา แต่หัวข้อในไฟล์เป็นศัพท์อังกฤษ ตารางนี้เชื่อมสองฝั่งเข้าหากัน
# ระบบให้คะแนนคำอังกฤษที่ตรงกับหัวข้อสูงสุด การเติมคำอังกฤษให้จึงช่วยการค้นหาได้มาก
# คำอังกฤษฝั่งซ้ายต้องมีอยู่ในชื่อหัวข้อของตำรา ไม่งั้นเติมไปก็ไม่ช่วย
_ALIASES = {
    "aggregate": ("ผลรวม", "ยอดรวม", "ค่าเฉลี่ย", "เฉลี่ย", "มากสุด", "สูงสุด", "น้อยสุด", "ต่ำสุด",
                  "นับจำนวน", "ฟังก์ชันสรุป"),
    "group by": ("จัดกลุ่ม", "แยกตาม", "กรองหลังจัดกลุ่ม"),
    "order by": ("เรียงลำดับ", "จัดเรียง", "มากไปน้อย", "น้อยไปมาก"),
    "where": ("กรองข้อมูล", "เงื่อนไข"),
    "join": ("เชื่อมตาราง", "รวมตาราง", "สองตาราง", "หลายตาราง"),
    "distinct": ("ไม่ซ้ำ",),
    "aliases": ("ตั้งชื่อชั่วคราว", "ชื่อเล่น"),
    "create": ("สร้างตาราง", "สร้างฐานข้อมูล"),
    "alter": ("แก้ไขโครงสร้าง", "เพิ่มคอลัมน์"),
    "drop": ("ลบตาราง",),
    "insert": ("เพิ่มข้อมูล", "ใส่ข้อมูล"),
    "update": ("แก้ไขข้อมูล", "อัปเดต"),
    "delete": ("ลบข้อมูล", "ลบแถว"),
    "primary key": ("คีย์หลัก",),
    "foreign key": ("คีย์นอก",),
}

# ศัพท์ที่ผู้ใช้พิมพ์ได้หลายแบบ แต่ตำราใช้คำเดียว: เติมคำที่ตำราใช้ต่อท้ายคำถาม
# (ค่าที่สามเป็น True = แทนที่คำเดิมเลย เพราะคำอังกฤษเดิมจะไปตรงกับหัวข้ออื่น)
_REWRITES = [
    (r"weak entit(y|ies)", "เอ็นทิตี้แบบอ่อนแอ", True),
    (r"\b1\s*nf\b|first normal form", "นอมอลฟอร์มระดับที่ 1"),
    (r"\b2\s*nf\b|second normal form", "นอมอลฟอร์มระดับที่ 2"),
    (r"\b3\s*nf\b|third normal form", "นอมอลฟอร์มระดับที่ 3"),
    (r"นอร์มัลไลเซชัน|นอร์มัลไลเซชั่น|นอร์มอลไลเซชัน|นอมอลไลเซชั่น", "นอมอลไลเซชัน", True),
    (r"normali[sz]", "นอมอลไลเซชัน"),
    (r"นอร์มัลฟอร์ม|นอร์มอลฟอร์ม", "นอมอลฟอร์ม", True),
    (r"normal form", "นอมอลฟอร์ม"),
    (r"\bdbms\b", "ระบบจัดการฐานข้อมูล"),
    (r"data dictionary", "พจนานุกรมข้อมูล"),
    (r"\bentit(y|ies)\b|เอนทิตี|เอ็นทิตี(?!้)", "เอ็นทิตี้"),
    (r"\battributes?\b|แอตทริบิวท์|แอทริบิวต์|แอททริบิวต์", "แอตทริบิวต์"),
    (r"\brelations?\b|รีเลชั่น", "รีเลชัน"),
    (r"\b(having|group)\b", "group by"),
    (r"\b(count|avg|sum|max|min)\b", "aggregate"),
    (r"functional dependenc|dependency|ฟังก์ชันขึ้นต่อกัน", "ฟังก์ชันการขึ้นต่อกัน"),
    (r"\bschema\b|สคีมา", "โครงร่างฐานข้อมูล"),
    (r"data independence", "ความเป็นอิสระของข้อมูล"),
    (r"three.?(level|schema)|3.?(level|schema)", "สถาปัตยกรรม 3 ระดับ"),
    (r"\berd?\b|e-r diagram|อีอาร์", "er diagram"),
    (r"\binformation\b", "สารสนเทศ"),
    (r"\bsecurity\b", "ความปลอดภัย"),
    (r"\bwildcards?\b|ไวลด์การ์ด|\boperators?\b|ตัวดำเนินการ", "สัญลักษณ์"),
    (r"\bpassword\b|รหัสผ่าน|เข้ารหัส", "ระบบรักษาความปลอดภัยสำหรับผู้ใช้"),
]

# หัวข้อบทนำ บทสรุป และแบบฝึกหัด พูดกว้าง ๆ ทั้งบท ให้แพ้หัวข้อเนื้อหาจริง เว้นแต่ผู้ใช้ถามถึงเอง
_META_WORDS = ("บทนำ", "สรุป", "แบบฝึกหัด", "summary", "exercise")


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
    return "\n\n".join(_MD_FENCE.findall(text)).strip() if m else _md_prose(text)


def _md_prose(text):
    """ตัดเส้นคั่นแนวนอน (--- หรือ ***) ทิ้ง ไม่งั้นเส้นคั่นของหัวข้อถัดไป
    จะถูกดูดมาอยู่ท้ายคำอธิบายของหัวข้อก่อนหน้า"""
    text = re.sub(r"^[ \t]*(-{3,}|\*{3,}|_{3,})[ \t]*$", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _load_md(path):
    """อ่านไฟล์ Markdown ตามข้อตกลง:
    `## หัวข้อ` = 1 หัวข้อ, ข้อความถัดมา = คำอธิบาย,
    `### รูปแบบคำสั่ง` = Syntax, `### ตัวอย่าง` = Example"""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
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
            "references": _md_prose(named.get("แหล่งอ้างอิง", "")),
        })
    return entries


def load_entries():
    """Fail closed: only load the verified textbook, never legacy files or a model."""
    global DATASET_ERROR, DOCUMENT_META
    DATASET_ERROR, DOCUMENT_META = "", {}
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        # basename กันไม่ให้ manifest ชี้ออกไปนอกโฟลเดอร์ที่กำหนด
        path = os.path.join(KNOWLEDGE_DIR, os.path.basename(manifest["markdown_filename"]))
        pdf_path = os.path.join(os.path.dirname(MANIFEST_PATH), os.path.basename(manifest["pdf_filename"]))
        for target, expected in (
            (path, manifest["markdown_sha256"]),
            (pdf_path, manifest["pdf_sha256"]),
        ):
            with open(target, "rb") as f:
                if hashlib.sha256(f.read()).hexdigest() != expected:
                    raise ValueError("Handbook checksum mismatch")
        entries = _load_md(path)
        if len(entries) != manifest["topic_count"]:
            raise ValueError("Handbook topic count mismatch")
        DOCUMENT_META = manifest
    except (OSError, ValueError, KeyError, TypeError):
        DATASET_ERROR = "ชุดข้อมูลยังไม่พร้อมหรือไม่ตรงกับ PDF จึงหยุดตอบเพื่อป้องกันการใช้ข้อมูลผิดฉบับครับ"
        return []
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
    for word in words:
        if re.search(r"\b" + re.escape(word) + r"\b", topic):
            score += 10.0
        elif re.search(r"\b" + re.escape(word) + r"\b", entry["_haystack"]):
            score += 2.0
    if grams:
        topic_hits = sum(1 for g in grams if g in topic)
        body_hits = sum(1 for g in grams if g in entry["_haystack"])
        # หารด้วยจำนวน n-gram ทั้งหมด เพื่อไม่ให้คำถามยาวได้เปรียบเกินไป
        score += 8.0 * topic_hits / len(grams)
        score += 3.0 * body_hits / len(grams)
    return score


def _legacy_search(query, limit=6, min_score=1.0):
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
    return []


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


def _expand(text):
    for pattern, extra, *replace in _REWRITES:
        if replace:
            text = re.sub(pattern, extra, text)
        elif re.search(pattern, text):
            text += " " + extra
    return text


def _numbers(text):
    """ตัวเลขที่มีความหมายในชื่อหัวข้อ เช่น 'ระดับที่ 3' โดยไม่นับเลขหัวข้อ 7.5 และลำดับ · 3."""
    text = re.sub(r"^\d+\.\d+ |· \d+\. |บทที่ \d+", " ", text)
    return set(re.findall(r"(?<![\d.])\d(?![\d.])", text))


def _chapter_of(topic):
    """'7.5 ...' / 'บทสรุป บทที่ 7 ...' / 'ภาคผนวก ก ...' -> '7' หรือ 'ก'"""
    m = re.match(r"^(\d+)\.\d+ ", topic) or re.search(r"บทที่ (\d+)", topic) or re.search(r"ภาคผนวก ([กข])", topic)
    return m.group(1) if m else ""


def _is_meta(topic):
    return topic.startswith(("บทสรุป", "แบบฝึกหัด")) or topic.endswith("(บทนำ)")


# คำที่ตามหลัง "ภาษา" แล้วยังหมายถึงภาษา SQL ในตำรา (เช่น ภาษา DDL = ภาษานิยามข้อมูลของ SQL)
_SQL_LANG_WORDS = {"sql", "ddl", "dml", "dcl", "data", "structured", "query"}


def search(query, limit=6, min_score=1.0):
    """Require topic evidence: a word in the body alone is not evidence the book explains it."""
    text = query.lower().strip()
    exact = [entry for entry in ENTRIES if entry["topic"].lower() == text]
    if exact:
        return exact[:limit]
    # ระบุเลขหัวข้อมาตรง ๆ เช่น "7.5"
    num = re.search(r"(?<![\d.])(\d{1,2}\.\d{1,2})(?![\d.])", text)
    if num:
        by_num = [e for e in ENTRIES if e["topic"].startswith(num.group(1) + " ")]
        if by_num:
            return by_num[:1]
    if re.search(r"(?:what is sql\b|(?<![\w-])sql\s*(?:คืออะไร|ทำอะไรได้|ใช้ทำอะไร|มีกี่ประเภท|มีกี่แบบ|แบ่งเป็น)"
                 r"|ภาษา sql คือ|ความหมายของภาษา sql)", text):
        return [e for e in ENTRIES if e["topic"].startswith("8.1 ")][:1]

    if re.search(r"ภาคผนวก\s*[ค-ฮ]", text):
        return []   # ตำรามีแค่ภาคผนวก ก และ ข
    chapter = re.search(r"บทที่\s*(\d{1,2})|ภาคผนวก\s*([กข])", text)
    pool = ENTRIES
    if chapter:
        wanted = chapter.group(1) or chapter.group(2)
        pool = [e for e in ENTRIES if _chapter_of(e["topic"]) == wanted] or ENTRIES
        text = text.replace(chapter.group(0), " ")
    meta_query = any(k in text for k in _META_WORDS)

    # ตำรามีแต่ "ภาษา SQL" ถ้าถามภาษาอื่น (ภาษา C, Python, Java) คำว่า "ภาษา" อย่างเดียว
    # จะพาไปเจอหัวข้อ "8.1 ความหมายของภาษา SQL" ทั้งที่ตำราไม่ได้พูดถึงภาษานั้นเลย
    lang = re.search(r"ภาษา\s*([a-z][a-z0-9+#]*|ซี|จาวา|ไพทอน|ไพธอน)", text)
    if lang and lang.group(1) not in _SQL_LANG_WORDS:
        return []

    text = _expand(text)
    words = set(_WORD_RE.findall(text)) - _STOPWORDS - {"function", "use", "explain", "does"}
    words |= _alias_words(text)
    english = " ".join(_WORD_RE.findall(query.lower()))
    grams = _thai_ngrams(text)
    numbers = _numbers(text)
    ranked = []
    for e in pool:
        topic = e["topic"].lower()
        tokens = set(_WORD_RE.findall(topic))
        hits = words & tokens
        thai = _thai_ngrams(topic)
        overlap = len(grams & thai) / max(1, len(grams))
        if not hits and not (len(grams & thai) >= 3 and overlap >= .45):
            continue
        score = 10 * len(hits) + overlap * 8
        if words and hits:
            score += 5 * len(hits) / len(words)
        # วลีอังกฤษหลายคำตรงกับชื่อหัวข้อทั้งวลี เช่น "many to many"
        if " " in english and english in topic:
            score += 15
        score += 6 * len(numbers & _numbers(topic))
        if _is_meta(e["topic"]) and not meta_query:
            score *= .3
        ranked.append((score, e))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        if chapter and pool is not ENTRIES:
            # ถามถึงบทเฉย ๆ เช่น "บทที่ 7" ให้บทนำของบทนั้น
            return [e for e in pool if e["topic"].endswith("(บทนำ)")][:1] or pool[:1]
        return []
    return [e for score, e in ranked if score >= max(min_score, ranked[0][0] * .7)][:limit]


BOOK_NAME = "การจัดการระบบฐานข้อมูลเพื่องานธุรกิจ"
HELP_HINT = 'พิมพ์ "ตอบอะไรได้บ้าง" เพื่อดูหัวข้อทั้งหมด'
NO_DATA = ("ไม่มีข้อมูลเรื่องนี้ในตำราครับ\n\n"
           f"ผมตอบได้เฉพาะเรื่องฐานข้อมูลและ SQL จากตำรา **{BOOK_NAME}** — {HELP_HINT}")

EXAMPLES = ["คีย์หลัก (Primary Key) คืออะไร", "ER Diagram คืออะไร", "นอมอลฟอร์มระดับที่ 3 (3NF)",
            "INNER JOIN กับ LEFT JOIN ต่างกันยังไง", "GROUP BY กับ HAVING ใช้ยังไง"]

# คำถามถึงตัวบอท ไม่ใช่คำถามเนื้อหา: ตัดคำสุภาพ/สรรพนามทิ้งแล้วต้องเหลือตรงกับวลีเหล่านี้ทั้งหมด
# (เทียบทั้งประโยค เพื่อไม่ให้ "SQL ทำอะไรได้บ้าง" กลายเป็นคำถามถึงบอท)
_POLITE = re.compile(r"[\s?!.ๆ]+|ครับ|คับ|ค่ะ|คะ|นะ|จ้า|จ้ะ|หน่อย|มากๆ|มาก")
# สรรพนามเรียกบอท ตัดทิ้งเฉพาะตอนเช็กคำถามถึงบอท (ห้ามตัดก่อนเช็ก "ขอบคุณ" ไม่งั้นเหลือ "ขอบ")
_PRONOUNS = re.compile(r"คุณ|บอท|ครูเอสคิว|นาย|เธอ|แก|น้อง")
_GREETINGS = ("สวัสดี", "หวัดดี", "ดีจ้า", "hello", "hi", "hey")
_THANKS = ("ขอบคุณ", "ขอบใจ", "thanks", "thankyou", "thx")
_ABOUT_BOT = {
    "ตอบอะไรได้บ้าง", "ตอบอะไรได้", "ตอบเรื่องอะไรได้บ้าง", "ตอบเรื่องอะไรบ้าง", "ทำอะไรได้บ้าง", "ทำอะไรได้",
    "ช่วยอะไรได้บ้าง", "ช่วยอะไรได้", "ถามอะไรได้บ้าง", "ถามอะไรได้", "ถามเรื่องอะไรได้บ้าง", "รู้อะไรบ้าง",
    "รู้เรื่องอะไรบ้าง", "มีหัวข้ออะไรบ้าง", "มีเรื่องอะไรบ้าง", "คือใคร", "เป็นใคร", "ใช้งานยังไง", "ใช้งานอย่างไร",
    "วิธีใช้", "help", "/help", "เมนู", "menu",
}


def _about_bot():
    chapters = [e["topic"].removesuffix(" (บทนำ)") for e in ENTRIES if e["topic"].endswith("(บทนำ)")]
    return "\n".join(
        [f"ผมครูเอสคิว ตอบคำถามเรื่องฐานข้อมูลและ SQL จากตำรา **{BOOK_NAME}** เท่านั้น "
         "ไม่แต่งคำตอบเอง ถ้าเรื่องไหนตำราไม่มี ผมจะบอกว่าไม่มีข้อมูลครับ", "", "ตำราแบ่งเป็นหัวข้อเหล่านี้"]
        + ["- " + c for c in chapters]
        + ["", "ลองถามเช่น"] + ["- " + q for q in EXAMPLES]
        + ["", "ถามด้วยเลขหัวข้อก็ได้ เช่น 7.5 หรือ แบบฝึกหัดบทที่ 7"])


def small_talk(query):
    """คำทักทาย คำขอบคุณ และคำถามว่าบอทตอบอะไรได้ ตอบด้วยข้อความคงที่ ไม่ค้นในตำรา"""
    text = _POLITE.sub("", query.lower())
    for g in _GREETINGS:
        if text.startswith(g):
            rest = text[len(g):]
            if not rest:
                return ("สวัสดีครับ ผมครูเอสคิว ถามเรื่องฐานข้อมูลและ SQL ได้เลย เช่น "
                        + ", ".join(EXAMPLES[:3]) + "\n\n" + HELP_HINT)
            text = rest   # "สวัสดี ตอบอะไรได้บ้าง" ให้ดูส่วนที่เหลือต่อ
            break
    if text in _THANKS:
        return "ยินดีครับ มีคำถามเรื่องฐานข้อมูลหรือ SQL ถามต่อได้เลยครับ"
    if _PRONOUNS.sub("", text) in _ABOUT_BOT:
        return _about_bot()
    return None


FIGURE_DIR = os.path.join(os.path.dirname(__file__), "static", "figures")
FIGURE_URL = "/static/figures/"
_CAPTION_RE = re.compile(r"^ภาพที่\s*(\d+\.\d+)(?!\d)")


def with_figures(description):
    """ใส่รูปจากตำรา (ตัดจากหน้า PDF ไว้ล่วงหน้า) ไว้เหนือบรรทัดคำบรรยาย "ภาพที่ X.Y" แบบเดียวกับในเล่ม
    ใช้เฉพาะรูปที่อยู่ใน manifest และมีไฟล์อยู่จริง"""
    figures = {f["figure"]: f for f in DOCUMENT_META.get("figures", [])}
    if not figures:
        return description
    out = []
    for line in description.split("\n"):
        m = _CAPTION_RE.match(line)
        f = figures.get(m.group(1)) if m else None
        if f and os.path.isfile(os.path.join(FIGURE_DIR, os.path.basename(f["file"]))):
            out.append(f"![ภาพที่ {f['figure']}]({FIGURE_URL}{os.path.basename(f['file'])})")
        out.append(line)
    return "\n".join(out)


def answer_from_dataset(history):
    """No generated prose: render only stored fields, with traceable provenance."""
    global ENTRIES
    # Revalidate on each answer, including when files change after startup.
    ENTRIES = load_entries()
    if DATASET_ERROR:
        return DATASET_ERROR
    questions = [str(m.get("content") or "") for m in history if isinstance(m, dict) and m.get("role") == "user"]
    query = questions[-1] if questions else ""
    canned = small_talk(query)
    if canned:
        return canned
    entries = search(query, limit=2)
    if not entries and len(questions) > 1 and query.startswith(("แล้ว", "ขอตัวอย่าง", "อธิบายต่อ")):
        entries = search(questions[-2] + " " + query, limit=2)
    if not entries:
        return NO_DATA
    blocks = []
    for e in entries:
        parts = ["## " + e["topic"], with_figures(e["description"])]
        for key, label in (("syntax", "รูปแบบคำสั่ง"), ("example", "ตัวอย่างจากชุดข้อมูล")):
            if e[key]:
                parts.append("### " + label + "\n```sql\n" + e[key] + "\n```")
        # บท + เลขหน้า มาจากส่วน "แหล่งอ้างอิง" ของหัวข้อในไฟล์ (ตรวจกับสารบัญและหน้า PDF แล้ว)
        parts.append("แหล่งข้อมูล: " + (e.get("references") or e["topic"]) + " · ไฟล์ " + e["source"])
        blocks.append("\n\n".join(parts))
    return "\n\n---\n\n".join(blocks)

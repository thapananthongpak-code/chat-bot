"""โหลดตำราฐานข้อมูล (Markdown ที่แปลงจาก PDF) แล้วค้นหาหัวข้อที่เกี่ยวข้องกับคำถามผู้ใช้"""

import os
import re
import hashlib
import json

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "output/pdf/manifest.json")
DATASET_ERROR = ""
DOCUMENT_META = {}

_EMPTY = {"", "-", "–", "—"}

# คำภาษาอังกฤษที่พบบ่อยจนไม่ช่วยแยกแยะหัวข้อ
_STOPWORDS = {"sql", "table", "column", "name", "value", "data", "the", "how", "what", "is", "in", "of", "to"}

# วลีภาษาไทยที่เป็นคำถาม/คำเชื่อม ตัดทิ้งก่อนสร้าง n-gram ไม่งั้นทุกหัวข้อจะได้คะแนนเท่ากันหมด
_TH_NOISE = [
    "คืออะไร", "คือ", "อะไรบ้าง", "อะไร", "ยังไงบ้าง", "ยังไง", "อย่างไร",
    "ช่วยอธิบาย", "อธิบาย", "ช่วยบอก", "ช่วย", "หน่อย", "ขอตัวอย่าง",
    "ตัวอย่าง", "อยากรู้", "อยากทราบ", "เรื่อง", "ครับ", "ค่ะ", "คะ", "นะ",
    "แล้ว", "และ", "หรือ", "ที่", "ให้", "ได้", "การ", "ของ", "แบบ", "ทำ", "ใช้",
    "ความแตกต่าง", "แตกต่าง", "ต่างกัน", "เปรียบเทียบ", "ไหม", "กับ", "มีกี่", "กี่",
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


def _md_prose(text):
    """ตัดเส้นคั่นแนวนอน (--- หรือ ***) ทิ้ง ไม่งั้นเส้นคั่นของหัวข้อถัดไป
    จะถูกดูดมาอยู่ท้ายคำอธิบายของหัวข้อก่อนหน้า"""
    text = re.sub(r"^[ \t]*(-{3,}|\*{3,}|_{3,})[ \t]*$", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _load_md(path):
    """อ่านไฟล์ Markdown ตามข้อตกลง:
    `## หัวข้อ` = 1 หัวข้อ, ข้อความถัดมา = เนื้อหา, `### แหล่งอ้างอิง` = บทและเลขหน้า"""
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
        entries.append({
            "topic": topic,
            "description": _clean(_md_prose(segs[0])),
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
        # คะแนนเท่ากัน ให้หัวข้อที่ชื่อตรงกับคำถามเกือบทั้งชื่อชนะ (เช่น "5.3 เอ็นทิตี้" ชนะ
        # "4.6 กฎความคงสภาพ… · 1. กฎความคงสภาพของเอ็นทิตี้" เมื่อถาม "เอ็นทิตี้มีกี่ประเภท")
        # (หัวข้อย่อยวัดเฉพาะชื่อส่วนของตัวเอง ไม่นับชื่อหัวข้อหลักที่นำหน้า)
        own = _thai_ngrams(topic.split(" · ")[-1])
        if own:
            score += .5 * len(grams & own) / len(own)   # น้ำหนักน้อย ใช้ตัดสินเฉพาะตอนคะแนนใกล้กัน
        if _is_meta(e["topic"]) and not meta_query:
            score *= .3
        ranked.append((score, e))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        if chapter and pool is not ENTRIES:
            # ถามถึงบทเฉย ๆ เช่น "บทที่ 7" ให้บทนำของบทนั้น
            return [e for e in pool if e["topic"].endswith("(บทนำ)")][:1] or pool[:1]
        return []

    def coverage(topic):
        """ส่วนของคำถามที่ชื่อหัวข้อนี้ตอบ: คำอังกฤษ ตัวเลข และ n-gram ไทยที่ตรงกัน"""
        topic = topic.lower()
        return ({"w:" + w for w in words & set(_WORD_RE.findall(topic))}
                | {"n:" + n for n in numbers & _numbers(topic)}
                | {"g:" + g for g in grams & _thai_ngrams(topic)})

    def adds(cov, base):
        """cov ตอบส่วนของคำถามที่ base ยังไม่ได้ตอบจริงไหม (ไม่ใช่แค่ตัวอักษรซ้ำบังเอิญ 1-2 ชิ้น)"""
        new = cov - base
        new_grams = sum(1 for x in new if x.startswith("g:"))
        return any(not x.startswith("g:") for x in new) or new_grams >= max(3, .25 * len(grams))

    by_topic = {e["topic"]: e for e in ENTRIES}
    cut = max(min_score, ranked[0][0] * .7)
    chosen, covered = [], set()
    for score, e in ranked:
        if score < cut or len(chosen) >= limit:
            break
        cov = coverage(e["topic"])
        parent = by_topic.get(e["topic"].split(" · ")[0])
        if parent is not e and parent is not None:
            if any(c is parent for c in chosen):
                continue   # ตอบทั้งหัวข้อหลักไปแล้ว ส่วนย่อยรวมอยู่ในนั้น
            # ส่วนย่อยตรงกับคำถามแค่เพราะชื่อหัวข้อหลัก (เช่น "ประเภทของคีย์") ให้ตอบทั้งหัวข้อ ไม่ใช่ส่วนเดียว
            parent_cov = coverage(parent["topic"])
            if not adds(cov, parent_cov):
                e, cov = parent, parent_cov
        if any(c is e for c in chosen):
            continue
        # หัวข้อถัดไปต้องตอบส่วนของคำถามที่หัวข้อก่อนหน้ายังไม่ได้ตอบ (เช่น LEFT JOIN ใน "INNER JOIN กับ LEFT JOIN")
        # ไม่งั้นเป็นแค่หัวข้อที่มีคำซ้ำ ไม่ใช่เรื่องที่ถาม
        if chosen and not adds(cov, covered):
            continue
        # บทนำ/บทสรุป/แบบฝึกหัด พูดกว้าง ๆ ทั้งบท ไม่ดึงมาเป็นหัวข้อเสริม เว้นแต่ผู้ใช้ถามถึงเอง
        if chosen and _is_meta(e["topic"]) and not meta_query:
            continue
        chosen.append(e)
        covered |= cov
    return chosen


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


def section_parts(entry):
    """หัวข้อยาวถูกแบ่งเป็นส่วนย่อย ("4.5 ประเภทของคีย์ · 3. คีย์หลัก") ถ้าตอบหัวข้อหลัก ต้องได้ครบทุกส่วน
    ไม่ใช่แค่ย่อหน้านำ (ซึ่งมักจบด้วย "ดังรายละเอียดต่อไปนี้")"""
    if " · " in entry["topic"]:
        return [entry]
    return [entry] + [e for e in ENTRIES if e["topic"].startswith(entry["topic"] + " · ")]


# ---------------------------------------------------------------- บทสนทนาต่อเนื่อง
# ถามต่อสั้น ๆ เช่น "ขอตัวอย่างเพิ่ม" "อธิบายเพิ่ม" "มันต่างกันยังไง" ต้องรู้ว่ากำลังคุยเรื่องอะไรอยู่
# เรื่องที่คุยอยู่ = หัวข้อ (บรรทัด "## ") ในคำตอบล่าสุดของบอท ซึ่งเบราว์เซอร์ส่งประวัติมาทุกครั้ง
_EXAMPLE_RE = re.compile(r"ตัวอย่าง|example", re.I)
_MORE_RE = re.compile(r"อธิบายเพิ่ม|อธิบายต่อ|ขยายความ|ละเอียด|เพิ่มเติม|ข้อมูลเพิ่ม|มีอะไรอีก|อะไรอีก|มีอีก|อีกไหม|"
                      r"เกี่ยวข้อง|เกี่ยวกับหัวข้อนี้|เกี่ยวกับเรื่องนี้|ต่อเลย|ต่อไป|เล่าต่อ|\bmore\b", re.I)
_COMPARE_RE = re.compile(r"ต่างกัน|ต่างจาก|แตกต่าง|เทียบ|เหมือนกันไหม|\bvs\b", re.I)
# ต่อจากคำตอบตัวอย่าง: "อีก" "มีอีกไหม" "ต่อ" สั้น ๆ = ขอตัวอย่างต่อ
# (แต่ "เพิ่มเติมที่เกี่ยวกับหัวข้อนี้" "อธิบายเพิ่ม" = ขอหัวข้อที่เกี่ยวข้อง)
_AGAIN_RE = re.compile(r"^(มี|ขอ|เอา)?(อีก|ต่อ)|อีก(ไหม|มั้ย|หน่อย|สิ|ครับ|ค่ะ)?$|\bmore\b", re.I)
_RELATED_RE = re.compile(r"เกี่ยว|อธิบาย|ขยายความ|ละเอียด|หัวข้อ")
# คำที่อ้างถึงเรื่องที่คุยอยู่ ("มันต่างจาก…", "เรื่องนี้…") ถ้าไม่มี ถือว่าเป็นคำถามใหม่ที่ครบในตัวเอง
_BACKREF_RE = re.compile(r"มัน|อันนี้|อันนั้น|ตัวนี้|เรื่องนี้|หัวข้อนี้|ข้างบน|เมื่อกี้|ที่แล้ว|ก่อนหน้า|สองอัน|ทั้งสอง|\bit\b|\bthis\b", re.I)
# คำที่ใช้ถามต่อ ตัดทิ้งก่อนดูว่าผู้ใช้เอ่ยถึงหัวข้อใหม่ไหม
_FOLLOW_WORDS = re.compile(
    r"ขอ|ยก|เอา|ดู|ตัวอย่าง|example|อธิบาย|เพิ่มเติม|เพิ่ม|ขยายความ|ละเอียด|ข้อมูล|อีก|ไหม|หน่อย|ต่อ|เลย|ไป|"
    r"เล่า|เกี่ยวข้อง|เกี่ยวกับ|หัวข้อ|เรื่อง|นี้|นั้น|มัน|อันนี้|แล้ว|ล่ะ|ต่างกัน|ต่างจาก|แตกต่าง|เทียบ|"
    r"เหมือนกัน|ยังไง|อย่างไร|อะไร|มี|บ้าง|ครับ|ค่ะ|คะ|นะ|จ้า|\bmore\b|\bvs\b|[\s?!.,ๆ]+", re.I)
_GENERIC_TERMS = {"sql", "table", "microsoft access", "access", "data", "er", "a", "b", "fk"}
EXAMPLES_PER_ANSWER = 3


def _answer_topics(text):
    return [line[3:].strip() for line in text.split("\n") if line.startswith("## ")]


def conversation_context(history):
    """หัวข้อในคำตอบล่าสุดที่เป็นเนื้อหาจากตำรา (ข้ามคำตอบคงที่/รายการตัวอย่าง ซึ่งไม่มีบรรทัด "## ")
    คืน (หัวข้อล่าสุด, หัวข้อก่อนหน้าที่ต่างออกไป, ข้อความที่บอทเคยแสดงแล้วทั้งหมด)"""
    by_topic = {e["topic"]: e for e in ENTRIES}
    answers = [str(m.get("content") or "") for m in history
               if isinstance(m, dict) and m.get("role") == "assistant"]
    topic_answers = [[by_topic[t] for t in _answer_topics(a) if t in by_topic] for a in answers]
    topic_answers = [t for t in topic_answers if t]
    current = topic_answers[-1] if topic_answers else []
    previous = next((t for t in reversed(topic_answers[:-1])
                     if {e["topic"] for e in t} != {e["topic"] for e in current}), [])
    return current, previous, "\n".join(answers)


def key_terms(entry):
    """คำหลักของหัวข้อ ใช้หาตัวอย่าง/หัวข้อที่เกี่ยวข้อง: วลีอังกฤษในชื่อ (GROUP BY, Primary Key)
    และชื่อไทยของหัวข้อย่อย (คีย์หลัก) ถ้าไม่มีวลีอังกฤษ ใช้ชื่อไทยของหัวข้อ"""
    title = entry["topic"].split(" · ")[-1]
    title = re.sub(r"^(ภาคผนวก [กข] )?(\d+\.)+\d*\s*", "", title)
    english = [p.strip() for p in re.findall(r"[A-Za-z][A-Za-z0-9_ \-]*[A-Za-z0-9_]", title)]
    english = [p for p in english if p.lower() not in _GENERIC_TERMS and len(p) >= 3]
    # วลีไทยของชื่อ (ไม่เอาวงเล็บและคำอังกฤษ แต่เก็บตัวเลข เช่น "นอมอลฟอร์มระดับที่ 3")
    thai = re.sub(r"\(.*\)|[A-Za-z_:/\-]+", " ", title)
    thai = re.sub(r"\s+", " ", thai).strip()
    thai = [thai] if len(thai) >= 4 else []
    if " · " in entry["topic"] or not english:
        return english + thai
    return english


def _blocks(description):
    """แบ่งเนื้อหาเป็นก้อน: บล็อกโค้ด ```...``` ทั้งก้อน หรือบรรทัดข้อความ"""
    lines, out, i = description.split("\n"), [], 0
    while i < len(lines):
        if lines[i].startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append(("code", "\n".join(lines[i:j + 1])))
            i = j + 1
        else:
            out.append(("text", lines[i]))
            i += 1
    return out


def _example_snippets(entry, terms):
    """ตัวอย่างในหัวข้อนี้ที่เกี่ยวกับคำหลัก (ข้อความจากตำราตรงตัว):
    คำสั่ง SQL ที่มีคำหลัก + บรรทัดนำ ("ตัวอย่างที่ …") + ตารางผลลัพธ์ที่ตามมา, หรือบรรทัด "ตัวอย่าง/เช่น" ที่มีคำหลัก"""
    blocks = _blocks(entry["description"])
    has = lambda t: any(term.lower() in t.lower() for term in terms)
    out, used = [], set()
    for k, (kind, text) in enumerate(blocks):
        if k in used:
            continue
        if kind == "code" and has(text):
            lead = [j for j in range(max(0, k - 2), k) if blocks[j][0] == "text" and blocks[j][1].strip()]
            start = next((j for j in lead if blocks[j][1].startswith("ตัวอย่างที่")), lead[-1] if lead else k)
            end = k + 1
            while end < len(blocks) and end - k <= 15 and blocks[end][0] == "text" and (
                    " | " in blocks[end][1] or blocks[end][1].startswith("ตารางที่")):
                end += 1
            used.update(range(start, end))
            out.append("\n".join(b[1] for b in blocks[start:end]))
        elif kind == "text" and has(text) and re.search(r"ตัวอย่าง|เช่น", text) and not text.startswith("ภาพที่"):
            used.add(k)
            out.append(text)
    return out


def _topic_name(current):
    return " / ".join(dict.fromkeys(e["topic"].split(" · ")[0] if len(current) > 1 else e["topic"] for e in current))


def _source_line(e):
    return "แหล่งข้อมูล: " + (e.get("references") or e["topic"]) + " · ไฟล์ " + e["source"]


def more_examples(current, shown_text):
    """ตัวอย่างเรื่องที่คุยอยู่ จากหัวข้ออื่นในตำรา ครั้งละ 3 ตัวอย่าง ข้ามที่เคยแสดงแล้ว"""
    terms = [t for e in current for t in key_terms(e)]
    name = _topic_name(current)
    if not terms:
        return f"เรื่อง **{name}** ในตำรามีตัวอย่างเท่าที่แสดงไปแล้วด้านบนครับ\n\n" + related_topics(current, shown_text, lead=False)
    shown_topics = {e["topic"] for e in current}
    seen = re.sub(r"\s+", "", shown_text)
    found = []
    for order, e in enumerate(ENTRIES):
        if e["topic"] in shown_topics:
            continue
        for snippet in _example_snippets(e, terms):
            if re.sub(r"\s+", "", snippet) not in seen:
                # คำสั่ง SQL จริงก่อน, บทนำ/บทสรุป/แบบฝึกหัดไว้ท้าย, นอกนั้นตามลำดับในเล่ม
                rank = (0 if "```" in snippet else 1, 1 if _is_meta(e["topic"]) else 0, order)
                found.append((rank, e, snippet))
    found.sort(key=lambda f: f[0])
    found = [(e, snippet) for _, e, snippet in found]
    if not found:
        return (f"ตัวอย่างเรื่อง **{name}** ในตำรามีเท่าที่แสดงไปแล้วครับ\n\n"
                + related_topics(current, shown_text, lead=False))
    blocks = [f"ตัวอย่างเพิ่มเติมเรื่อง **{name}** จากหัวข้ออื่นในตำรา"]
    for e, snippet in found[:EXAMPLES_PER_ANSWER]:
        blocks.append("### จาก " + e["topic"] + "\n\n" + with_figures(snippet) + "\n\n" + _source_line(e))
    rest = len(found) - EXAMPLES_PER_ANSWER
    if rest > 0:
        blocks.append(f'ยังมีอีก {rest} ตัวอย่าง พิมพ์ "ขอตัวอย่างเพิ่ม" เพื่อดูต่อ')
    return "\n\n---\n\n".join(blocks)


def related_topics(current, shown_text, lead=True):
    """หัวข้อในตำราที่เกี่ยวกับเรื่องที่คุยอยู่ แสดงเป็นปุ่มให้แตะถามต่อ (ไม่เดาเนื้อหาเอง)"""
    shown = set(_answer_topics(shown_text)) | {e["topic"] for e in current}
    terms = [t.lower() for e in current for t in key_terms(e)]
    chapters = {_chapter_of(e["topic"]) for e in current}
    picks = []

    def add(e):
        if e["topic"] not in shown and all(p is not e for p in picks):
            picks.append(e)

    for e in current:   # 1) ส่วนอื่นของหัวข้อเดียวกันที่ยังไม่ได้แสดง
        base = e["topic"].split(" · ")[0]
        for x in ENTRIES:
            if x["topic"].split(" · ")[0] == base:
                add(x)
    for x in ENTRIES:   # 2) หัวข้ออื่นที่ชื่อมีคำหลัก
        if terms and any(t in x["topic"].lower() for t in terms) and not _is_meta(x["topic"]):
            add(x)
    ranked = []         # 3) หัวข้อในบทเดียวกันที่เนื้อหาพูดถึงคำหลักบ่อย
    for x in ENTRIES:
        if _chapter_of(x["topic"]) in chapters and not _is_meta(x["topic"]):
            hits = sum(x["description"].lower().count(t) for t in terms)
            if hits:
                ranked.append((hits, x))
    for _, x in sorted(ranked, key=lambda p: -p[0]):
        add(x)
    for x in ENTRIES:   # 4) บทสรุปของบท
        if _chapter_of(x["topic"]) in chapters and x["topic"].startswith("บทสรุป"):
            add(x)
    name = _topic_name(current)
    if not picks:
        return f"ในตำราไม่มีหัวข้ออื่นที่เกี่ยวกับ **{name}** เพิ่มเติมครับ"
    head = f"หัวข้อในตำราที่เกี่ยวกับ **{name}** (แตะเพื่อดูเนื้อหา)" if lead else "หัวข้อที่เกี่ยวข้องในตำรา (แตะเพื่อดูเนื้อหา)"
    return head + "\n\n" + "\n".join(f"[[ถาม:{x['topic']}]]" for x in picks[:6])


def render_topics(entries):
    blocks = []
    for e in (part for entry in entries for part in section_parts(entry)):
        # บท + เลขหน้า มาจากส่วน "แหล่งอ้างอิง" ของหัวข้อในไฟล์ (ตรวจกับสารบัญและหน้า PDF แล้ว)
        blocks.append("\n\n".join(["## " + e["topic"], with_figures(e["description"]), _source_line(e)]))
    return "\n\n---\n\n".join(blocks)


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

    current, previous, shown_text = conversation_context(history)
    if current:
        # ถามต่อจากเรื่องที่คุยอยู่: ตัดคำถามต่อทิ้ง ดูว่ายังเหลือชื่อหัวข้อใหม่ไหม
        residual = _FOLLOW_WORDS.sub(" ", query).strip()
        mentioned = search(residual, limit=3) if residual else []
        current_topics = {e["topic"] for e in current}
        if _COMPARE_RE.search(query):
            pair = []
            if mentioned:
                # "แล้วมันต่างจาก INNER JOIN ยังไง" -> เรื่องที่คุยอยู่ + เรื่องที่ยกมาเทียบ
                # ("INNER JOIN กับ LEFT JOIN ต่างกันยังไง" ระบุครบทั้งสองฝั่ง = คำถามใหม่ ไม่เอาเรื่องเดิมมาปน)
                implicit = _BACKREF_RE.search(query) or (re.search(r"ต่างจาก|เทียบกับ", query) and len(mentioned) == 1)
                if implicit:
                    pair = current + [e for e in mentioned if e["topic"] not in current_topics]
            elif previous:    # "มันต่างกันยังไง" -> สองเรื่องล่าสุดที่คุยกัน
                pair = previous + current
            else:             # คุยมาเรื่องเดียว ยังไม่รู้ว่าจะเทียบกับอะไร
                return (f"ต้องการเทียบ **{_topic_name(current)}** กับเรื่องอะไรครับ "
                        'พิมพ์ชื่อเรื่องที่ต้องการเทียบ เช่น "ต่างจาก INNER JOIN ยังไง"')
            if len({e["topic"] for e in pair}) > 1:
                return "ตำราอธิบายแต่ละเรื่องไว้ดังนี้\n\n---\n\n" + render_topics(pair)
        last_answer = next((str(m.get("content") or "") for m in reversed(history)
                            if isinstance(m, dict) and m.get("role") == "assistant"), "")
        asking_examples = _EXAMPLE_RE.search(query) or (   # "มีอีกไหม" ต่อจากคำตอบตัวอย่าง
            last_answer.startswith("ตัวอย่างเพิ่มเติมเรื่อง") and _AGAIN_RE.search(query.strip())
            and not _RELATED_RE.search(query))
        if asking_examples and (not mentioned or {e["topic"] for e in mentioned} <= current_topics):
            return more_examples(current, shown_text)
        if _MORE_RE.search(query) and not mentioned:
            return related_topics(current, shown_text)

    entries = search(query, limit=3)
    if not entries and len(questions) > 1 and query.startswith(("แล้ว", "อธิบายต่อ")):
        entries = search(questions[-2] + " " + query, limit=3)
    if not entries:
        return NO_DATA
    return render_topics(entries)

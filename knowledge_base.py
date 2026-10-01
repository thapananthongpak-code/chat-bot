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


def _heading_matches(query):
    """พิมพ์หัวข้อในเล่มโดยไม่มีเลขหัวข้อ เช่น "โครงสร้างแฟ้มข้อมูลแบบเรียงลำดับ" "การทำนอมอลไลเซชัน" -> หัวข้อนั้น"""
    asked = {_term_key(t) for t in _asked_terms(query)} - {""}
    return [e for e in ENTRIES if not _is_meta(e["topic"]) and len(_term_key(_own_title(e))) >= 4
            and asked & {_term_key(_heading(e)), _term_key(_own_title(e))}]


def _special_topics(text):
    """คำถามพื้นฐานที่ชื่อหัวข้อตอบไม่ตรง จึงกำหนดหัวข้อไว้เอง"""
    text = text.lower().strip()
    if re.search(r"(?:what is sql\b|(?<![\w-])sql\s*(?:คืออะไร|ทำอะไรได้|ใช้ทำอะไร|มีกี่ประเภท|มีกี่แบบ|แบ่งเป็น)"
                 r"|ภาษา sql คือ|ความหมายของภาษา sql)", text):
        return [e for e in ENTRIES if e["topic"].startswith("8.1 ")][:1]
    # "JOIN คืออะไร" ถามคำสั่ง JOIN ทั่วไป: บทนำบทที่ 10 อธิบายการเชื่อมตาราง + ตารางรูปแบบ JOIN ทุกชนิดใน 10.2
    # (ไม่งั้นได้ "10.1 การเกิด CARTESIAN JOIN" ซึ่งเป็น JOIN ชนิดเดียว)
    if re.fullmatch(r"(คำสั่ง\s*)?join(\s+table)?", " ".join(_asked_terms(text)).strip()):
        return [e for e in ENTRIES if e["topic"].startswith(("บทที่ 10 ", "10.2 "))]
    return []


def search(query, limit=6, min_score=1.0):
    """Require topic evidence: a word in the body alone is not evidence the book explains it."""
    text = query.lower().strip()
    exact = [entry for entry in ENTRIES if entry["topic"].lower() == text]
    if exact:
        return exact[:limit]
    same = _heading_matches(query)
    if same:
        return same[:limit]
    # ระบุเลขหัวข้อมาตรง ๆ เช่น "7.5"
    num = re.search(r"(?<![\d.])(\d{1,2}\.\d{1,2})(?![\d.])", text)
    if num:
        by_num = [e for e in ENTRIES if e["topic"].startswith(num.group(1) + " ")]
        if by_num:
            return by_num[:1]
    special = _special_topics(text)
    if special:
        return special[:limit]

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


def _find_examples(terms, skip_topics, seen):
    found = []
    for order, e in enumerate(ENTRIES):
        if e["topic"] in skip_topics:
            continue
        for snippet in _example_snippets(e, terms):
            if re.sub(r"\s+", "", snippet) not in seen:
                # คำสั่ง SQL จริงก่อน, บทนำ/บทสรุป/แบบฝึกหัดไว้ท้าย, นอกนั้นตามลำดับในเล่ม
                rank = (0 if "```" in snippet else 1, 1 if _is_meta(e["topic"]) else 0, order)
                found.append((rank, e, snippet))
    found.sort(key=lambda f: f[0])
    return [(e, snippet) for _, e, snippet in found]


def more_examples(current, shown_text, focus_terms=()):
    """ตัวอย่างเรื่องที่คุยอยู่ จากหัวข้ออื่นในตำรา ครั้งละ 3 ตัวอย่าง ข้ามที่เคยแสดงแล้ว
    focus_terms = ศัพท์ที่ถามเมื่อคำตอบล่าสุดแสดงแค่บางส่วนของหัวข้อ ("ทูเพิล" ในหัวข้อ 4.4, "COUNT" ในหัวข้อ 9.10)
    หาตัวอย่างของศัพท์นั้นก่อน รวมส่วนที่ยังไม่ได้แสดงของหัวข้อเดิมด้วย"""
    seen = re.sub(r"\s+", "", shown_text)
    found, name = [], _topic_name(current)
    focus_terms = [t for t in focus_terms if 2 <= len(t) <= 30]
    if focus_terms:
        found = _find_examples(focus_terms, set(), seen)
        name = " / ".join(focus_terms) if found else name
    terms = [t for e in current for t in key_terms(e)]
    if not found and not terms:
        return f"เรื่อง **{name}** ในตำรามีตัวอย่างเท่าที่แสดงไปแล้วด้านบนครับ\n\n" + related_topics(current, shown_text, lead=False)
    if not found:
        found = _find_examples(terms, {e["topic"] for e in current}, seen)
    if not found:
        return (f"ตัวอย่างเรื่อง **{name}** ในตำรามีเท่าที่แสดงไปแล้วครับ\n\n"
                + related_topics(current, shown_text, lead=False))
    where = "ในตำรา" if any(e in current for e, _ in found) else "จากหัวข้ออื่นในตำรา"
    blocks = [f"ตัวอย่างเพิ่มเติมเรื่อง **{name}** {where}"]
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
    return render_plan([(e, None) for e in entries])


# ---------------------------------------------------------------- ตอบเฉพาะส่วนที่ถาม
# หัวข้อยาวมักอธิบายหลายเรื่อง เช่น 1.1 มีทั้งความหมายของข้อมูลและของสารสนเทศ ถาม "สารสนเทศคืออะไร"
# จึงควรได้เฉพาะย่อหน้าที่อธิบายสารสนเทศ (พร้อมตัวอย่าง/รูป/ตารางที่ประกอบ) ไม่ใช่ทั้งหัวข้อ
# ย่อหน้าที่แสดงยังเป็นข้อความจากตำราตรงตัวทุกตัวอักษร เพียงแต่ไม่แสดงย่อหน้าที่ไม่เกี่ยว
FOCUS_MIN_CHARS = 1500   # หัวข้อสั้นกว่านี้แสดงทั้งหัวข้อ ตัดแล้วไม่ได้อ่านง่ายขึ้น
BLOCK_CHARS = 1200       # นิยามยาวถึงนี้แล้ว หยุดที่ย่อหน้าถัดไป (ตาราง/รูปที่กำลังแสดงอยู่ยังแสดงจนครบ)
PARTIAL_NOTE = "แสดงเฉพาะส่วนที่ตอบคำถาม แตะเพื่ออ่านทั้งหัวข้อ"


def units(entry):
    """ย่อหน้าของหัวข้อ: บล็อกโค้ดทั้งก้อน หรือทีละบรรทัด (ไฟล์ความรู้เก็บหนึ่งย่อหน้าต่อบรรทัด)"""
    return [text for _, text in _blocks(entry["description"])]


# ศัพท์เดียวกันสะกดได้หลายแบบ (ในตำราเองก็สะกดไม่เหมือนกันทุกที่) แปลงเป็นแบบเดียวก่อนเทียบ
_SPELLINGS = [
    (r"เอ็?น[ทต]ิตี้?", "เอ็นทิตี้"),
    (r"แอ[ตทด]{0,2}ร?ิบิว[ตท]?์?", "แอตทริบิวต์"),
    (r"เร็?[คก]{1,2}อร์ด", "เรคอร์ด"),
    (r"ทู(?:เพิ้?ล|พิล|เปิล)", "ทูเพิล"),
    (r"คาร์ดิน[ัา]ล?ลิ[ตท][ีิ]้?", "คาร์ดินัลลิตี้"),
    (r"ซ[ุู][ปบ]?เปอร์คีย์", "ซุปเปอร์คีย์"),
    (r"ส[กค]ีมา", "สกีมา"),
    (r"ฟ[ิี][ลว]ด์", "ฟิลด์"),
    (r"ไบ[ตท]์", "ไบต์"),
    (r"นอร์?ม[ัอ]ลไลเซชั่?น", "นอมอลไลเซชัน"),
    (r"นอร์?ม[ัอ]ลฟอร์ม?", "นอมอลฟอร์ม"),
    (r"^ภาษา(?=\s*[a-z])", ""),                     # "ภาษา SQL" = "SQL"
]


def _term_key(text):
    """รูปมาตรฐานของศัพท์ ใช้เทียบศัพท์ในคำถามกับศัพท์ที่ตำรานิยาม"""
    text = text.lower().strip()
    for pattern, repl in _SPELLINGS:
        text = re.sub(pattern, repl, text)
    return re.sub(r"[\s\-_:;,.'\"“”()]+", "", text)


_NUM_MARK = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2})*)(?:\s*([.)])|\s)\s*")
_CAPTION = re.compile(r"^(ภาพที่|ตารางที่)\s*\d")
_EXPLAIN = re.compile(r"^จาก\s*(ภาพ|ตาราง)")
_NOT_TERM = re.compile(r"^(จาก|หมายเหตุ|ข้อใด|ตัวอย่าง|รูปแบบ|โครงสร้างคำสั่ง|โครงสร้างการ|ตาราง|ที่มา|ภาพที่|ขั้น|วิธี|"
                       r"สรุป|ประเภทคำสั่ง|[a-z_0-9(),.\s]+$)")
_INTRO_END = re.compile(r"(ต่อไปนี้|ดังนี้|ได้แก่|ดังรายละเอียด\S*|ประกอบด้วย|มีดังนี้|:)\s*$")


def _defined_terms(line):
    """ศัพท์ที่บรรทัดนี้นิยามไว้ คืน (ชื่อศัพท์ทุกแบบ, นิยามเต็ม?)
    - "ทูเพิล หมายถึง …" / "2) ฟิลด์ (Field) หมายถึง …" / "ภาษา SQL (Structured Query Language) เป็น…" -> นิยามเต็ม
    - "ดีกรี (Degree)" / "1. ภาษาสำหรับนิยามข้อมูล (Data Definition Language: DDL)" -> หัวเรื่องของศัพท์ เนื้อหาอยู่บรรทัดถัดไป"""
    text = _NUM_MARK.sub("", line).strip()
    m = re.match(r"(?P<th>[^()|:“”\"]{1,45}?)\s*(?:หรือ\s*)?\((?P<en>[A-Za-z][^()]{0,60})\)\s*(?P<rest>.*)$", text)
    if m and re.search(r"\d{4}|et al|&", m.group("en")):
        m = None                            # วงเล็บเป็นการอ้างอิง "(Petersen, 2018)" ไม่ใช่ชื่อศัพท์
    if m:
        th, en, rest = m.group("th").strip(), m.group("en"), m.group("rest")
        # "5) บิต (Bit) บิต เป็น…" / "…(DML) ภาษาสำหรับจัดการฐานข้อมูล เป็น…" ทวนชื่อศัพท์ก่อนนิยาม
        full = bool(re.match(r"(?:" + re.escape(th) + r"\s*)?(หมายถึง|คือ|เป็น|จะ|มี|ถือ)", rest))
        if rest and not full:
            return [], False
    else:
        m = re.match(r"(?P<th>[^()|:“”\"]{1,30}?)\s*(หมายถึง|คือ)\s", text)
        if not m:
            return [], False
        th, en, full = m.group("th").strip(), "", True
    if not th or _NOT_TERM.match(th) or len(th) > 40 or re.search(r"(?<!ความ)เป็น|คือ|หมายถึง", th):
        return [], False                    # "กระบวนการ 2NF เป็นการกำจัด (Partial Dependency)" เป็นประโยค ไม่ใช่ชื่อศัพท์
    names = [th] + [p.strip() for p in th.split("หรือ") if p.strip()]
    names += [p.strip() for p in re.split(r"[:,]| or ", en) if len(p.strip()) >= 2]
    if en:
        names.append(f"{th} ({en})")      # พิมพ์ทั้งชื่อไทยและอังกฤษตามหัวเรื่องในเล่ม
    return list(dict.fromkeys(n for n in names if n)), full


_DEFINITIONS = {"key": None, "index": {}}


def definitions():
    """ดัชนีศัพท์ที่ตำรานิยามไว้ในเนื้อหา: รูปมาตรฐานของศัพท์ -> [(หัวข้อ, เลขย่อหน้า, นิยามเต็ม?)]
    (หัวข้อตามสารบัญมีแค่ 172 ชื่อ แต่ศัพท์อย่างทูเพิล ดีกรี ฟิลด์ DDL นิยามไว้ในเนื้อหาของหัวข้ออื่น)"""
    if _DEFINITIONS["key"] is not ENTRIES:
        index = {}
        for e in ENTRIES:
            own = _own_title(e)
            for k, u in enumerate(units(e)):
                names, full = _defined_terms(u)
                if not names and k < 3 and own and re.match(re.escape(own) + r"\s*(หมายถึง|คือ|เป็น)", u):
                    names, full = [own], True       # "เหมืองข้อมูล เป็น…" ต้นหัวข้อ "11.4 เหมืองข้อมูล"
                for name in names:
                    key = _term_key(name)
                    if len(key) >= 2:
                        index.setdefault(key, []).append((e, k, full))
        # ชื่ออังกฤษในชื่อหัวข้อ "11.6 ปัญญาประดิษฐ์ (Artificial Intelligence: AI)" ใช้ถามแทนชื่อไทยได้
        for e in ENTRIES:
            thai = index.get(_term_key(_own_title(e)), [])
            for name in _title_names(e)[1:] if thai else []:
                key = _term_key(name)
                index[key] = index.get(key, []) + [h for h in thai if h not in index.get(key, [])]
        _DEFINITIONS.update(key=ENTRIES, index=index)
    return _DEFINITIONS["index"]


def definition_block(entry, start):
    """ย่อหน้าที่อธิบายศัพท์ซึ่งนิยามไว้ที่ย่อหน้า start: ตัวนิยาม + ตัวอย่าง รูป ตาราง โค้ด และรายการย่อยที่ตามมา
    หยุดเมื่อถึงศัพท์ถัดไป หัวเรื่องถัดไป หรือรูปใหม่ที่ไม่เกี่ยวกับศัพท์นี้"""
    us = units(entry)
    names, full = _defined_terms(us[start])
    if full and start > 0:
        prev_names, prev_full = _defined_terms(us[start - 1])
        if prev_names and not prev_full and {_term_key(n) for n in prev_names} & {_term_key(n) for n in names}:
            start -= 1          # หัวเรื่องของศัพท์ "ดีกรี (Degree)" อยู่บรรทัดก่อนนิยาม
            names, full = prev_names, False
    keys = {_term_key(n) for n in names}
    mark = _NUM_MARK.match(us[start])
    style = mark.group(2) if mark else None
    picked, size = [start], len(us[start])
    body_seen = full            # หัวเรื่องเฉย ๆ ต้องได้ย่อหน้าเนื้อหาอย่างน้อยหนึ่งย่อหน้า
    intro = bool(_INTRO_END.search(us[start]))
    example = in_list = explained = False
    for k in range(start + 1, len(us)):
        u = us[k].strip()
        if not u:
            continue
        num = _NUM_MARK.match(u)
        other_names, _ = _defined_terms(u)
        other = other_names and not ({_term_key(n) for n in other_names} & keys)
        enough = size >= BLOCK_CHARS
        if u.startswith("```") or " | " in u or re.match(r"^ที่มา\s*:?", u):
            pass                            # ตาราง โค้ด และที่มาของรูป ไปกับย่อหน้าก่อนหน้าเสมอ
        elif _CAPTION.match(u):
            if explained or (enough and not example):
                break                       # รูปใหม่หลังคำอธิบายรูปก่อนหน้า = เรื่องถัดไป
            in_list = False
        elif _EXPLAIN.match(u):
            explained, example, in_list = True, False, False
        elif num and style and num.group(2) == style and "." not in num.group(1):
            break                           # ข้อถัดไประดับเดียวกัน เช่น "2) ฟิลด์" ต่อจาก "1) แฟ้มข้อมูล"
        elif other and not (num and (intro or in_list) and not re.search(r"\([A-Za-z]", u)):
            break                           # ศัพท์อื่น (ยกเว้นข้อย่อยของรายการที่ศัพท์นี้เกริ่นไว้)
        elif num:
            if not (intro or in_list or not body_seen) or (enough and not in_list):
                break
            in_list = True
        elif re.match(r"ตัวอย่าง(ที่\s*\d|การ)", u) or (enough and not in_list):
            break                           # โจทย์ตัวอย่าง/การประยุกต์ใช้ เป็นเนื้อหาต่อยอด ไม่ใช่ความหมาย
        elif u.startswith("ตัวอย่าง"):
            example = True
        elif not body_seen:
            body_seen = True
        elif re.match(r"(กระบวนการ|ขั้นตอน|ประโยชน์|ข้อดี|ข้อเสีย|วิธี|การประยุกต์)", u) and _INTRO_END.search(u):
            break                           # เกริ่นรายการเรื่องใหม่ (ขั้นตอน/ประโยชน์) ไม่ใช่ความหมาย
        elif example or (in_list and len(u) <= 200):
            pass                            # ข้อมูลตัวอย่าง / คำอธิบายของข้อย่อย
        elif len(u) <= 40 or not any(key in _term_key(u) for key in keys):
            break                           # หัวเรื่องของเรื่องถัดไป หรือย่อหน้าที่ไม่ได้พูดถึงศัพท์นี้แล้ว
        else:
            in_list = False
        picked.append(k)
        size += len(u)
        intro = bool(_INTRO_END.search(u))
    return picked


def _asked_terms(query):
    """ศัพท์ที่ถาม: ตัดคำถาม/คำสุภาพทิ้ง ("สารสนเทศคืออะไรครับ" -> ["สารสนเทศ"], "COUNT ใช้ยังไง" -> ["COUNT"])
    ถามเทียบ ("ข้อมูลกับสารสนเทศต่างกันยังไง") ได้ศัพท์ทั้งสองฝั่ง"""
    text = re.sub(r"\s*(ใช้ยังไง|ใช้อย่างไร|ใช้ทำอะไร|ใช้งานยังไง|ใช้งานอย่างไร)", " ", query)
    text = re.sub(r"^\s*(วิธีใช้งาน|วิธีใช้|การใช้งาน)\s*", " ", text)
    text = re.sub(r"คืออะไร|หมายถึงอะไร|แปลว่าอะไร|อะไรคือ|หมายถึง|แปลว่า|คือ|ความหมายของ|ความหมาย|"
                  r"ช่วยอธิบาย|อธิบาย|ช่วยบอก|บอกหน่อย|อยากรู้ว่า|อยากรู้|อยากทราบ|สงสัยว่า|"
                  r"what\s+is|what\s+are|what's|define|definition\s+of|meaning\s+of|"
                  r"ความแตกต่างระหว่าง|ความแตกต่าง|แตกต่างกัน|ต่างกัน|ต่างจาก|เปรียบเทียบ|เทียบ|ยังไง|อย่างไร|"
                  r"ครับ|คับ|ค่ะ|คะ|นะ|จ้า|หน่อย|[?？!]", " ", text, flags=re.I)
    parts = re.split(r"\s+กับ\s*|กับ|\s+และ\s+|\s+vs\.?\s+|\s*/\s*|,", text) if _COMPARE_RE.search(query) else [text]
    return [p.strip() for p in parts if _term_key(p)]


_DEFINE_RE = re.compile(r"คือ|หมายถึง|แปลว่า|ความหมาย|what\s+is|what's|define|meaning|ต่างกัน|แตกต่าง|ต่างจาก|เทียบ", re.I)


def find_definition(term, prefer=()):
    """ย่อหน้าที่ตำรานิยามศัพท์นี้ไว้ดีที่สุด คืน (หัวข้อ, เลขย่อหน้า, นิยามเต็ม?) หรือ None
    ลำดับ: นิยามเต็มก่อนหัวเรื่องเฉย ๆ, หัวข้อที่ชื่อมีศัพท์นี้หรือค้นเจอจากชื่อหัวข้อก่อน, บทสรุป/แบบฝึกหัดทีหลัง,
    นอกนั้นเอาที่นิยามไว้ก่อนในเล่ม ถ้าไม่มีนิยามเต็มของศัพท์นี้ ใช้นิยามเต็มในหัวข้อที่ค้นเจอซึ่งชื่อศัพท์มีคำที่ถาม
    (ถาม "ฐานข้อมูล" ได้นิยาม "ระบบฐานข้อมูล" ในหัวข้อ 2.2 แทนป้ายในรูป "ฐานข้อมูล (DBMS)")"""
    key = _term_key(term)
    # เทียบด้วยชื่อหัวข้อ ไม่ใช่ตัวอ็อบเจกต์ (ENTRIES โหลดใหม่ทุกคำถาม คำถามที่มาพร้อมกันอาจถือคนละชุด)
    order = {e["topic"]: n for n, e in enumerate(ENTRIES)}
    preferred = {e["topic"] for e in prefer}
    hits = definitions().get(key, [])
    if not any(full and not _is_meta(e["topic"]) for e, _, full in hits):
        near = [(e, k, full) for other, found in definitions().items() if key in other
                for e, k, full in found if full and e["topic"] in preferred and not _is_meta(e["topic"])]
        hits = near or hits
    if not hits:
        return None
    return min(hits, key=lambda h: (_is_meta(h[0]["topic"]), not h[2],
                                    key not in _term_key(h[0]["topic"]) and h[0]["topic"] not in preferred,
                                    order.get(h[0]["topic"], 0), h[1]))


def _heading(entry):
    """ชื่อหัวข้อตามที่พิมพ์ในเล่มโดยไม่มีเลขหัวข้อ: "4.5 ประเภทของคีย์ · 3. คีย์หลัก (Primary Key)" -> "คีย์หลัก (Primary Key)" """
    return re.sub(r"^(ภาคผนวก [กข] )?(\d+\.)+\d*\s*", "", entry["topic"].split(" · ")[-1]).strip()


def _own_title(entry):
    """ชื่อหัวข้อไม่เอาเลขหัวข้อ ชื่อหัวข้อหลัก และคำอธิบายในวงเล็บ: "4.5 ประเภทของคีย์ · 3. คีย์หลัก (Primary Key)" -> "คีย์หลัก" """
    return re.sub(r"\s*\(.*$", "", _heading(entry)).strip()


def _title_names(entry):
    """ชื่อไทยของหัวข้อ + ชื่ออังกฤษในวงเล็บท้ายชื่อ: "11.6 ปัญญาประดิษฐ์ (Artificial Intelligence: AI)"
    -> ["ปัญญาประดิษฐ์", "Artificial Intelligence", "AI"]"""
    en = re.search(r"\(([A-Za-z][^()]*)\)\s*$", entry["topic"].split(" · ")[-1])
    names = [_own_title(entry)] + (re.split(r"[:,]", en.group(1)) if en else [])
    return [n.strip() for n in names if len(_term_key(n)) >= 2]


def asks_meaning(query):
    """ถามความหมาย/ความต่าง ("X คืออะไร", "X กับ Y ต่างกันยังไง") หรือพิมพ์แค่ชื่อศัพท์ที่ตำรานิยามไว้ ("ทูเพิล")"""
    terms = _asked_terms(query)
    return bool(_DEFINE_RE.search(query)) or (len(terms) == 1 and _term_key(terms[0]) in definitions())


def definition_blocks(query, entry):
    """ย่อหน้าที่หัวข้อนี้นิยามศัพท์ที่ถาม (เฉพาะคำถามความหมาย) หรือ [] ถ้าหัวข้อนี้ไม่ได้นิยามศัพท์นั้น"""
    if not asks_meaning(query):
        return []
    picked = set()
    for term in _asked_terms(query):
        hits = [h for h in definitions().get(_term_key(term), []) if h[0]["topic"] == entry["topic"]]
        if hits:
            e, k, _ = min(hits, key=lambda h: (not h[2], h[1]))
            picked |= set(definition_block(e, k))
    return sorted(picked)


def names_topic(query):
    """ถามด้วยชื่อหัวข้อเต็ม เลขหัวข้อ (7.5) หรือบท (แบบฝึกหัดบทที่ 7) = ต้องการทั้งหัวข้อนั้น ไม่ต้องตีความ"""
    text = query.lower().strip()
    return (any(e["topic"].lower() == text for e in ENTRIES)
            or bool(re.search(r"(?<![\d.])\d{1,2}\.\d{1,2}(?![\d.])|บทที่|ภาคผนวก", text)))


def plan_answer(query):
    """เลือกหัวข้อและย่อหน้าที่ตอบคำถาม โดยไม่ใช้ AI: [(หัวข้อ, เลขย่อหน้า หรือ None = ทั้งหัวข้อ)]
    ถามความหมายของศัพท์ -> เฉพาะย่อหน้าที่นิยามศัพท์นั้น (ถ้าหัวข้อยาว), ถามชื่อหัวข้อ/เลขหัวข้อ/อย่างอื่น -> ทั้งหัวข้อ"""
    return _plan(query)[0]


def _plan(query):
    """(แผนคำตอบ, มั่นใจไหม) — มั่นใจเมื่อถามด้วยชื่อ/เลขหัวข้อ, ศัพท์ที่ตำรานิยามไว้ หรือหัวเรื่องย่อยตรงตัว
    ไม่มั่นใจ = ได้หัวข้อจากคำที่ตรงกับชื่อหัวข้อเท่านั้น ซึ่งพลาดได้กับคำถามที่คนพิมพ์เอง"""
    entries = search(query, limit=3)
    terms = _asked_terms(query)
    whole = [(e, None) for e in entries]
    if names_topic(query) or not terms:
        return whole, bool(entries) and names_topic(query)
    if _special_topics(query) and not asks_meaning(query):
        return whole, True             # "SQL แบ่งเป็นกี่ประเภท" "JOIN" กำหนดหัวข้อไว้แล้ว
    plan, all_found = _meaning_plan(terms, entries) if asks_meaning(query) else ([], False)
    if plan and all_found:
        return plan, True
    if len(terms) > 1 and len(entries) >= len(terms) and _COMPARE_RE.search(query):
        return whole, True             # "INNER JOIN กับ LEFT JOIN ต่างกันยังไง" ค้นเจอครบทุกฝั่งจากชื่อหัวข้อ
    if _heading_matches(query):        # พิมพ์ชื่อหัวข้อในเล่ม (ไม่มีเลข) -> ทั้งหัวข้อ
        return whole, True
    sub = _subheading_plan(terms[0], entries) if len(terms) == 1 else []
    if sub:
        return sub, True
    # คำถามมีชื่อหัวข้อสั้นที่ค้นเจอเป็นอันดับแรกอยู่ทั้งชื่อ ("ทำไมต้องมีคีย์หลัก" -> "คีย์หลัก (Primary Key)")
    # แสดงทั้งหัวข้อได้โดยไม่เกินคำถาม ไม่ต้องให้ AI ตีความ (AI เคยเลือก "ซุปเปอร์คีย์" แทน)
    if len(entries) == 1 and len(entries[0]["description"]) < FOCUS_MIN_CHARS \
            and len(_own_title(entries[0])) >= 4 and _term_key(_own_title(entries[0])) in _term_key(query):
        return whole, True
    # ถามประเภท วิธีใช้ ("GROUP BY ใช้ยังไง") หรือคำที่ตรงกับชื่อหัวข้อบางส่วน -> ทั้งหัวข้อ
    return plan or whole, False


_SUBNUM = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{1,2}\s")   # หัวเรื่องระดับที่สามในเล่ม "9.10.3 ฟังก์ชัน COUNT()…"
_CATEGORY = r"(ข้อดี|ข้อเสีย|ข้อจำกัด|ประเภท|ชนิด|คุณสมบัติ|ความหมาย|ตัวอย่าง|ลักษณะ|ประโยชน์|วิธี|ขั้นตอน|สรุป)"


def _is_subheading(us, k):
    """หัวเรื่องย่อยในเนื้อหา: "9.10.3 ฟังก์ชัน COUNT() การนับจำนวน" หรือบรรทัดสั้นที่ตามด้วยย่อหน้าเนื้อหา
    เช่น "ข้อดีของแบบจำลองฐานข้อมูลเชิงสัมพันธ์" (ป้ายในรูปมักเป็นบรรทัดสั้นติดกันหลายบรรทัด จึงไม่นับ)"""
    u = us[k].strip()
    if _SUBNUM.match(u):
        return True
    if (not 4 <= len(u) <= 70 or " | " in u or u.startswith("```") or _CAPTION.match(u) or _EXPLAIN.match(u)
            or u.startswith("ที่มา") or _INTRO_END.search(u) or _NUM_MARK.match(u)):
        return False
    nxt = next((x.strip() for x in us[k + 1:] if x.strip()), "")
    return len(nxt) >= len(u) + 15 or bool(_NUM_MARK.match(nxt) or _INTRO_END.search(nxt))


def subheading_block(entry, k):
    """หัวเรื่องย่อยที่ย่อหน้า k จนถึงหัวเรื่องถัดไประดับเดียวกัน
    หัวเรื่องที่พูดถึงเรื่องเดียวกันและไม่ได้ขึ้นต้นด้วยข้อดี/ประเภท/ตัวอย่าง… เป็นหัวข้อย่อยของมัน
    ("ประเภทของแอตทริบิวต์" มี "คีย์แอตทริบิวต์ (Key Attribute)" เป็นหัวข้อย่อย แต่ "ข้อดีของ X" จบที่ "ข้อจำกัดของ X")"""
    us = units(entry)
    head = us[k].strip()
    subject = _term_key(re.sub(r"^" + _CATEGORY + r"(ของ|ที่)?", "", head))
    picked = [k]
    for j in range(k + 1, len(us)):
        u = us[j].strip()
        if _SUBNUM.match(head):
            if _SUBNUM.match(u):
                break
        elif _is_subheading(us, j) and (re.match(_CATEGORY, u) or not subject or subject not in _term_key(u)):
            break
        picked.append(j)
    return picked


_SUBHEADINGS = {"key": None, "index": {}}


def subheadings():
    """ดัชนีหัวเรื่องย่อยในเนื้อหา: รูปมาตรฐานของหัวเรื่อง (ไม่เอาเลข 9.10.3) -> [(หัวข้อ, เลขย่อหน้า)]"""
    if _SUBHEADINGS["key"] is not ENTRIES:
        index = {}
        for e in ENTRIES:
            us = units(e)
            for k in range(len(us)):
                if _is_subheading(us, k):
                    key = _term_key(_SUBNUM.sub("", us[k].strip()))
                    if len(key) >= 6:
                        index.setdefault(key, []).append((e, k))
        _SUBHEADINGS.update(key=ENTRIES, index=index)
    return _SUBHEADINGS["index"]


def _subheading_plan(term, entries):
    """ถามหัวเรื่องย่อยในเนื้อหา ("ข้อดีของแบบจำลองฐานข้อมูลเชิงสัมพันธ์", "คุณสมบัติของรีเลชันที่สำคัญ")
    หรือศัพท์ที่เป็นหัวเรื่องระดับที่สามของหัวข้อที่ค้นเจอ ("COUNT ใช้ยังไง" -> "9.10.3 ฟังก์ชัน COUNT()")
    -> เฉพาะส่วนนั้นของหัวข้อยาว"""
    key = _term_key(term)
    hits = [(e, k) for e, k in subheadings().get(key, [])
            if len(e["description"]) >= FOCUS_MIN_CHARS and not _is_meta(e["topic"])]
    hits.sort(key=lambda h: all(h[0]["topic"] != e["topic"] for e in entries))   # หัวข้อที่ค้นเจอจากชื่อก่อน
    if not hits and entries and len(entries[0]["description"]) >= FOCUS_MIN_CHARS and len(key) >= 3:
        us = units(entries[0])
        found = [k for k, u in enumerate(us) if _SUBNUM.match(u.strip()) and key in _term_key(u)]
        if len(found) == 1:
            hits = [(entries[0], found[0])]
    if not hits:
        return []
    e, k = hits[0]
    block = subheading_block(e, k)
    if block[-1] == len(units(e)) - 1 and len(section_parts(e)) > 1:
        return [(e, None)]      # "ประเภทของเอ็นทิตี้" เป็นหัวเรื่องท้ายหัวข้อ เนื้อหาอยู่ในหัวข้อย่อยที่แบ่งไว้ทุกส่วน
    return [(e, block)]


def _meaning_plan(terms, entries):
    """ถามความหมาย: ย่อหน้าที่ตำรานิยามแต่ละศัพท์ (หัวข้อยาว) หรือทั้งหัวข้อ (หัวข้อสั้น/หัวข้อที่ชื่อคือศัพท์นั้น)"""
    plan = []
    for term in terms:
        # หัวข้อที่ชื่อคือศัพท์นี้ ("5.3 เอ็นทิตี้") หรือเป็นหัวข้อความหมายของศัพท์นี้
        # ("5.1 ความหมายและความเป็นมา (บทที่ 5 … (ER Diagram))") เชื่อได้กว่าประโยคที่แค่หน้าตาเหมือนนิยาม
        # (เช่น "6.2.2 การแปลง (ER-Diagram) เป็นรีเลชัน…" ซึ่งพูดถึงการแปลง ไม่ใช่ความหมายของ ER Diagram)
        titled = next((e for e in entries if _term_key(term) in {_term_key(n) for n in _title_names(e)}
                       or ("ความหมาย" in e["topic"] and _term_key(term) in _term_key(e["topic"]))), None)
        found = find_definition(term, prefer=entries)
        if found and _is_meta(found[0]["topic"]) and any(not _is_meta(e["topic"]) for e in entries):
            found = None                    # นิยามในแบบฝึกหัด/บทสรุป ใช้เมื่อไม่มีหัวข้อเนื้อหาที่ตอบได้เท่านั้น
        if titled and (not found or found[0] is not titled):
            # หัวข้อชื่อตรงกับศัพท์ เช่น "5.3 เอ็นทิตี้": ตอบส่วนนำของหัวข้อ ไม่ต้องรวมหัวข้อย่อยทุกประเภท
            plan.append((titled, [] if len(titled["description"]) < FOCUS_MIN_CHARS else None))
        elif found:
            e, k, _ = found
            plan.append((e, definition_block(e, k) if len(e["description"]) >= FOCUS_MIN_CHARS else []))
    # ศัพท์สองคำในหัวข้อเดียวกัน (ข้อมูล / สารสนเทศ ใน 1.1) รวมเป็นคำตอบเดียว
    merged = {}
    for e, picked in plan:
        t = e["topic"]
        if t in merged and merged[t][1] is not None and picked:
            merged[t] = (e, sorted(set(merged[t][1]) | set(picked)))
        else:
            merged.setdefault(t, (e, picked))
    return list(merged.values()), len(plan) == len(terms)


def _shows_terms(plan, terms):
    """ข้อความที่จะแสดงตามแผนนี้มีศัพท์ที่ถามอยู่จริงไหม (เทียบแบบไม่สนช่องว่าง/ตัวพิมพ์/การสะกดที่ต่างกัน)"""
    keys = {_term_key(t) for t in terms} - {""}
    shown = []
    for e, picked in plan:
        if picked is None:
            shown += [u for p in section_parts(e) for u in units(p)]
        else:
            shown += units(e) if not picked else [units(e)[k] for k in picked]
    # ต้องอยู่ในย่อหน้าเนื้อหา ไม่ใช่แค่ข้อในรายการ/ช่องในตาราง ("- Sql Injection" ในตาราง 12.2 ไม่ได้อธิบายว่าคืออะไร)
    text = _term_key(" ".join(u for u in shown if not u.lstrip().startswith("-") and " | " not in u))
    return any(k in text for k in keys)


def render_plan(plan):
    """plan: [(หัวข้อ, ย่อหน้าที่เลือก)] ย่อหน้าที่เลือก None = ทั้งหัวข้อรวมหัวข้อย่อยทุกส่วน,
    [] = ทั้งหัวข้อเฉพาะส่วนนี้ (ไม่รวมหัวข้อย่อย), [เลข...] = เฉพาะย่อหน้าเหล่านั้น ตามลำดับในเล่ม"""
    blocks = []
    whole = {entry["topic"] for entry, picked in plan if picked is None}
    shown = set()
    for entry, picked in plan:
        main = entry["topic"].split(" · ")[0]
        if entry["topic"] in shown or (main != entry["topic"] and main in whole):
            continue                           # แสดงไปแล้ว หรือรวมอยู่ในหัวข้อหลักที่แสดงครบทุกส่วน
        shown.add(entry["topic"])
        parts = section_parts(entry) if picked is None else [entry]
        for e in parts:
            us = units(e)
            partial = bool(picked) and len(set(picked)) < len(us)
            text = "\n".join(us[k] for k in sorted(set(picked))) if partial else e["description"]
            # บท + เลขหน้า มาจากส่วน "แหล่งอ้างอิง" ของหัวข้อในไฟล์ (ตรวจกับสารบัญและหน้า PDF แล้ว)
            block = ["## " + e["topic"], with_figures(text), _source_line(e)]
            more = [e["topic"]] if partial else []
            if picked is not None and len(section_parts(e)) > 1:
                more = [e["topic"]]            # หัวข้อย่อยที่ไม่ได้แสดง อ่านต่อได้จากหัวข้อหลัก
            if more:
                block.append(PARTIAL_NOTE + "\n" + "\n".join(f"[[ถาม:{t}]]" for t in more))
            blocks.append("\n\n".join(block))
    return "\n\n---\n\n".join(blocks)


def question_key(query):
    """รูปมาตรฐานของคำถาม: พิมพ์ต่างกันเล็กน้อยถือเป็นคำถามเดียวกัน ได้คำตอบเดียวกัน
    ("SQL คืออะไร", "sql คืออะไรครับ?", "sql  คือ อะไร" -> "sql คืออะไร")"""
    text = re.sub(r"[\s?？!.,ๆ\"'“”]+", " ", query.lower()).strip()
    text = re.sub(r"(?<=[฀-๿]) (?=[฀-๿])", "", text)          # ช่องว่างระหว่างคำไทยไม่มีความหมาย
    return re.sub(r"\s*(ครับ|คับ|ค่ะ|คะ|นะคะ|นะครับ|นะ|จ้า|จ้ะ|หน่อย)+$", "", text).strip()


def plan_to_json(plan):
    return [{"topic": e["topic"], "picked": picked} for e, picked in plan]


def plan_from_json(items):
    """แผนที่จำไว้ -> แผนของตำราที่โหลดอยู่ หรือ None ถ้าอ้างหัวข้อ/ย่อหน้าที่ไม่มีแล้ว"""
    by_topic = {e["topic"]: e for e in ENTRIES}
    plan = []
    for item in items if isinstance(items, list) else []:
        e = by_topic.get(item.get("topic")) if isinstance(item, dict) else None
        picked = item.get("picked") if e else None
        if e is None or not (picked is None or (isinstance(picked, list) and
                                                all(isinstance(k, int) and 0 <= k < len(units(e)) for k in picked))):
            return None
        plan.append((e, picked))
    return plan if isinstance(items, list) else None


def _decide(query, plan, selector, memory):
    """คำถามที่ต้องตีความ (วิธีค้นเองไม่มั่นใจ):
    1) เคยตอบคำถามนี้แล้ว -> คำตอบเดิม (AI ตอบไม่เหมือนเดิมทุกครั้ง จึงต้องจำ ไม่ถาม AI ซ้ำ)
    2) ยังไม่เคย -> ให้ AI ช่วยเลือก แล้วจำคำตอบที่แสดงไว้ (รวมกรณีที่ AI ใช้ไม่ได้และตอบด้วยวิธีค้นเอง)
    3) จำเพิ่มไม่ได้ (บน Vercel) -> ไม่เรียก AI สด ใช้วิธีค้นเองซึ่งได้ผลเดิมทุกครั้ง"""
    book = DOCUMENT_META.get("markdown_sha256")
    key = question_key(query)
    if memory is not None:
        stored = memory.get(key, book)
        restored = plan_from_json(stored.get("plan")) if isinstance(stored, dict) else None
        if restored is not None:
            return restored
        if not memory.writable:
            return plan
    if not selector:
        return plan
    chosen = selector(query)
    # ค้นเองไม่เจอเลยและถามความหมายของศัพท์ ("MySQL คืออะไร"): ย่อหน้าที่ AI เลือกต้องมีศัพท์นั้นอยู่จริง
    # ไม่งั้นเป็นแค่หัวข้อที่เรื่องใกล้เคียง (ตำราไม่ได้อธิบายศัพท์นั้น) ตอบว่าไม่มีข้อมูลตามเดิม
    # AI เลือกได้แค่แบบฝึกหัด/บทสรุปทั้งที่ไม่ได้ถามถึง (เคยสุ่มพลาดครั้งหนึ่ง) ใช้ผลค้นเองแทน
    only_meta = chosen and plan and all(e["topic"].startswith(("แบบฝึกหัด", "บทสรุป")) for e, _ in chosen) \
        and not any(k in query.lower() for k in _META_WORDS)
    if chosen and not only_meta and (plan or not asks_meaning(query) or _shows_terms(chosen, _asked_terms(query))):
        plan, source = chosen, "AI"
    elif chosen is None:
        source = "ค้นเอง (เรียก AI ไม่สำเร็จ)"
    else:
        source = "ค้นเอง (AI ไม่พบหรือผลไม่ผ่านการตรวจ)"
    if memory is not None:
        memory.put(key, book, plan_to_json(plan), source)
    return plan


def answer_from_dataset(history, selector=None, memory=None):
    """No generated prose: render only stored fields, with traceable provenance.
    selector (ไม่บังคับ) = ตัวช่วยเลือกหัวข้อ/ย่อหน้าด้วย AI (ai_select.plan_answer) คืนแผนแบบ plan_answer
    หรือ None/[] เมื่อใช้ไม่ได้หรือไม่เจอ ซึ่งจะกลับมาใช้วิธีค้นแบบเดิม
    memory (ไม่บังคับ) = answer_memory.AnswerMemory จำคำตอบของคำถามที่ต้องตีความ ถามซ้ำได้คำตอบเดิมเสมอ"""
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
            # คำตอบก่อนหน้าแสดงเฉพาะส่วน: ตัวอย่างของศัพท์ที่ถาม ไม่ใช่ของทั้งหัวข้อ
            asked = _asked_terms(questions[-2]) if PARTIAL_NOTE in last_answer and len(questions) > 1 else []
            return more_examples(current, shown_text, focus_terms=asked)
        if _MORE_RE.search(query) and not mentioned:
            # คำตอบล่าสุดแสดงแค่ส่วนที่ถาม: "อธิบายเพิ่ม" "มีอีกไหม" = อ่านทั้งหัวข้อ, "…ที่เกี่ยวข้อง" = หัวข้ออื่น
            if PARTIAL_NOTE in last_answer and not re.search(r"เกี่ยว", query):
                return render_topics(current)
            return related_topics(current, shown_text)

    # วิธีค้นเองมั่นใจ (ชื่อหัวข้อ, ศัพท์ที่ตำรานิยามไว้, หัวเรื่องย่อยตรงตัว) ได้ผลเดิมทุกครั้ง ไม่ต้องใช้ AI
    # นอกนั้นใช้คำตอบที่จำไว้ หรือให้ AI ช่วยตีความแล้วจำไว้
    plan, sure = _plan(query)
    if not sure:
        plan = _decide(query, plan, selector, memory)
    if not plan and len(questions) > 1 and query.startswith(("แล้ว", "อธิบายต่อ")):
        plan = plan_answer(questions[-2] + " " + query)
    if not plan:
        return NO_DATA
    return render_plan(plan)

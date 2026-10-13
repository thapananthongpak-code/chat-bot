"""ให้ AI (Gemini) ช่วยอ่านคำถามที่คนพิมพ์เอง แล้วเลือกว่าหัวข้อและย่อหน้าไหนในตำราตอบคำถามนั้น

AI ไม่ได้เขียนคำตอบ: AI ส่งกลับมาแค่ "เลขหัวข้อ" กับ "เลขย่อหน้า" ระบบตรวจว่าเป็นเลขที่มีอยู่จริง
แล้วนำข้อความจากตำรามาแสดงตรงตัว (knowledge_base.render_plan) AI จึงเติมคำหรือแต่งเนื้อหาเองไม่ได้
ไม่ได้ตั้ง GEMINI_API_KEY หรือเรียก AI ไม่สำเร็จ (โควตาเต็ม, เน็ตหลุด, ช้าเกิน) -> คืน None ให้ใช้วิธีค้นแบบเดิม
AI ตอบไม่เหมือนเดิมทุกครั้ง: ผลที่ได้ถูกจำไว้ใน answer_memory.py ถามซ้ำจึงได้คำตอบเดิม
"""

import json
import os
import re
import ssl
import urllib.error
import urllib.request

import knowledge_base as kb

try:   # Python จาก python.org บน macOS ไม่มีใบรับรอง CA ติดมา เรียก HTTPS ไม่ผ่านถ้าไม่ใช้ certifi
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL = ssl.create_default_context()

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# flash-lite ตอบใน ~1 วินาทีเมื่อปิดการคิดยาว (thinkingLevel minimal) และโควตาฟรีมากกว่ารุ่น flash
DEFAULT_MODEL = "gemini-3.5-flash-lite"
TIMEOUT = 15          # วินาทีต่อการเรียกหนึ่งครั้ง ช้ากว่านี้ใช้วิธีค้นแบบเดิมแทน
MAX_SECTIONS = 3
AI_FOCUS_MIN_CHARS = 600   # หัวข้อสั้นกว่านี้แสดงทั้งหัวข้อได้เลย ไม่ต้องให้ AI เลือกประโยค
PARA_PREVIEW = 300    # AI เห็นแต่ละย่อหน้าแค่ช่วงต้น พอให้รู้ว่าพูดเรื่องอะไร (ประหยัดเวลาและโควตา)


def enabled():
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def model_label():
    """ชื่อรุ่น AI ที่ใช้อยู่ (บันทึกไว้คู่กับคำตอบที่จำ)"""
    return (os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL) if enabled() else ""


def _generate(system, prompt, schema):
    """เรียก Gemini ให้ตอบเป็น JSON ตาม schema"""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
    config = {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema}
    if "lite" in model:
        config["thinkingConfig"] = {"thinkingLevel": "minimal"}
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": config}
    req = urllib.request.Request(API_URL.format(model=model), data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_SSL) as resp:
        data = json.load(resp)
    return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])


def _schema(name, item_type):
    return {"type": "OBJECT", "properties": {name: {"type": "ARRAY", "items": {"type": item_type}}}, "required": [name]}


ROUTE_SYSTEM = """You map a student's question to sections of a Thai textbook on database systems and SQL.
You never answer the question yourself; you only return section ids.
Input: the question, then the list of sections as "id. title — นิยาม: terms defined inside — หัวเรื่อง: sub-headings inside".
Return the ids of the sections whose text answers the question, best first, at most 3.
- Choose the section that explains the concept being asked. A section that only mentions the same words does not count.
- Terms listed after "นิยาม" are defined inside that section, so for "X คืออะไร" choose the section that defines X even if its title is broader.
- A question about two things ("X กับ Y ต่างกันยังไง") needs the sections for both X and Y.
- Prefer content sections over chapter introductions (บทนำ), summaries (บทสรุป) and exercises (แบบฝึกหัด) unless the question asks for those.
- If a long section is split into parts ("หัวข้อ · 1. …") and the question asks about one part, choose that part.
- Students use everyday words instead of the book's terms (e.g. "เชื่อมสองตาราง" means JOIN, "ตั้งชื่อชั่วคราวให้คอลัมน์" means ALIASES). Match by meaning, using the sub-headings (หัวเรื่อง) as well as the titles.
- The book teaches with Microsoft Access (appendix ข and the security chapter show how to do things in Access), so Access how-to questions are covered.
- Return an empty list only when no section explains what is asked: unrelated subjects, other programming languages, other database products (MySQL, Oracle…) or SQL features that no section covers (transactions, stored procedures, triggers, CTE…). Do not guess."""

FOCUS_SYSTEM = """You pick sentences from a Thai textbook on database systems that answer a student's question.
You never write the answer yourself; you only return labels.
Input: the question and its type, then the paragraphs of one or more sections. Short paragraphs are labelled [section.paragraph].
Long paragraphs are split into sentences labelled [section.paragraph.sentence].
Return the labels the student needs to read to get the answer, and nothing more. The shorter the better, as long as the answer is complete:
- choose the sentences that directly answer what is asked; a paragraph may be only partly relevant, so pick its sentences one by one;
- add the table, SQL block or figure caption right after a chosen sentence only when that sentence introduces it ("ดังตารางต่อไปนี้", "ดังนี้");
- leave out other concepts, general introductions, repeated explanations and examples the question does not ask for;
- if the question asks for a whole list (types, steps, advantages, commands…), include every item of that list and each item's explanation;
- never return more than about 1,500 characters of text in total;
- if nothing answers the question, return an empty list."""


def _catalog():
    """รายชื่อหัวข้อทั้งเล่ม พร้อมศัพท์ที่แต่ละหัวข้อนิยามไว้และหัวเรื่องย่อยในเนื้อหา
    (ช่วยให้ AI รู้ว่าทูเพิลอยู่ในหัวข้อ 4.4 และวิธีตั้ง/ลบรหัสผ่านฐานข้อมูล Access อยู่ในหัวข้อ 12.5)"""
    terms, heads = {}, {}
    for hits in kb.definitions().values():
        for e, k, _ in hits:
            names, _ = kb._defined_terms(kb.units(e)[k])
            if names and names[0] not in terms.setdefault(e["topic"], []):
                terms[e["topic"]].append(names[0])
    for hits in kb.subheadings().values():
        for e, k in hits:
            u = kb.units(e)[k].strip()
            # เฉพาะหัวเรื่องภาษาไทย ไม่เอาบรรทัดโค้ด (Me.TxtPassword.SetFocus) และป้ายในรูป
            if (re.match(r"[฀-๿]", u) and 6 <= len(u) <= 60 and not re.search(r"[=;{}]|\.\w", u)
                    and u not in heads.setdefault(e["topic"], [])):
                heads[e["topic"]].append(u)
    lines = []
    for i, e in enumerate(kb.ENTRIES):
        t, h = terms.get(e["topic"], []), heads.get(e["topic"], [])
        lines.append(f"{i}. {e['topic']}" + (" — นิยาม: " + ", ".join(t[:12]) if t else "")
                     + (" — หัวเรื่อง: " + "; ".join(h[:8]) if h else ""))
    return "\n".join(lines)


def _preview(text):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= PARA_PREVIEW else text[:PARA_PREVIEW] + "…"


def attach(us, picked):
    """ย่อหน้าที่ต้องไปด้วยกันแม้ AI ไม่ได้เลือก (ตาราง/โค้ด/รูปที่เกริ่นไว้) ดู knowledge_base.attach_units"""
    return kb.attach_units(us, picked)


def route(query):
    """เลขหัวข้อที่ AI เลือก (ตรวจแล้วว่ามีจริง) — [] = AI บอกว่าตำราไม่มีเรื่องนี้"""
    got = _generate(ROUTE_SYSTEM, f"คำถาม: {query}\n\nหัวข้อในตำรา:\n{_catalog()}", _schema("sections", "INTEGER"))
    ids = [i for i in got.get("sections", []) if isinstance(i, int) and 0 <= i < len(kb.ENTRIES)]
    return list(dict.fromkeys(ids))[:MAX_SECTIONS]


def _numbered(i, us):
    """ย่อหน้าของหัวข้อ i พร้อมเลขกำกับ: ย่อหน้าร้อยแก้วยาวแบ่งเป็นประโยค [หัวข้อ.ย่อหน้า.ประโยค] ที่เหลือเป็นก้อนเดียว"""
    lines = []
    for k, u in enumerate(us):
        segs = kb.segments(u)
        if len(segs) > 1:
            lines += [f"[{i}.{k}.{n}] {re.sub(chr(10), ' ', u[a:b]).strip()}" for n, (a, b) in enumerate(segs, 1)]
        else:
            lines.append(f"[{i}.{k}] {_preview(u)}")
    return "\n".join(lines)


def focus(query, ids, qtype="topic"):
    """ย่อหน้า/ประโยคที่ AI เลือกในแต่ละหัวข้อ {เลขหัวข้อ: [เลขย่อหน้า หรือช่วง (ย่อหน้า, เริ่ม, จบ)]} (ตรวจแล้วว่ามีจริง)
    ถ้าเลือกครบทุกประโยคของย่อหน้า นับเป็นทั้งย่อหน้า ประโยคที่ติดกันรวมเป็นช่วงเดียว"""
    blocks = [f"## {kb.ENTRIES[i]['topic']}\n" + _numbered(i, kb.units(kb.ENTRIES[i])) for i in ids]
    hint = kb.TYPE_HINT.get(qtype, "")
    prompt = f"คำถาม: {query}\n" + (f"ชนิดคำถาม: {qtype}. {hint}\n" if hint else "") + "\n" + "\n\n".join(blocks)
    got = _generate(FOCUS_SYSTEM, prompt, _schema("paragraphs", "STRING"))
    chosen = {}                                # {หัวข้อ: {ย่อหน้า: {ประโยค} หรือ None = ทั้งย่อหน้า}}
    for label in got.get("paragraphs", []):
        m = re.fullmatch(r"\[?(\d+)\.(\d+)(?:\.(\d+))?\]?", str(label).strip())
        if not m or int(m.group(1)) not in ids:
            continue
        i, k = int(m.group(1)), int(m.group(2))
        us = kb.units(kb.ENTRIES[i])
        if k >= len(us):
            continue
        paras = chosen.setdefault(i, {})
        if m.group(3) is None:
            paras[k] = None
        else:
            n = int(m.group(3)) - 1
            if 0 <= n < len(kb.segments(us[k])) and paras.get(k, set()) is not None:
                paras.setdefault(k, set()).add(n)
    picked = {}
    for i, paras in chosen.items():
        us, items = kb.units(kb.ENTRIES[i]), []
        for k, ns in paras.items():
            segs = kb.segments(us[k])
            if ns is None or len(ns) == len(segs):
                items.append(k)
                continue
            run = []
            for n in sorted(ns) + [None]:
                if run and (n is None or n != run[-1] + 1):
                    items.append((k, segs[run[0]][0], segs[run[-1]][1]))
                    run = []
                if n is not None:
                    run.append(n)
        picked[i] = kb._normalize_picks(items)
    return picked


_ERRORS = (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError)


def _log(exc):
    detail = ""
    if isinstance(exc, urllib.error.HTTPError):
        detail = exc.read().decode("utf-8", "replace")[:200]
    print(f"[!] ใช้ AI เลือกหัวข้อไม่สำเร็จ ใช้วิธีค้นแบบเดิมแทน: {type(exc).__name__}: {exc} {detail}")


def _select(query):
    """(เลขหัวข้อ, {เลขหัวข้อ: ย่อหน้า/ช่วงที่เลือก / [] หรือ "all" = ทั้งหัวข้อ / "drop" = ไม่ใช้}) หรือ None เมื่อเรียก AI ไม่ได้
    เรียก AI ไม่เกินสองครั้ง: เลือกหัวข้อ แล้วเลือกประโยค (ข้ามรอบสองเมื่อได้หัวข้อสั้นหัวข้อเดียว
    หรือระบบหาย่อหน้านิยามของศัพท์ที่ถามได้เอง) ผลที่ได้ knowledge_base จำไว้ใน answer_memory"""
    try:
        ids = route(query)
    except _ERRORS as exc:
        _log(exc)
        return None
    picked = {}
    # AI เลือกทั้งหัวข้อหลักและหัวข้อย่อยของมัน ("คีย์มีกี่ประเภท" -> 4.5 + 4.5·1 + 4.5·2) = ถามทั้งกลุ่ม: แสดงหัวข้อหลักครบทุกส่วน
    topics = [kb.ENTRIES[i]["topic"] for i in ids]
    groups = {t for t in topics if any(o.startswith(t + " · ") for o in topics)}
    ids = [i for i in ids if kb.ENTRIES[i]["topic"].split(" · ")[0] not in groups or kb.ENTRIES[i]["topic"] in groups]
    for i in ids:
        e = kb.ENTRIES[i]
        if e["topic"] in groups:
            picked[i] = "all"
        elif len(e["description"]) < AI_FOCUS_MIN_CHARS:
            picked[i] = [] if len(ids) == 1 else None   # หัวข้อสั้นหัวข้อเดียว แสดงทั้งหัวข้อได้เลย
        else:
            # ถามความหมายของศัพท์ที่หัวข้อนี้นิยามไว้ ระบบหาย่อหน้านิยามได้เอง ไม่ต้องใช้โควตา AI
            picked[i] = kb.definition_blocks(query, e) or None
    need = [i for i in ids if picked[i] is None]
    if need:
        try:
            chosen = focus(query, need, kb.question_type(query))
        except _ERRORS as exc:
            _log(exc)                          # เลือกหัวข้อได้แล้วแต่เลือกประโยคไม่ได้: แสดงทั้งหัวข้อ (ถูกจำกัดความยาวภายหลัง)
            return ids, {i: (p if p is not None else "all") for i, p in picked.items()}
        for i in need:
            if not chosen:
                picked[i] = "all"              # AI ไม่เลือกเลยสักหัวข้อ: แสดงหัวข้อที่เลือกมาทั้งหมด
            elif not chosen.get(i):
                picked[i] = "drop"             # อ่านเนื้อหาแล้วไม่มีประโยคที่ตอบคำถาม (หัวข้อที่แค่ชื่อคล้าย)
            else:
                picked[i] = attach(kb.units(kb.ENTRIES[i]), chosen[i])
    return ids, picked


def plan_answer(query):
    """แผนคำตอบแบบเดียวกับ knowledge_base.plan_answer: [(หัวข้อ, ย่อหน้าที่เลือก)]
    คืน None เมื่อใช้ AI ไม่ได้ และ [] เมื่อ AI บอกว่าตำราไม่มีเรื่องนี้ (ผู้เรียกตัดสินใจเองว่าจะค้นแบบเดิมต่อไหม)"""
    if not enabled() or kb.DATASET_ERROR:
        return None
    selected = _select(query)
    if selected is None:
        return None
    ids, picked = selected
    # ถามความหมายได้เฉพาะส่วนนำของหัวข้อที่ถูกแบ่งส่วน ถามประเภท/วิธีใช้ได้ครบทุกหัวข้อย่อย
    whole = [] if kb.asks_meaning(query) else None
    return [(kb.ENTRIES[i], whole if picked[i] in ([], "all") else picked[i]) for i in ids if picked[i] != "drop"]

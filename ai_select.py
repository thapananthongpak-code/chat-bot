"""ให้ AI ช่วยอ่านคำถามที่คนพิมพ์เอง แล้วเลือกว่าหัวข้อและย่อหน้าไหนในตำราตอบคำถามนั้น

AI ไม่ได้เขียนคำตอบ: AI ส่งกลับมาแค่ "เลขหัวข้อ" กับ "เลขย่อหน้า" ระบบตรวจว่าเป็นเลขที่มีอยู่จริง
แล้วนำข้อความจากตำรามาแสดงตรงตัว (knowledge_base.render_plan) AI จึงเติมคำหรือแต่งเนื้อหาเองไม่ได้
ใช้ Claude เมื่อตั้ง ANTHROPIC_API_KEY, ใช้ Gemini เมื่อตั้ง GEMINI_API_KEY (มีทั้งคู่ใช้ Claude, บังคับได้ด้วย AI_PROVIDER)
ไม่ได้ตั้ง key หรือเรียก AI ไม่สำเร็จ (โควตาเต็ม, เน็ตหลุด, ช้าเกิน) -> คืน None ให้ใช้วิธีค้นแบบเดิม
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

try:
    import anthropic
except ImportError:          # ใช้แค่ Gemini ก็ได้ ไม่ต้องติดตั้ง
    anthropic = None

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# flash-lite ตอบใน ~1 วินาทีเมื่อปิดการคิดยาว (thinkingLevel minimal) และโควตาฟรีมากกว่ารุ่น flash
DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-5"     # เปลี่ยนได้ด้วย ANTHROPIC_MODEL เช่น claude-sonnet-5-5, claude-haiku-4-5
TIMEOUT = 15          # วินาทีต่อการเรียกหนึ่งครั้ง ช้ากว่านี้ใช้วิธีค้นแบบเดิมแทน
MAX_SECTIONS = 3
PARA_PREVIEW = 300    # AI เห็นแต่ละย่อหน้าแค่ช่วงต้น พอให้รู้ว่าพูดเรื่องอะไร (ประหยัดเวลาและค่าใช้จ่าย)


def provider():
    """"anthropic" | "gemini" | None ตาม key ที่ตั้งไว้"""
    forced = os.getenv("AI_PROVIDER", "").strip().lower()
    has_claude = bool(os.getenv("ANTHROPIC_API_KEY", "").strip()) and anthropic is not None
    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())
    if forced in ("anthropic", "claude"):
        return "anthropic" if has_claude else None
    if forced == "gemini":
        return "gemini" if has_gemini else None
    return "anthropic" if has_claude else "gemini" if has_gemini else None


def enabled():
    return provider() is not None


def model_label():
    """ชื่อรุ่น AI ที่ใช้อยู่ (บันทึกไว้คู่กับคำตอบที่จำ)"""
    if provider() == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", "").strip() or DEFAULT_CLAUDE_MODEL
    if provider() == "gemini":
        return os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
    return ""


def _generate(system, prompt, schema, static=""):
    """เรียก AI ให้ตอบเป็น JSON ตาม schema
    static = ข้อความยาวที่เหมือนกันทุกคำถาม (รายชื่อหัวข้อทั้งเล่ม) Claude เก็บเป็น prompt cache ได้"""
    if provider() == "anthropic":
        return _claude(system, prompt, schema, static)
    return _gemini(system, prompt + ("\n\n" + static if static else ""), schema)


_CLIENT = {}


def _claude(system, prompt, schema, static):
    model = model_label()
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if _CLIENT.get("key") != key:
        # SDK ลองใหม่เองเมื่อเจอ 429/5xx/เน็ตหลุด 1 ครั้ง นานสุดราว 30 วินาทีแล้วใช้วิธีค้นเองแทน
        _CLIENT.update(key=key, client=anthropic.Anthropic(api_key=key, timeout=TIMEOUT, max_retries=1))
    blocks = [{"type": "text", "text": system}]
    if static:
        blocks.append({"type": "text", "text": static, "cache_control": {"type": "ephemeral"}})
    config = {"format": {"type": "json_schema", "schema": schema}}
    if not model.startswith("claude-haiku"):
        config["effort"] = "low"       # งานเลือกเลขหัวข้อ ไม่ต้องคิดยาว (Haiku 4.5 ไม่รองรับ effort)
    response = _CLIENT["client"].messages.create(
        model=model, max_tokens=4000, system=blocks,
        messages=[{"role": "user", "content": prompt}], output_config=config)
    if response.stop_reason in ("refusal", "max_tokens"):
        raise ValueError(f"Claude หยุดตอบ: {response.stop_reason}")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise ValueError("Claude ไม่ได้ส่งผลลัพธ์")
    return json.loads(text)


def _gemini(system, prompt, schema):
    """เรียก Gemini ให้ตอบเป็น JSON ตาม schema"""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = model_label()
    config = {"temperature": 0, "responseMimeType": "application/json", "responseSchema": _gemini_schema(schema)}
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


def _gemini_schema(schema):
    """JSON Schema -> รูปแบบ schema ของ Gemini (ชนิดตัวพิมพ์ใหญ่ ไม่มี additionalProperties)"""
    if isinstance(schema, dict):
        return {k: (v.upper() if k == "type" else _gemini_schema(v))
                for k, v in schema.items() if k != "additionalProperties"}
    return schema


def _schema(name, item_type):
    return {"type": "object", "properties": {name: {"type": "array", "items": {"type": item_type}}},
            "required": [name], "additionalProperties": False}


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

FOCUS_SYSTEM = """You pick paragraphs from a Thai textbook on database systems that answer a student's question.
You never write the answer yourself; you only return paragraph labels.
Input: the question, then the paragraphs of one or more sections, each labelled [section.paragraph] (long paragraphs are cut short with …).
Return the labels of the paragraphs the student needs to read to answer the question completely, and nothing more:
- include the paragraphs that directly explain what is asked, plus the example, table, figure caption or SQL that illustrates it right after them;
- leave out paragraphs about other concepts, general introductions, and further examples the question does not ask for;
- if the question asks for a whole list (types, steps, advantages, commands…), include every item of that list and each item's explanation;
- if no paragraph answers the question, return an empty list."""


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
    """ย่อหน้าที่ต้องไปด้วยกัน แม้ AI ไม่ได้เลือก: ตาราง/โค้ด/ที่มาของรูปที่ตามหลังย่อหน้าที่เลือก,
    คำบรรยายรูป "ภาพที่ X" คู่กับคำอธิบาย "จากภาพที่ X", และบรรทัดเนื้อหาของหัวข้อย่อยที่เลือก"""
    out = set(picked)
    for k in sorted(picked):
        j = k + 1
        while j < len(us) and (us[j].startswith("```") or " | " in us[j] or re.match(r"^ที่มา\s*:?", us[j])):
            out.add(j)
            j += 1
        cap = kb._CAPTION.match(us[k].strip())
        if cap or _is_heading_only(us[k]):   # เลือกคำบรรยายรูป/หัวเรื่อง ต้องได้คำอธิบายที่ตามมาด้วย
            if j < len(us) and not kb._CAPTION.match(us[j]):
                out.add(j)
        ref = re.match(r"^จาก\s*(ภาพ|ตาราง)ที่\s*(\d+\.\d+)", us[k].strip())
        if ref:   # "จากภาพที่ 1.2 …" ต้องมีรูป 1.2 ให้เห็นด้วย
            for j in range(k - 1, max(-1, k - 12), -1):
                if re.match(r"^" + ref.group(1) + r"ที่\s*" + re.escape(ref.group(2)) + r"(?!\d)", us[j].strip()):
                    out.update(range(j, k))
                    break
    return sorted(out)


def _is_heading_only(u):
    names, full = kb._defined_terms(u)
    return bool(names) and not full


def route(query):
    """เลขหัวข้อที่ AI เลือก (ตรวจแล้วว่ามีจริง) — [] = AI บอกว่าตำราไม่มีเรื่องนี้"""
    got = _generate(ROUTE_SYSTEM, f"คำถาม: {query}", _schema("sections", "integer"),
                    static=f"หัวข้อในตำรา:\n{_catalog()}")
    ids = [i for i in got.get("sections", []) if isinstance(i, int) and 0 <= i < len(kb.ENTRIES)]
    return list(dict.fromkeys(ids))[:MAX_SECTIONS]


def focus(query, ids):
    """ย่อหน้าที่ AI เลือกในแต่ละหัวข้อ {เลขหัวข้อ: [เลขย่อหน้า]} (ตรวจแล้วว่ามีจริง)"""
    blocks = []
    for i in ids:
        us = kb.units(kb.ENTRIES[i])
        blocks.append(f"## {kb.ENTRIES[i]['topic']}\n" + "\n".join(f"[{i}.{k}] {_preview(u)}" for k, u in enumerate(us)))
    got = _generate(FOCUS_SYSTEM, f"คำถาม: {query}\n\n" + "\n\n".join(blocks), _schema("paragraphs", "string"))
    picked = {}
    for label in got.get("paragraphs", []):
        m = re.fullmatch(r"\[?(\d+)\.(\d+)\]?", str(label).strip())
        if m and int(m.group(1)) in ids and int(m.group(2)) < len(kb.units(kb.ENTRIES[int(m.group(1))])):
            picked.setdefault(int(m.group(1)), set()).add(int(m.group(2)))
    return {i: sorted(ks) for i, ks in picked.items()}


_ERRORS = (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError) + (
    (anthropic.APIError,) if anthropic is not None else ())


def _log(exc):
    detail = ""
    if isinstance(exc, urllib.error.HTTPError):
        detail = exc.read().decode("utf-8", "replace")[:200]
    elif anthropic is not None and isinstance(exc, anthropic.RateLimitError):
        detail = "(เกินอัตราที่บัญชีใช้ได้ต่อนาที)"
    print(f"[!] ใช้ AI เลือกหัวข้อไม่สำเร็จ ใช้วิธีค้นแบบเดิมแทน: {type(exc).__name__}: {exc} {detail}")


def _select(query):
    """(เลขหัวข้อ, {เลขหัวข้อ: ย่อหน้าที่เลือก / [] หรือ "all" = ทั้งหัวข้อ / "drop" = ไม่ใช้}) หรือ None เมื่อเรียก AI ไม่ได้
    เรียก AI ไม่เกินสองครั้ง: เลือกหัวข้อ แล้วเลือกย่อหน้า (ข้ามรอบสองเมื่อได้หัวข้อสั้นหัวข้อเดียว
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
        elif len(e["description"]) < kb.FOCUS_MIN_CHARS:
            picked[i] = [] if len(ids) == 1 else None   # หัวข้อสั้นหัวข้อเดียว แสดงทั้งหัวข้อได้เลย
        else:
            # ถามความหมายของศัพท์ที่หัวข้อนี้นิยามไว้ ระบบหาย่อหน้านิยามได้เอง ไม่ต้องใช้โควตา AI
            picked[i] = kb.definition_blocks(query, e) or None
    need = [i for i in ids if picked[i] is None]
    if need:
        try:
            chosen = focus(query, need)
        except _ERRORS as exc:
            _log(exc)                          # เลือกหัวข้อได้แล้วแต่เลือกย่อหน้าไม่ได้: แสดงทั้งหัวข้อ
            return ids, {i: (p if p is not None else "all") for i, p in picked.items()}
        for i in need:
            if not chosen:
                picked[i] = "all"              # AI ไม่เลือกย่อหน้าเลยสักหัวข้อ: แสดงหัวข้อที่เลือกมาทั้งหมด
            elif not chosen.get(i):
                picked[i] = "drop"             # อ่านเนื้อหาแล้วไม่มีย่อหน้าที่ตอบคำถาม (หัวข้อที่แค่ชื่อคล้าย)
            elif len(kb.ENTRIES[i]["description"]) < kb.FOCUS_MIN_CHARS:
                picked[i] = []                 # หัวข้อสั้นที่ตอบคำถาม แสดงทั้งหัวข้อ
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

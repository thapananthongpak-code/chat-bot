"""สร้างคลังคำตอบล่วงหน้า (ai_answers.json) ให้คำถามเชิงวิเคราะห์ของทุกหัวข้อ

เว็บบน Vercel เรียก AI สดไม่ได้ (เขียนไฟล์ไม่ได้ และต้องตอบคำถามเดิมให้เหมือนเดิมเสมอ) จึงให้ AI คัดประโยคล่วงหน้าที่นี่
แล้ว commit ไฟล์ขึ้นไปพร้อมโค้ด คำถามที่ผู้ใช้พิมพ์ต่างจากที่สร้างไว้เล็กน้อยก็ใช้คำตอบเดียวกัน
เพราะคำตอบถูกจำตาม (ชนิดคำถาม, หัวข้อ) ด้วย (knowledge_base.typed_key)

    python build_library.py              # สร้างต่อจากที่มี (ข้ามคำถามที่จำไว้แล้ว)
    python build_library.py --fresh      # ลบคำตอบที่ AI เคยเลือกไว้ แล้วสร้างใหม่ทั้งหมด
    python build_library.py --repin      # ให้ AI เลือกใหม่ทีละข้อเฉพาะคำตอบเดิมที่ AI เคยเลือก (ข้อที่ AI ไม่ตอบคงของเดิมไว้)
    python build_library.py --list       # แค่แสดงรายการคำถามที่จะสร้าง
    python build_library.py --limit 20   # สร้างแค่ 20 ข้อแรก (ลองก่อน)
    python build_library.py --workers 8  # เรียก AI คู่ขนาน (ค่าเริ่มต้น 6 โควตายังไม่เกิน 12 ครั้ง/นาที)

AI ตอบกลับได้แค่เลขหัวข้อ/เลขประโยค ข้อความทุกตัวอักษรมาจากตำราเหมือนเดิม
เรียก AI ไม่สำเร็จ (โควตา/ล่ม) จะรอแล้วลองใหม่ ข้อที่ยังไม่สำเร็จจะไม่ถูกจำ (ไม่ปักคำตอบแบบค้นเองลงไฟล์)
"""

import os
import re
import sys
import time

import knowledge_base as kb
import ai_select

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "ai_answers.json")
CALLS_PER_MINUTE = 12          # โควตาฟรีของ Gemini 15 ครั้งต่อนาที เผื่อไว้
RETRY_WAITS = (20, 60, 120)    # วินาที ก่อนลองใหม่เมื่อ API ล่ม/โควตาเต็ม
# รุ่นที่ลองสลับกันเมื่อรุ่นแรกล่ม (รุ่นแรกคือ GEMINI_MODEL หรือค่าเริ่มต้นของ ai_select)
FALLBACK_MODELS = ("gemini-3.1-flash-lite-preview", "gemini-3-flash-preview")
TYPE_ORDER = {"ขอตัวอย่าง": 0, "ใช้ยังไง": 1, "ขั้นตอน": 1, "มีอะไรบ้าง": 2, "ประโยชน์ของ": 3, "อธิบาย": 4}
SQL_CHAPTERS = ("บทที่ 8", "บทที่ 9", "บทที่ 10")


def load_env():
    path = os.path.join(HERE, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            m = re.match(r"\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
            if m and not os.getenv(m.group(1)):
                os.environ[m.group(1)] = m.group(2).strip("'\"")


def term_of(entry):
    """ชื่อเรื่องที่คนพิมพ์: วลีอังกฤษในชื่อหัวข้อ (INNER JOIN, GROUP BY) ถ้ามี ไม่งั้นชื่อไทยของหัวข้อ"""
    english = [p for p in kb.key_terms(entry) if re.fullmatch(r"[A-Za-z][A-Za-z0-9 _\-]+", p) and len(p) >= 3]
    if english:
        return english[0]
    title = re.sub(r"^(บทที่ \d+\s*)", "", kb._own_title(entry)).strip()
    return re.sub(r"\s*\(บทนำ\)$", "", title)


def questions_for(entry):
    """คำถามเชิงวิเคราะห์ที่ตำราตอบได้ ตามสิ่งที่หัวข้อนั้นมีจริง (ตัวอย่าง/โค้ด/ขั้นตอน/รายการ)"""
    term = term_of(entry)
    if len(term) < 3:
        return []
    text = entry["description"]
    out = []
    if kb._example_spans(entry, None):
        out.append(f"ขอตัวอย่าง{term}")
    out.append(f"อธิบาย{term}")
    chapter = entry.get("references", "")
    if not any(c in chapter for c in SQL_CHAPTERS) and not entry["topic"].startswith("ภาคผนวก"):
        out.append(f"ประโยชน์ของ{term}")
    if "```" in text:
        out.append(f"{term} ใช้ยังไง")
    elif "ขั้นตอน" in text:
        out.append(f"ขั้นตอน{term}")
    items = len(re.findall(r"(?m)^\d{1,2}[.)]\s", text))
    if len(kb.section_parts(entry)) > 2 or items >= 3:
        out.append(f"{term} มีอะไรบ้าง")
    return out


def priority(question):
    """คำถามที่คนถามบ่อยก่อน (ตัวอย่าง, วิธีใช้, รายการ, เหตุผล, อธิบาย) แล้วเรียงตามลำดับในเล่ม: หยุดกลางทางก็ได้คลังที่ใช้ได้"""
    for marker, rank in TYPE_ORDER.items():
        if question.startswith(marker) or question.endswith(marker):
            return rank
    return 5


def all_questions():
    seen, out = set(), []
    for entry in kb.ENTRIES:
        if kb._is_meta(entry["topic"]) or entry["topic"].startswith("แบบฝึกหัด"):
            continue
        if len(entry["description"]) < ai_select.AI_FOCUS_MIN_CHARS:
            continue                   # หัวข้อสั้นแสดงทั้งหัวข้อได้อยู่แล้ว ไม่ต้องให้ AI คัด
        for q in questions_for(entry):
            key = kb.question_key(q)
            if key not in seen:
                seen.add(key)
                out.append(q)
    return sorted(out, key=priority)      # sorted ไม่สลับลำดับในกลุ่มเดียวกัน (ตามลำดับในเล่ม)


class Unavailable(Exception):
    """เรียก AI ไม่สำเร็จหลังลองใหม่แล้ว: ข้ามข้อนี้ ไม่จำคำตอบแบบค้นเอง"""


def topic_selector(query):
    """เหมือน ai_select.plan_answer แต่ข้ามรอบเลือกหัวข้อ: คลังนี้เก็บตาม (ชนิดคำถาม, หัวข้อ) และหัวข้อคือผลค้นอันดับแรก
    (ตัวเดียวกับที่ knowledge_base.typed_key ใช้) จึงเรียก AI แค่รอบเลือกประโยค — ครึ่งเดียวของโควตา
    คืน None เมื่อเรียก AI ไม่สำเร็จ"""
    found = kb.search(query, limit=1)
    if not found:
        return []
    entry, qtype = found[0], kb.question_type(query)
    if qtype == "properties" and len(kb.section_parts(entry)) > 2:
        return [(entry, None)]                 # หัวข้อที่แบ่งหลายส่วน: ใจความเปิดของทุกส่วน (kb._limit_plan) ไม่ต้องใช้ AI
    if len(entry["description"]) < ai_select.AI_FOCUS_MIN_CHARS:
        return [(entry, [])]
    i = kb.ENTRIES.index(entry)
    try:
        picked = ai_select.focus(query, [i], qtype).get(i)
    except ai_select._ERRORS as exc:
        ai_select._log(exc)
        return None
    if not picked:
        return []                              # AI อ่านแล้วบอกว่าหัวข้อนี้ไม่มีประโยคที่ตอบ
    return [(entry, ai_select.attach(kb.units(entry), picked))]


def main(argv):
    from concurrent.futures import ThreadPoolExecutor
    import threading

    load_env()
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    workers = int(argv[argv.index("--workers") + 1]) if "--workers" in argv else 6
    questions = all_questions()[:limit]
    if "--list" in argv:
        print("\n".join(questions))
        print(f"รวม {len(questions)} ข้อ")
        return 0
    if not ai_select.enabled():
        print("ไม่ได้ตั้ง GEMINI_API_KEY ใน .env")
        return 1
    ai_select.TIMEOUT = 60
    memory = kb_memory()
    book = kb.DOCUMENT_META.get("markdown_sha256")
    if "--fresh" in argv:
        gone = [k for k, v in memory.data["answers"].items() if str(v.get("source", "")).startswith("AI")]
        memory.forget(gone)
        print(f"ลบคำตอบที่ AI เคยเลือก {len(gone)} ข้อ")
    repin = {}
    if "--repin" in argv:
        # คำถามเดิมที่ AI เคยเลือก (เก็บเป็นรูปมาตรฐาน) เลือกใหม่ด้วยวิธีระดับประโยค
        repin = {k: v for k, v in memory.data["answers"].items() if str(v.get("source", "")).startswith("AI")}
        questions = list(repin)

    lock = threading.Lock()
    state = {"last": 0.0, "calls": 0, "model": 0, "done": 0, "failed": 0, "skipped": 0}
    models = [os.environ.get("GEMINI_MODEL", "").strip() or ai_select.DEFAULT_MODEL] + list(FALLBACK_MODELS)
    real_generate = ai_select._generate

    def throttled(system, prompt, schema):
        with lock:                             # เริ่มการเรียกห่างกันตามโควตา (ทำงานคู่ขนานได้ แต่ไม่เกินโควตา)
            wait = 60.0 / CALLS_PER_MINUTE - (time.time() - state["last"])
            state["last"] = time.time() + max(wait, 0)
            state["calls"] += 1
            model = models[state["model"]]
        if wait > 0:
            time.sleep(wait)
        os.environ["GEMINI_MODEL"] = model
        try:
            got = real_generate(system, prompt, schema)
            memory.model = model
            return got
        except Exception:
            with lock:
                state["model"] = (state["model"] + 1) % len(models)   # รุ่นนี้ล่ม ลองรุ่นถัดไปในครั้งหน้า
            raise

    ai_select._generate = throttled

    def selector(query):
        for wait in (0,) + RETRY_WAITS:
            time.sleep(wait)
            got = topic_selector(query)
            if got is not None:
                return got
        raise Unavailable(query)

    def work(n_q):
        n, q = n_q
        old = repin.get(q)
        if memory.get(kb.question_key(q), book) and not old:
            with lock:
                state["skipped"] += 1
            return
        if old:
            memory.forget([q])
        try:
            answer = kb.answer_from_dataset([{"role": "user", "content": q}], selector=selector, memory=memory)
        except Unavailable:
            if old:
                memory.put(q, book, old["plan"], old["source"])     # AI ไม่ตอบ: คงคำตอบเดิมไว้
            with lock:
                state["failed"] += 1
            print(f"[{n}/{len(questions)}] ข้าม (AI ไม่ตอบ): {q}", flush=True)
            return
        with lock:
            state["done"] += 1
        topics = [l[3:30] for l in answer.split("\n") if l.startswith("## ")]
        print(f"[{n}/{len(questions)}] {q} -> {topics[:2] or 'ไม่มีข้อมูล'} ({state['calls']} calls)", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, enumerate(questions, 1)))
    print(f"เสร็จ: สร้างใหม่ {state['done']}, มีอยู่แล้ว {state['skipped']}, ไม่สำเร็จ {state['failed']}, "
          f"เรียก AI {state['calls']} ครั้ง")
    return 1 if state["failed"] else 0


def kb_memory():
    from answer_memory import AnswerMemory
    return AnswerMemory(PATH, writable=True, model=ai_select.model_label())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

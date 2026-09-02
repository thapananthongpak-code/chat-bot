"""แปลงคู่มือ SQL รูปแบบ PDF ให้เป็นไฟล์ Markdown สำหรับคลังความรู้ของบอท

วิธีใช้:  ./venv/bin/python tools_pdf_to_md.py <ไฟล์.pdf> <ผลลัพธ์.md>
ต้องติดตั้ง pypdf ก่อน:  ./venv/bin/pip install pypdf

รองรับ PDF ที่จัดหัวข้อเป็นเลขลำดับ เช่น "3. คำสั่ง SELECT" และมีหัวข้อย่อย
"รูปแบบคำสั่ง" กับ "ตัวอย่าง" ซึ่งจะถูกแยกเป็นคอลัมน์ Syntax และ Example
"""
import re
import sys

HEAD = re.compile(r"^\d{1,2}\.\s+(\S.*)$")
# บรรทัดโค้ด SQL — ขึ้นต้นด้วยคำสงวน หรือเป็นบรรทัดต่อเนื่องของคำสั่ง
SQL_LINE = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TRUNCATE|BACKUP|EXEC|"
    r"FROM|WHERE|GROUP\s+BY|ORDER\s+BY|HAVING|VALUES|SET\b|ON\b|UNION|CASE|WHEN|ELSE|END|"
    r"INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+OUTER\s+JOIN|JOIN|CONSTRAINT|"
    r"PRIMARY\s+KEY|FOREIGN\s+KEY|CHECK\s*\(|AND\s|OR\s|AS\b|WITH\s+DIFFERENTIAL|GO;|"
    r"SHOW\s+DATABASES|TO\s+DISK|--|/\*|\*/|\)|\(|\w+\s+(int|varchar|date|nvarchar)\b)",
    re.I)
SYNTAX_MARK = re.compile(r"^(รูปแบบ|รูปแบบคำสั่ง)")
SUBHEAD = re.compile(r"^(ตัวอย่าง|คัดลอก|เพิ่ม|ใช้|เลือก|กำหนด|เรียง|ค้นหา|นับ|สร้าง|แสดง|"
                     r"จัดเรียง|ผสม|การ|แก้ไข|ลบ|ยกเลิก|ตั้งชื่อ|เชื่อม)")


def is_sql(line):
    """โค้ด SQL ในคู่มือไม่มีอักษรไทยปนเลย ใช้เป็นตัวคัดกรองที่แม่นที่สุด"""
    return bool(SQL_LINE.match(line)) and not re.search(r"[฀-๿]", line)


def read_lines(pdf_path):
    from pypdf import PdfReader
    out = []
    for page in PdfReader(pdf_path).pages:
        for line in (page.extract_text() or "").split("\n"):
            line = line.rstrip()
            if not line.strip():
                continue
            if "คู่มือภาษา SQL" in line:      # header ประจำหน้า
                continue
            if re.fullmatch(r"\s*\d{1,3}\s*", line):  # เลขหน้า
                continue
            out.append(line)
    return out


def sections(lines):
    cur, buf = None, []
    for line in lines:
        m = HEAD.match(line.strip())
        if m:
            if cur:
                yield cur, buf
            cur, buf = m.group(1).strip(), []
        elif cur:
            buf.append(line)
    if cur:
        yield cur, buf


def blocks(body):
    """แยกบรรทัดเป็นก้อน สลับระหว่างร้อยแก้วกับโค้ด SQL"""
    out, cur, mode = [], [], None
    for line in body:
        kind = "sql" if is_sql(line) else "text"
        if kind != mode and cur:
            out.append((mode, cur))
            cur = []
        mode = kind
        cur.append(line.strip())
    if cur:
        out.append((mode, cur))
    return out


def parse(topic, body):
    desc, syntax, examples = [], "", []
    seen_syntax_mark = False
    parts = blocks(body)
    for i, (mode, lines) in enumerate(parts):
        if mode == "text":
            for line in lines:
                if SYNTAX_MARK.match(line):
                    seen_syntax_mark = True
                elif not SUBHEAD.match(line) or len(line) > 45:
                    desc.append(line)  # เก็บเฉพาะร้อยแก้วจริง ไม่เอาหัวข้อย่อยสั้น ๆ
            continue
        code = "\n".join(lines)
        prev = " ".join(parts[i - 1][1]) if i and parts[i - 1][0] == "text" else ""
        if not syntax and (seen_syntax_mark or SYNTAX_MARK.search(prev)):
            syntax = code
        else:
            examples.append(code)
    text = re.sub(r"\s+", " ", " ".join(desc)).strip()
    # เก็บตัวอย่างให้ครบ (สูงสุด 4) ยิ่งมีตัวอย่างจริงมาก โมเดลยิ่งไม่ต้องแต่งเอง
    return topic, text, syntax.strip(), "\n\n".join(examples[:4]).strip()


def to_markdown(rows):
    out = ["# คลังความรู้ SQL ภาษาไทย", "",
           "แต่ละหัวข้อขึ้นต้นด้วย `## ` ตามด้วยคำอธิบาย",
           "แล้วใส่ `### รูปแบบคำสั่ง` และ `### ตัวอย่าง` เป็นบล็อกโค้ด ```sql", ""]
    for topic, desc, syntax, example in rows:
        out += ["---", "", f"## {topic}", ""]
        if desc:
            # ขึ้นย่อหน้าใหม่ตรงหัวข้อย่อยของเนื้อหา เช่น "COUNT(*) — นับทุกแถว"
            out += [re.sub(r"\s+(?=[A-Z][A-Za-z_()*\s]{2,30}—)", "\n\n", desc), ""]
        if syntax:
            out += ["### รูปแบบคำสั่ง", "", "```sql", syntax, "```", ""]
        if example:
            out += ["### ตัวอย่าง", "", "```sql", example, "```", ""]
    return "\n".join(out).rstrip() + "\n"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    pdf_path, md_path = sys.argv[1], sys.argv[2]
    rows = [parse(t, b) for t, b in sections(read_lines(pdf_path))]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(to_markdown(rows))
    avg = sum(len(d) for _, d, _, _ in rows) / max(len(rows), 1)
    print(f"เขียน {md_path} แล้ว {len(rows)} หัวข้อ (คำอธิบายเฉลี่ย {avg:.0f} ตัวอักษร)")


if __name__ == "__main__":
    main()

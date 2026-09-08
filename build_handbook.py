"""Build lossless Markdown and a 100-page handbook from the user's 72-page PDF.

Run with the document runtime Python, then render_handbook.cjs, then --merge.
The input PDF is never changed. Generated text retains all content except repeated
page headers and the known page-number line, which are represented in metadata.
"""
import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from pypdf import PdfReader, PdfWriter
import knowledge_base as kb

ROOT = Path(__file__).resolve().parent
TMP = ROOT / 'tmp/pdfs'
OUT = ROOT / 'output/pdf'
MD = ROOT / 'knowledge/sql_handbook_th.md'


def source_sections(reader):
    sections = []
    current = {'topic': 'บทนำและแหล่งที่มาของคู่มือ SQL', 'lines': [], 'pages': []}
    original = []
    for number, page in enumerate(reader.pages, 1):
        lines = (page.extract_text() or '').splitlines()
        # Remove the repeated header and its immediately following number only.
        if lines and 'คู่มือภาษา SQL เบื้องต้น' in lines[0]:
            lines = lines[1:]
        if lines and lines[0].strip() == str(number):
            lines = lines[1:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            original.append(line)
            match = re.match(r'^\d{1,2}\.\s+(\S.*)$', line)
            if match or (number == 72 and line == 'สรุป'):
                if current['lines']:
                    sections.append(current)
                current = {'topic': match.group(1) if match else 'สรุปคู่มือ SQL พื้นฐาน', 'lines': [], 'pages': []}
            current['lines'].append(line)
            current['pages'].append(number + 1)  # New cover is physical page 1.
    if current['lines']:
        sections.append(current)
    reconstructed = [line for section in sections for line in section['lines']]
    assert reconstructed == original, 'Original text was lost or reordered'
    return sections, '\n'.join(original)


def fence_sql(lines):
    """Presentation only; never drop a line, limit examples, or rewrite SQL."""
    out, in_code = [], False
    start = re.compile(r'^(SELECT\b|WITH\b|INSERT\s+INTO\b|UPDATE\s+\w+\s+SET\b|DELETE\s+FROM\b|CREATE\s+(TABLE|INDEX|DATABASE|PROCEDURE)\b|DROP\s+(TABLE|INDEX|DATABASE)\b|ALTER\s+TABLE\b|BACKUP\s+DATABASE\b|TRUNCATE\s+TABLE\b)', re.I)
    for line in lines:
        if not in_code and start.match(line) and not re.search(r'[ก-๙]', line):
            out.append('```sql')
            in_code = True
        out.append(line)
        if in_code and ';' in line:
            out.append('```')
            in_code = False
    if in_code:
        out.append('```')
    return '\n'.join(out)


def supplements():
    existing = kb._load_md(str(ROOT / 'knowledge/sql_extended_th.md'))
    notes = json.loads((ROOT / 'handbook_notes.json').read_text())
    assert len(existing) == len(notes) == 16
    result = []
    for entry, (detail, question, answer) in zip(existing, notes):
        result.append(dict(topic=entry['topic'], description=entry['description'], detail=detail,
                           question=question, answer=answer, example=entry['example'],
                           url=re.search(r'https://\S+', entry['references'])[0]))
    for title, desc, detail, example, question, answer, url in json.loads((ROOT / 'handbook_additions.json').read_text()):
        result.append(dict(topic=title, description=desc, detail=detail, example=example,
                           question=question, answer=answer,
                           url=url if url.startswith('https:') else 'https://www.postgresql.org/docs/current/' + url))
    assert len(result) == 26
    return result


def prepare(pdf):
    TMP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(pdf)
    assert len(reader.pages) == 72, 'This build expects the provided 72-page source'
    old, text = source_sections(reader)
    new = supplements()
    md = ['# คู่มือ SQL และฐานข้อมูล ฉบับรวม 100 หน้า', '',
          'ข้อความต้นฉบับครบ 72 หน้า + ภาคเสริมจากเอกสารทางการ 26 หัวข้อ พร้อมเลขหน้า PDF ฉบับรวม', '']
    for section in old:
        pages = sorted(set(section['pages']))
        span = str(pages[0]) if len(pages) == 1 else f'{pages[0]}-{pages[-1]}'
        md.extend(['## ' + section['topic'], '', fence_sql(section['lines']), '',
                   '### แหล่งอ้างอิง', '', f'คู่มือฉบับรวม หน้า {span} · ต้นฉบับ chatbot-dataset1.pdf ของผู้ใช้',
                   'ต้นฉบับระบุแหล่งที่มา https://www.w3schools.com/sql/ (คงข้อความเดิม ไม่ได้ตรวจทุกข้อกับเว็บไซต์)', ''])
    for page, e in enumerate(new, 74):
        md.extend(['## ' + e['topic'], '', e['description'], '', e['detail'], '',
                   '**คำถามตรวจความเข้าใจ:** ' + e['question'], '', '**คำตอบ:** ' + e['answer'], ''])
        if e['example']:
            md.extend(['### ตัวอย่าง', '', '```sql', e['example'], '```', ''])
        md.extend(['### แหล่งอ้างอิง', '', e['url'],
                   f'คู่มือฉบับรวม หน้า {page} · ตรวจเอกสาร 2026-09-08 · เรียบเรียงภาษาไทยและตัวอย่างสาธิตโดยผู้จัดทำ', ''])
    MD.write_text('\n'.join(md), encoding='utf-8')
    # A separate complete extraction is useful for auditing the legacy conversion.
    (TMP / 'original_text.txt').write_text(text, encoding='utf-8')
    manifest = dict(source_pdf_sha256=hashlib.sha256(Path(pdf).read_bytes()).hexdigest(),
                    source_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    source_pages=72, original_sections=len(old), added_sections=len(new),
                    expected_pages=100, topics=[{'title': e['topic'], 'page': i, 'url': e['url']} for i,e in enumerate(new,74)])
    (TMP / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    h = html.escape
    css = '''@font-face{font-family:Thai;src:url('file:///System/Library/Fonts/Supplemental/Tahoma.ttf')}
    @font-face{font-family:Thai;src:url('file:///System/Library/Fonts/Supplemental/Tahoma%20Bold.ttf');font-weight:700}
    @page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;color:#202522;font-family:Thai,sans-serif}
    .page{width:210mm;height:297mm;padding:17mm 19mm 17mm;position:relative;break-after:page;overflow:hidden}
    .eyebrow{font-size:9px;letter-spacing:2px;color:#3a6357;margin-bottom:9mm}
    h1{font-size:29px;line-height:1.45;margin:0 0 7mm;letter-spacing:-.5px}h2{font-size:23px;line-height:1.5;margin:0 0 7mm}
    p{font-size:14px;line-height:1.85;margin:0 0 5mm}h3{font-size:12px;color:#3a6357;margin:6mm 0 3mm;letter-spacing:.3px}
    pre{background:#f1f4f2;border-left:3px solid #355f50;padding:5mm;font:11.5px/1.7 monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0 0 5mm}
    .review{background:#f4f5f2;padding:5mm;margin-top:6mm;border-radius:2mm}.review p{font-size:12px;margin:0 0 3mm}
    .source{margin-top:6mm;font-size:9px;line-height:1.8;overflow-wrap:anywhere;color:#566059}.source a{color:inherit}
    footer{position:absolute;bottom:9mm;left:19mm;right:19mm;display:flex;justify-content:space-between;border-top:1px solid #ccc;padding-top:3mm;font-size:9px;color:#68716c}
    .toc{columns:2;column-gap:8mm;font-size:10px;line-height:1.8;margin-top:5mm}.toc div{break-inside:avoid;margin-bottom:2mm}
    .intro{padding:6mm;background:#eff4f0;margin:7mm 0}.intro p{font-size:12px}
    .refs{font-size:8px;line-height:1.65}.refs div{margin-bottom:2.3mm;overflow-wrap:anywhere}.refs a{color:#30483e}
    '''
    def footer(n):
        return f'<footer><span>SQL / DATABASE HANDBOOK · ฉบับรวม 2026</span><span>{n:03d} / 100</span></footer>'
    pages = [f'''<section class="page"><div class="eyebrow">REFERENCE EDITION / 2026</div>
    <h1>SQL และฐานข้อมูล<br>คู่มือฉบับรวม 100 หน้า</h1>
    <p>จากพื้นฐาน SQL สู่การออกแบบ ความปลอดภัย<br>ประสิทธิภาพ และการดูแลฐานข้อมูล</p>
    <div class="intro"><p><b>หน้า 2-73</b> คงต้นฉบับผู้ใช้ 72 หน้าไว้ครบ เลขหน้าที่หัวกระดาษเป็นเลขต้นฉบับ</p>
    <p><b>หน้า 74-99</b> ภาคเสริม 26 หัวข้อจากเอกสารทางการ พร้อมแบบทบทวนและตัวอย่างสาธิต</p>
    <p><b>หน้า 100</b> บรรณานุกรม · ไฟล์ Markdown ใช้เลขหน้าของฉบับรวมนี้ในการอ้างอิง</p></div>
    <h3>แผนที่ภาคเสริม</h3><div class="toc">''' + ''.join(f'<div>{i} / {h(e["topic"])}</div>' for i,e in enumerate(new,74)) +
    f'''</div><div class="source">เนื้อหาครอบคลุมหัวข้อหลัก ไม่ใช่ทุกคุณสมบัติของทุก DBMS ข้อความเดิมและไวยากรณ์เฉพาะระบบต้องพิจารณาตามบริบท ตัวอย่างใหม่เป็นแบบฝึกหัดในฐานทดลอง</div>{footer(1)}</section>''']
    for n,e in enumerate(new,74):
        code = '<h3>ตัวอย่างสาธิต</h3><pre>' + h(e['example']) + '</pre>' if e['example'] else ''
        pages.append(f'''<section class="page"><div class="eyebrow">DATABASE PRACTICE / {n-73:02d}</div>
        <h2>{h(e['topic'])}</h2><h3>แนวคิดและการใช้งาน</h3><p>{h(e['description'])}</p>
        <h3>ประเด็นที่ควรเข้าใจ</h3><p>{h(e['detail'])}</p>{code}
        <div class="review"><h3 style="margin-top:0">ตรวจความเข้าใจ</h3><p><b>{h(e['question'])}</b></p><p>{h(e['answer'])}</p></div>
        <div class="source"><b>อ่านเอกสารต้นทาง</b><br><a href="{h(e['url'])}">{h(e['url'])}</a><br>
        ตรวจ 8 กันยายน 2026 · เรียบเรียงภาษาไทย · ตัวอย่างจัดทำเพื่อสาธิต</div>{footer(n)}</section>''')
    refs = ['https://www.w3schools.com/sql/'] + list(dict.fromkeys(e['url'] for e in new))
    pages.append('<section class="page"><div class="eyebrow">SOURCE REGISTER</div><h2>บรรณานุกรมและที่มาของข้อมูล</h2><p style="font-size:12px">ต้นฉบับ 72 หน้าจัดเตรียมโดยผู้ใช้ และระบุ W3Schools บนหน้าปก ภาคเสริมใช้เอกสาร PostgreSQL, Microsoft Learn, OWASP และ MongoDB ด้านล่าง วันที่ตรวจเอกสาร 8 กันยายน 2026</p><div class="refs">' + ''.join(f'<div>{i:02d}. <a href="{h(url)}">{h(url)}</a></div>' for i,url in enumerate(refs,1)) + '</div><div class="source">เก็บข้อมูลเก่าและใหม่แยกที่มา การรวมเอกสารไม่ได้เป็นการรับรองความถูกต้องของข้อความต้นฉบับทุกบรรทัด ควรตรวจเอกสารของรุ่นฐานข้อมูลที่ใช้งานจริงก่อนรันคำสั่ง</div>' + footer(100) + '</section>')
    (TMP / 'supplement.html').write_text('<!doctype html><html lang="th"><meta charset="utf-8"><style>'+css+'</style><body>'+''.join(pages)+'</body></html>',encoding='utf-8')
    print(json.dumps({'original_sections':len(old),'new_sections':len(new),'html_pages':len(pages),'markdown':str(MD)},ensure_ascii=False))


def merge(pdf):
    old = PdfReader(pdf)
    extra = PdfReader(TMP / 'supplement.pdf')
    assert len(extra.pages) == 28, f'Expected 28 authored pages, got {len(extra.pages)}'
    writer = PdfWriter()
    writer.add_page(extra.pages[0])
    for page in old.pages:
        writer.add_page(page)
    for page in extra.pages[1:]:
        writer.add_page(page)
    writer.add_outline_item('คู่มือฉบับรวม / Contents',0)
    writer.add_outline_item('ต้นฉบับ 72 หน้า',1)
    manifest = json.loads((TMP / 'manifest.json').read_text())
    for e in manifest['topics']:
        writer.add_outline_item(e['title'],e['page']-1)
    writer.add_outline_item('บรรณานุกรม',99)
    writer.add_metadata({'/Title':'SQL และฐานข้อมูล - คู่มือฉบับรวม 100 หน้า','/Author':'ครูเอสคิว / User-provided source + official documentation'})
    path = OUT / 'sql_database_handbook_100p_th.pdf'
    with path.open('wb') as f:
        writer.write(f)
    final = PdfReader(path)
    assert len(final.pages) == 100
    for i, page in enumerate(old.pages):
        assert page.extract_text() == final.pages[i+1].extract_text(), f'Original page changed: {i+1}'
    assert all((p.extract_text() or '').strip() for p in final.pages)
    manifest['pdf_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest['markdown_sha256'] = hashlib.sha256(MD.read_bytes()).hexdigest()
    manifest['validation'] = '100 pages; 72 source pages text-identical; all pages contain selectable text'
    (OUT / 'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(path, path.stat().st_size, 'bytes; 100 pages validated')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf')
    parser.add_argument('--merge',action='store_true')
    args = parser.parse_args()
    (merge if args.merge else prepare)(args.pdf)

"""ตอบเฉพาะส่วนที่ถาม (ไม่ดึงทั้งหัวข้อมาเมื่อถามเรื่องเดียว) และ AI ช่วยเลือกหัวข้อ/ย่อหน้าได้โดยไม่แต่งคำตอบเอง
ทดสอบแบบไม่ต่อเน็ต: ส่วนที่เรียก AI ใช้ตัวปลอมแทน Gemini (ทดสอบกับ Gemini จริงใช้ eval_questions.py --ai)"""
import json
import os
import re
import tempfile
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import knowledge_base as kb
import ai_select
import eval_questions as ev
from answer_memory import AnswerMemory

BOOK_LINES = set(Path(kb.KNOWLEDGE_DIR, 'db_business_textbook_th.md').read_text(encoding='utf-8').split('\n'))
FIXED = re.compile(r'^(## |แหล่งข้อมูล:|!\[ภาพที่ [\d.]+\]\(/static/figures/|\[\[ถาม:|---$|ตำราอธิบายแต่ละเรื่อง)')


def ask(q, selector=None, history=()):
    return kb.answer_from_dataset(list(history) + [{'role': 'user', 'content': q}], selector=selector)


def temp_memory(test, writable=True):
    """ที่จำคำตอบชั่วคราวสำหรับทดสอบ (ไม่แตะ ai_answers.json ของจริง)"""
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    os.unlink(path)
    test.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
    return AnswerMemory(path, writable=writable, model='test-model')


def topic_index(prefix):
    return next(i for i, e in enumerate(kb.ENTRIES) if e['topic'].startswith(prefix))


class FakeGemini:
    """แทน ai_select._generate: ตอบตามที่กำหนด และจำว่าถูกเรียกด้วยอะไร"""
    def __init__(self, sections=(), paragraphs=(), error=None):
        self.sections, self.paragraphs, self.error, self.calls = list(sections), list(paragraphs), error, []

    def __call__(self, system, prompt, schema, static=""):
        self.calls.append((system, prompt))
        if self.error:
            raise self.error
        if system == ai_select.ROUTE_SYSTEM:
            return {'sections': self.sections}
        return {'paragraphs': self.paragraphs}


class FocusedAnswers(unittest.TestCase):
    def assertVerbatim(self, answer):
        """ทุกบรรทัดเนื้อหาในคำตอบต้องเป็นบรรทัดในไฟล์ตำราตรงตัว (ยกเว้นชื่อหัวข้อ ที่มา รูป ปุ่ม)"""
        for line in answer.split('\n'):
            if line.strip() and not FIXED.match(line) and line != kb.PARTIAL_NOTE:
                self.assertIn(line, BOOK_LINES)

    def test_question_sets(self):
        # หัวข้อตามสารบัญทุกหัวข้อ, หัวเรื่องย่อยในเนื้อหา, คำถามแบบพิมพ์เอง, คำถามนอกตำรา (ไม่นับข้อที่ต้องใช้ AI)
        for case in ev.toc_cases(kb) + ev.HEADING_CASES + ev.NATURAL_CASES + ev.PARAPHRASE_CASES + ev.OUTSIDE_CASES:
            if case.get('ai'):
                continue
            with self.subTest(q=case['q']):
                answer = ask(case['q'])
                self.assertEqual(ev.check(kb, case, answer), [])
                if answer != kb.NO_DATA:
                    self.assertVerbatim(answer)

    def test_meaning_of_one_term_is_not_the_whole_topic(self):
        # ภาพหน้าจอจากผู้ใช้: "สารสนเทศคืออะไร" เคยได้ทั้งหัวข้อ 1.1 (รวมความหมายของข้อมูลและรูป 1.3)
        answer = ask('สารสนเทศคืออะไร')
        whole = next(e for e in kb.ENTRIES if e['topic'].startswith('1.1 '))
        self.assertIn('สารสนเทศ (Information) หมายถึง', answer)
        self.assertIn('ตัวอย่างสารสนเทศ', answer)
        self.assertIn('![ภาพที่ 1.2](/static/figures/fig_1_2.webp)', answer)   # รูปประกอบของส่วนนี้ยังอยู่
        self.assertNotIn('ข้อมูล (Data) หมายถึง', answer)
        self.assertLess(len(answer), len(whole['description']) * 0.5)

    def test_partial_answer_offers_the_whole_topic(self):
        answer = ask('ทูเพิลคืออะไร')
        topic = next(e for e in kb.ENTRIES if e['topic'].startswith('4.4 '))
        self.assertIn(kb.PARTIAL_NOTE, answer)
        self.assertIn(f"[[ถาม:{topic['topic']}]]", answer)
        # แตะปุ่ม = ถามด้วยชื่อหัวข้อเต็ม ได้ทั้งหัวข้อ
        self.assertIn(kb.with_figures(topic['description']), ask(topic['topic']))
        # พิมพ์ "อธิบายเพิ่ม" ต่อจากคำตอบบางส่วน ก็ได้ทั้งหัวข้อเช่นกัน
        history = [{'role': 'user', 'content': 'ทูเพิลคืออะไร'}, {'role': 'assistant', 'content': answer}]
        self.assertIn(kb.with_figures(topic['description']), ask('อธิบายเพิ่ม', history=history))
        # ถามหัวข้อที่เกี่ยวข้อง ยังได้ปุ่มหัวข้ออื่นเหมือนเดิม
        related = ask('มีหัวข้ออะไรที่เกี่ยวข้องอีกไหม', history=history)
        self.assertIn('[[ถาม:', related)
        self.assertNotIn(topic['description'], related)

    def test_short_topic_is_shown_whole(self):
        answer = ask('คีย์หลักคืออะไร')
        topic = next(e for e in kb.ENTRIES if e['topic'].startswith('4.5 ประเภทของคีย์ · 3.'))
        self.assertIn(kb.with_figures(topic['description']), answer)
        self.assertNotIn(kb.PARTIAL_NOTE, answer)

    def test_definition_index(self):
        # ศัพท์ที่นิยามไว้ในเนื้อหา (ไม่ใช่ชื่อหัวข้อ) ต้องหาเจอ และประโยคที่แค่หน้าตาเหมือนนิยามต้องไม่ถูกนับ
        index = kb.definitions()
        for term, where in [('ทูเพิล', '4.4 '), ('DDL', '8.1 '), ('ฟิลด์', '1.3 '), ('บิต', '1.3 '), ('AI', '11.6 '),
                            ('Deletion Anomaly', '1.6 '), ('สคีมา', '3.9 ')]:
            with self.subTest(term=term):
                self.assertTrue(any(e['topic'].startswith(where) for e, _, _ in index[kb._term_key(term)]))
        self.assertNotIn(kb._term_key('Petersen, 2018'), index)                  # วงเล็บอ้างอิง
        self.assertFalse(any(e['topic'].startswith('7.4 ') for e, _, _ in index[kb._term_key('Partial Dependency')]))


class AiSelector(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key', 'ANTHROPIC_API_KEY': '', 'AI_PROVIDER': ''})
        env.start()
        self.addCleanup(env.stop)

    def use(self, fake):
        p = patch.object(ai_select, '_generate', fake)
        p.start()
        self.addCleanup(p.stop)
        return fake

    def test_ai_returns_only_numbers_and_text_comes_from_the_book(self):
        i = topic_index('8.2 ')
        n = len(kb.units(kb.ENTRIES[i]))
        fake = self.use(FakeGemini(sections=[i, 999, -1, 'x'],
                                   paragraphs=[f'{i}.0', f'[{i}.1]', f'{i}.{n + 50}', '3.1', 'แต่งคำตอบเอง']))
        answer = ask('ชนิดข้อมูลใน SQL มีอะไรบ้าง', selector=ai_select.plan_answer)
        self.assertEqual(len(fake.calls), 2)                        # เลือกหัวข้อ แล้วเลือกย่อหน้า
        self.assertIn('คำถาม: ชนิดข้อมูลใน SQL มีอะไรบ้าง', fake.calls[0][1])
        self.assertEqual([l[3:] for l in answer.split('\n') if l.startswith('## ')], [kb.ENTRIES[i]['topic']])
        self.assertNotIn('แต่งคำตอบเอง', answer)
        self.assertIn(kb.PARTIAL_NOTE, answer)
        FocusedAnswers.assertVerbatim(self, answer)

    def test_catalog_lists_terms_defined_inside_topics(self):
        catalog = ai_select._catalog()
        line = next(l for l in catalog.split('\n') if '4.4 โครงสร้างฐานข้อมูลเชิงสัมพันธ์' in l)
        self.assertIn('ทูเพิล', line)
        self.assertEqual(len(catalog.split('\n')), len(kb.ENTRIES))

    def test_ai_failure_falls_back_to_search(self):
        error = urllib.error.HTTPError('https://x', 429, 'Too Many Requests', {}, BytesIO(b'{"error": "quota"}'))
        self.use(FakeGemini(error=error))
        for q in ['ชนิดข้อมูลใน SQL มีอะไรบ้าง', 'GROUP BY ใช้ยังไง', 'ราคาทองวันนี้']:
            with self.subTest(q=q):
                self.assertEqual(ask(q, selector=ai_select.plan_answer), ask(q))

    def test_ai_says_not_in_book(self):
        self.use(FakeGemini(sections=[]))
        self.assertEqual(ask('ราคาทองวันนี้', selector=ai_select.plan_answer), kb.NO_DATA)
        # AI ว่าไม่มี แต่ค้นจากชื่อหัวข้อเจอ ใช้ผลค้นแบบเดิม (AI ตัดคำตอบที่มีในตำราทิ้งไม่ได้)
        self.assertEqual(ask('GROUP BY ใช้ยังไง', selector=ai_select.plan_answer), ask('GROUP BY ใช้ยังไง'))

    def test_confident_questions_do_not_use_ai(self):
        fake = self.use(FakeGemini(sections=[0]))
        for q in ['ทูเพิลคืออะไร', '7.5', 'ชนิดของแฟ้มข้อมูล', 'ข้อดีของแบบจำลองฐานข้อมูลเชิงสัมพันธ์',
                  kb.ENTRIES[5]['topic'], 'INNER JOIN กับ LEFT JOIN ต่างกันยังไง']:
            ask(q, selector=ai_select.plan_answer)
        self.assertEqual(fake.calls, [])

    def test_topic_without_picked_paragraphs_is_shown_whole(self):
        # AI เลือกหัวข้อแต่ไม่เลือกย่อหน้า (เคยเกิดกับคำถามเทียบ) ต้องไม่ตัดหัวข้อนั้นทิ้ง
        i, j = topic_index('10.5 '), topic_index('10.6 ')
        self.use(FakeGemini(sections=[i, j], paragraphs=[]))
        answer = ask('join สองแบบนี้ใช้ต่างกันตรงไหน', selector=ai_select.plan_answer)
        self.assertIn(kb.with_figures(kb.ENTRIES[i]['description']), answer)
        self.assertIn(kb.with_figures(kb.ENTRIES[j]['description']), answer)

    def test_topic_the_ai_read_and_rejected_is_dropped(self):
        # AI เลือกหลายหัวข้อ แต่พออ่านเนื้อหาแล้วเลือกย่อหน้าจากหัวข้อเดียว: หัวข้อที่แค่ชื่อคล้ายไม่ถูกแสดง
        appendix, security = topic_index('ภาคผนวก ข 1.'), topic_index('12.5 ')
        us = kb.units(kb.ENTRIES[security])
        k = next(k for k, u in enumerate(us) if 'Encrypt with Password' in u)
        fake = self.use(FakeGemini(sections=[appendix, security], paragraphs=[f'{security}.{k}']))
        answer = ask('ล็อกไฟล์ฐานข้อมูลไม่ให้คนอื่นเปิด', selector=ai_select.plan_answer)
        self.assertIn(appendix, [int(x) for x in re.findall(r'\[(\d+)\.\d+\]', fake.calls[1][1])])  # AI ได้อ่านเนื้อหาจริง
        self.assertEqual([l[3:] for l in answer.split('\n') if l.startswith('## ')], [kb.ENTRIES[security]['topic']])
        self.assertIn('Encrypt with Password', answer)

    def test_term_the_book_does_not_explain_stays_no_data(self):
        # ค้นเองไม่เจอ + AI เลือกหัวข้อที่ไม่มีคำว่า MySQL เลย (2.3 ระบบจัดการฐานข้อมูล) -> ยังตอบว่าไม่มีข้อมูล
        i = topic_index('2.3 ')
        self.use(FakeGemini(sections=[i], paragraphs=[f'{i}.0']))
        self.assertEqual(ask('MySQL คืออะไร', selector=ai_select.plan_answer), kb.NO_DATA)
        # ศัพท์ที่อยู่ในย่อหน้าที่ AI เลือกจริง ใช้คำตอบของ AI ได้
        j = topic_index('1.3 ')
        k = next(k for k, u in enumerate(kb.units(kb.ENTRIES[j])) if u.startswith('3) เรคอร์ดหรือระเบียน'))
        self.use(FakeGemini(sections=[j], paragraphs=[f'{j}.{k}']))
        self.assertIn('## 1.3 ', ask('ระเบียนข้อมูลในตารางคืออะไร', selector=ai_select.plan_answer))

    def test_exercise_page_does_not_replace_a_real_topic(self):
        # AI สุ่มพลาดเลือกแบบฝึกหัดท้ายบท ทั้งที่ค้นเองเจอหัวข้อเนื้อหา -> ใช้หัวข้อเนื้อหา
        self.use(FakeGemini(sections=[topic_index('แบบฝึกหัดท้ายบท บทที่ 9')]))
        self.assertEqual(ask('GROUP BY ใช้ยังไง', selector=ai_select.plan_answer), ask('GROUP BY ใช้ยังไง'))
        self.assertIn('แบบฝึกหัดท้ายบท', ask('แบบฝึกหัด GROUP BY', selector=ai_select.plan_answer))

    def test_parts_are_not_repeated(self):
        # AI เลือกทั้งหัวข้อหลัก 4.5 และหัวข้อย่อยของมัน ต้องแสดงแต่ละส่วนครั้งเดียว
        i = topic_index('4.5 ประเภทของคีย์')
        self.use(FakeGemini(sections=[i, i + 1, i + 2]))
        answer = ask('คีย์ในฐานข้อมูลแบ่งเป็นแบบไหนได้บ้าง', selector=ai_select.plan_answer)
        for e in kb.section_parts(kb.ENTRIES[i]):
            self.assertEqual(answer.count('## ' + e['topic'] + '\n'), 1)

    def test_definition_found_needs_one_call(self):
        fake = self.use(FakeGemini(sections=[topic_index('4.4 ')]))
        first = ai_select.plan_answer('ทูเพิลคืออะไร')
        self.assertEqual(len(fake.calls), 1)              # ย่อหน้านิยามหาเองได้ ไม่ต้องให้ AI เลือกย่อหน้า
        self.assertIn('ทูเพิล หมายถึง', kb.render_plan(first))

    def test_attach_keeps_figure_with_its_explanation(self):
        e = kb.ENTRIES[topic_index('1.1 ')]
        us = kb.units(e)
        explain = next(k for k, u in enumerate(us) if u.startswith('จาก ภาพที่ 1.2'))
        caption = next(k for k, u in enumerate(us) if u.startswith('ภาพที่ 1.2'))
        self.assertIn(caption, ai_select.attach(us, [explain]))

    def test_web_app_uses_ai_only_with_key(self):
        import app as application
        i = topic_index('8.2 ')
        self.use(FakeGemini(sections=[i], paragraphs=[f'{i}.0']))
        post = lambda client: client.post('/chat/stream', json={'message': 'ชนิดข้อมูลใน SQL มีอะไรบ้าง'}).get_data(as_text=True)
        with application.app.test_client() as client, patch.object(application, 'save_web_chat'):
            with patch.object(application, 'answer_memory', temp_memory(self)):
                self.assertIn('## 8.2 ', post(client))
                with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
                    self.assertIn('## 8.2 ', post(client))      # ถอด key แล้วก็ยังได้คำตอบเดิมที่จำไว้
            with patch.object(application, 'answer_memory', temp_memory(self)), \
                    patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
                self.assertNotIn('## 8.2 ', post(client))      # ไม่มี key และไม่เคยจำ: วิธีค้นเอง


class ChangingAI:
    """AI ที่ตอบไม่เหมือนเดิมทุกครั้ง (แบบที่ Gemini/Claude ทำจริง): แต่ละครั้งเลือกหัวข้อถัดไปในรายการ"""
    def __init__(self, *prefixes, error_first=False):
        self.sections = [topic_index(p) for p in prefixes]
        self.error_first, self.calls, self.routes = error_first, [], 0

    def __call__(self, system, prompt, schema, static=""):
        self.calls.append(system)
        if self.error_first and len(self.calls) == 1:
            raise urllib.error.URLError('network down')
        if system == ai_select.ROUTE_SYSTEM:
            self.routes += 1
            return {'sections': [self.sections[(self.routes - 1) % len(self.sections)]]}
        return {'paragraphs': []}


class SameAnswerEveryTime(unittest.TestCase):
    """ถามคำถามเดิมกี่รอบก็ต้องได้คำตอบเดิม แม้ AI จะตอบไม่เหมือนเดิมทุกครั้ง"""
    Q = 'ชนิดข้อมูลใน SQL มีอะไรบ้าง'

    def setUp(self):
        env = patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key', 'ANTHROPIC_API_KEY': '', 'AI_PROVIDER': ''})
        env.start()
        self.addCleanup(env.stop)

    def use(self, fake):
        p = patch.object(ai_select, '_generate', fake)
        p.start()
        self.addCleanup(p.stop)
        return fake

    def ask(self, q, memory):
        return kb.answer_from_dataset([{'role': 'user', 'content': q}], selector=ai_select.plan_answer, memory=memory)

    def test_ai_itself_is_not_repeatable(self):
        # ไม่มีที่จำคำตอบ: AI ตอบต่างกันแต่ละรอบ คำตอบของบอทก็ต่างตาม (ปัญหาที่ต้องแก้)
        self.use(ChangingAI('8.2 ', '1.2 '))
        self.assertNotEqual(ask(self.Q, selector=ai_select.plan_answer), ask(self.Q, selector=ai_select.plan_answer))

    def test_same_question_same_answer(self):
        fake = self.use(ChangingAI('8.2 ', '1.2 ', '8.6 '))
        memory = temp_memory(self)
        first = self.ask(self.Q, memory)
        routes = fake.routes
        for q in [self.Q, self.Q + 'ครับ', self.Q + ' ?', 'ชนิดข้อมูล ใน sql มีอะไรบ้าง', self.Q]:
            self.assertEqual(self.ask(q, memory), first)
        self.assertEqual(fake.routes, routes)             # ถามซ้ำไม่เรียก AI อีก
        self.assertIn('## 8.2 ', first)

    def test_answer_survives_restart(self):
        fake = self.use(ChangingAI('8.2 ', '1.2 '))
        memory = temp_memory(self)
        first = self.ask(self.Q, memory)
        again = AnswerMemory(memory.path, writable=True)   # เปิดเซิร์ฟเวอร์ใหม่ อ่านไฟล์เดิม
        calls = len(fake.calls)
        self.assertEqual(self.ask(self.Q, again), first)
        self.assertEqual(len(fake.calls), calls)
        saved = json.loads(Path(memory.path).read_text(encoding='utf-8'))
        self.assertEqual(saved['book'], kb.DOCUMENT_META['markdown_sha256'])
        entry = saved['answers'][kb.question_key(self.Q)]
        self.assertEqual(entry['plan'][0]['topic'], kb.ENTRIES[topic_index('8.2 ')]['topic'])
        self.assertEqual(entry['source'], 'AI test-model')

    def test_answer_given_while_ai_was_down_is_kept(self):
        # ครั้งแรก AI ใช้ไม่ได้ ตอบด้วยวิธีค้นเอง -> ครั้งต่อไป AI กลับมาแล้วก็ยังตอบแบบเดิม ไม่เปลี่ยนเอง
        self.use(ChangingAI('8.2 ', error_first=True))
        memory = temp_memory(self)
        first = self.ask(self.Q, memory)
        self.assertEqual(first, ask(self.Q))              # ตรงกับวิธีค้นเอง
        self.assertEqual(self.ask(self.Q, memory), first)
        self.assertIn('ค้นเอง', memory.get(kb.question_key(self.Q), kb.DOCUMENT_META['markdown_sha256'])['source'])

    def test_read_only_memory_never_calls_ai_live(self):
        # บน Vercel (อ่านอย่างเดียว): คำถามที่จำไว้ได้คำตอบที่จำ คำถามใหม่ได้วิธีค้นเอง ไม่เรียก AI สด
        book = kb.DOCUMENT_META['markdown_sha256']
        pinned = temp_memory(self)
        pinned.put(kb.question_key(self.Q), book, [{'topic': kb.ENTRIES[topic_index('8.2 ')]['topic'], 'picked': None}], 'AI')
        site = AnswerMemory(pinned.path, writable=False)
        fake = self.use(ChangingAI('1.2 '))
        self.assertIn('## 8.2 ', self.ask(self.Q, site))
        other = 'หาค่าเฉลี่ยใน sql ใช้คำสั่งอะไร'
        self.assertEqual(self.ask(other, site), ask(other))
        self.assertEqual(fake.calls, [])

    def test_stale_memory_is_ignored(self):
        memory = temp_memory(self)
        topic = kb.ENTRIES[topic_index('8.2 ')]['topic']
        memory.put(kb.question_key(self.Q), 'old-book', [{'topic': topic, 'picked': None}], 'AI')
        fake = self.use(ChangingAI('1.2 '))
        self.assertIn('## 1.2 ', self.ask(self.Q, memory))      # ตำราเปลี่ยน คำตอบเก่าใช้ไม่ได้
        self.assertEqual(fake.routes, 1)
        book = kb.DOCUMENT_META['markdown_sha256']
        memory.put(kb.question_key(self.Q), book, [{'topic': 'หัวข้อที่ไม่มีแล้ว', 'picked': None}], 'AI')
        self.assertIn('## 1.2 ', self.ask(self.Q, memory))      # อ้างหัวข้อที่ไม่มี -> ตอบใหม่
        self.assertIsNone(kb.plan_from_json([{'topic': topic, 'picked': [99999]}]))

    def test_confident_questions_are_not_stored(self):
        memory = temp_memory(self)
        for q in ['ทูเพิลคืออะไร', '7.5', 'ชนิดของแฟ้มข้อมูล']:
            self.ask(q, memory)
        self.assertEqual(memory.data['answers'], {})             # วิธีค้นเองได้ผลเดิมทุกครั้งอยู่แล้ว

    def test_question_key(self):
        for a, b in [('SQL คืออะไร', 'sql คืออะไรครับ?'), ('sql คืออะไร', 'sql  คือ อะไร'),
                     ('ชนิดข้อมูลใน SQL', 'ชนิดข้อมูล ใน sql นะคะ')]:
            self.assertEqual(kb.question_key(a), kb.question_key(b))
        self.assertEqual(kb.question_key('คะแนนสอบ'), 'คะแนนสอบ')   # "คะ" ในคำไม่ถูกตัด


class FakeClaude:
    """แทน anthropic.Anthropic: จำคำขอที่ส่งไป และตอบตามที่กำหนด"""
    requests, reply, stop = [], '{"sections": []}', 'end_turn'

    def __init__(self, **kwargs):
        self.options = kwargs
        self.messages = self

    def create(self, **kwargs):
        FakeClaude.requests.append(kwargs)
        return SimpleNamespace(stop_reason=FakeClaude.stop, content=[
            SimpleNamespace(type='thinking', thinking=''), SimpleNamespace(type='text', text=FakeClaude.reply)])


class ClaudeRequest(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-test', 'GEMINI_API_KEY': 'g-test',
                                      'ANTHROPIC_MODEL': '', 'AI_PROVIDER': ''})
        env.start()
        self.addCleanup(env.stop)
        client = patch.object(ai_select.anthropic, 'Anthropic', FakeClaude)
        client.start()
        self.addCleanup(client.stop)
        ai_select._CLIENT.clear()
        FakeClaude.requests, FakeClaude.stop = [], 'end_turn'

    def test_claude_is_used_when_its_key_is_set(self):
        self.assertEqual((ai_select.provider(), ai_select.model_label()), ('anthropic', 'claude-sonnet-5'))
        with patch.dict(os.environ, {'AI_PROVIDER': 'gemini'}):
            self.assertEqual(ai_select.provider(), 'gemini')

    def test_route_request(self):
        i = topic_index('8.2 ')
        FakeClaude.reply = json.dumps({'sections': [i, 9999]})
        self.assertEqual(ai_select.route('ชนิดข้อมูลใน SQL มีอะไรบ้าง'), [i])
        req = FakeClaude.requests[0]
        self.assertEqual(req['model'], 'claude-sonnet-5')
        self.assertEqual(req['messages'], [{'role': 'user', 'content': 'คำถาม: ชนิดข้อมูลใน SQL มีอะไรบ้าง'}])
        fmt = req['output_config']['format']
        self.assertEqual(fmt['type'], 'json_schema')
        self.assertFalse(fmt['schema']['additionalProperties'])
        self.assertEqual(req['output_config']['effort'], 'low')
        self.assertNotIn('temperature', req)                        # Sonnet 5 ไม่รับ temperature
        # รายชื่อหัวข้อทั้งเล่มเหมือนกันทุกคำถาม: อยู่ก่อนคำถามและทำ prompt cache
        self.assertEqual(req['system'][0]['text'], ai_select.ROUTE_SYSTEM)
        self.assertEqual(req['system'][1]['cache_control'], {'type': 'ephemeral'})
        self.assertTrue(req['system'][1]['text'].startswith('หัวข้อในตำรา:\n0. '))
        with patch.dict(os.environ, {'ANTHROPIC_MODEL': 'claude-haiku-4-5'}):
            ai_select.route('x')
            self.assertNotIn('effort', FakeClaude.requests[-1]['output_config'])

    def test_refusal_falls_back_to_search(self):
        FakeClaude.stop = 'refusal'
        q = 'ชนิดข้อมูลใน SQL มีอะไรบ้าง'
        self.assertIsNone(ai_select.plan_answer(q))
        self.assertEqual(ask(q, selector=ai_select.plan_answer), ask(q))
        self.assertIn(ai_select.anthropic.APIError, ai_select._ERRORS)   # 429/5xx/เน็ตหลุด ก็กลับไปค้นเองเช่นกัน


if __name__ == '__main__':
    unittest.main()

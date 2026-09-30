import json
import unittest
from pathlib import Path
import knowledge_base as kb


class DatasetTests(unittest.TestCase):
    def test_retrieval(self):
        for query, expected in [('COUNT()', 'Aggregate'), ('GROUP BY', 'GROUP BY'), ('HAVING', 'GROUP BY'),
                                ('LEFT JOIN', 'LEFT JOIN'), ('คีย์หลักคืออะไร', 'Primary Key'),
                                ('foreign key', 'Foreign Key'), ('3NF', 'นอมอลฟอร์มระดับที่ 3'),
                                ('นอร์มัลไลเซชันคืออะไร', 'แนวคิดการนอมอลไลเซชัน'),
                                ('weak entity', 'อ่อนแอ'), ('ER Diagram คืออะไร', '5.1'),
                                ('DBMS คืออะไร', 'ระบบจัดการฐานข้อมูล'),
                                ('ข้อมูลกับสารสนเทศต่างกันยังไง', 'สารสนเทศ'),
                                ('what is sql', 'ความหมายของภาษา SQL'), ('ภาษา SQL คืออะไร', 'ความหมายของภาษา SQL'),
                                ('ภาษา DDL คืออะไร', 'ความหมายของภาษา SQL'), ('7.5', 'นอมอลฟอร์มระดับที่ 1'),
                                ('แบบฝึกหัดบทที่ 7', 'แบบฝึกหัดท้ายบท บทที่ 7')]:
            with self.subTest(query=query):
                self.assertIn(expected, kb.search(query, 1)[0]['topic'])

    def test_unrelated(self):
        # รวมเรื่อง SQL ที่ตำราไม่ได้อธิบาย แม้บางคำจะโผล่ในเนื้อหา (เช่น Transaction ในตาราง)
        for query in ['ราคาทองวันนี้', 'weather today', 'เขียนเพลงรัก', 'quantum computer คืออะไร',
                      'วิธีทำต้มยำกุ้ง', 'ฟุตบอลคืนนี้ใครชนะ', 'python list comprehension',
                      'CTE', 'ROW_NUMBER', 'Transaction', 'stored procedure', 'SQL Injection',
                      # ชื่อระบบที่มีคำว่า sql ไม่ใช่คำถาม "SQL คืออะไร" และภาคผนวกที่ตำราไม่มี
                      'MySQL คืออะไร', 'NoSQL คืออะไร', 'what is sqlite', 'PostgreSQL คืออะไร', 'ภาคผนวก ค',
                      # ภาษาโปรแกรมอื่น เคยได้หัวข้อ "8.1 ความหมายของภาษา SQL" เพราะคำว่า "ภาษา"
                      'ภาษา C คืออะไร', 'ภาษา c', 'ภาษา Python คืออะไร', 'ภาษา Java', 'ภาษา C++', 'ภาษา PHP']:
            with self.subTest(query=query):
                self.assertEqual(kb.search(query), [])
                self.assertEqual(kb.answer_from_dataset([{'role': 'user', 'content': query}]), kb.NO_DATA)

    def test_no_unrelated_second_topic(self):
        # หัวข้อที่แค่มีคำซ้ำกับคำถาม ไม่ถูกดึงมาปน
        for query, only in [('DBMS คืออะไร', '2.3 '), ('ข้อดีของฐานข้อมูล', '2.5 '), ('พจนานุกรมข้อมูล', '6.8 '),
                            ('SELECT ใช้ยังไง', '9.2 '), ('นอร์มัลไลเซชันคืออะไร', '7.1 '), ('normalization', '7.1 '),
                            ('ERD', '5.1 '), ('ความสัมพันธ์แบบกลุ่มต่อกลุ่ม', '5.6 ')]:
            with self.subTest(query=query):
                found = kb.search(query, 3)
                self.assertEqual(len(found), 1, [e['topic'] for e in found])
                self.assertTrue(found[0]['topic'].startswith(only))

    def test_question_about_two_things_gets_both(self):
        for query, starts in [('INNER JOIN กับ LEFT JOIN ต่างกันยังไง', ['10.5 ', '10.6 ']),
                              ('คีย์หลักกับคีย์นอกต่างกันยังไง', ['4.5 ประเภทของคีย์ · 3.', '4.5 ประเภทของคีย์ · 4.']),
                              ('UPDATE กับ DELETE ต่างกันยังไง', ['8.7 ', '8.8 ']),
                              ('1NF 2NF 3NF', ['7.5 ', '7.6 ', '7.7 '])]:
            with self.subTest(query=query):
                self.assertEqual([e['topic'][:len(s)] for e, s in zip(kb.search(query, 3), starts)], starts)

    def test_whole_section_is_not_cut(self):
        # หัวข้อที่ถูกแบ่งส่วน ถามหัวข้อหลักต้องได้ครบทุกส่วน ไม่ใช่แค่ย่อหน้านำ ("…ดังรายละเอียดต่อไปนี้")
        ask = lambda q: kb.answer_from_dataset([{'role': 'user', 'content': q}])
        for query in ['ประเภทของคีย์', 'คีย์มีกี่ประเภท', '4.5']:
            with self.subTest(query=query):
                answer = ask(query)
                for part in [e for e in kb.ENTRIES if e['topic'].startswith('4.5 ประเภทของคีย์')]:
                    self.assertIn(kb.with_figures(part['description']), answer)   # เนื้อหาครบ (พร้อมรูปในตำรา)
        # ถามเจาะจงส่วนเดียว ได้ส่วนนั้นส่วนเดียว
        answer = ask('คีย์หลักคืออะไร')
        self.assertIn('## 4.5 ประเภทของคีย์ · 3. คีย์หลัก (Primary Key)', answer)
        self.assertNotIn('คีย์สำรอง (Alternate Key)', answer)
        self.assertIn('5.3 เอ็นทิตี้ · 2. เอ็นทิตี้แบบอ่อนแอ', ask('เอ็นทิตี้มีกี่ประเภท'))

    def test_small_talk(self):
        ask = lambda q: kb.answer_from_dataset([{'role': 'user', 'content': q}])
        # ถามว่าบอทตอบอะไรได้ ต้องได้รายชื่อบทจากตำรา ไม่ใช่ "ไม่มีข้อมูล"
        for q in ['คุณตอบอะไรได้บ้าง', 'บอททำอะไรได้บ้าง', 'ถามอะไรได้บ้างครับ', 'help', 'สวัสดีครับ คุณตอบอะไรได้บ้าง']:
            with self.subTest(q=q):
                self.assertIn('บทที่ 7 การนอมอลไลเซชัน', ask(q))
        for q in ['สวัสดีครับ', 'หวัดดี', 'hi']:
            with self.subTest(q=q):
                self.assertTrue(ask(q).startswith('สวัสดีครับ'))
        for q in ['ขอบคุณครับ', 'ขอบคุณมากๆครับ', 'thanks']:
            with self.subTest(q=q):
                self.assertTrue(ask(q).startswith('ยินดีครับ'))
        # คำถามเนื้อหาที่หน้าตาคล้ายกัน ต้องไปค้นในตำราตามปกติ
        self.assertIn('8.1 ความหมายของภาษา SQL', ask('SQL ทำอะไรได้บ้าง'))
        self.assertIn('9.11', ask('สวัสดี GROUP BY'))
        self.assertEqual(ask('history'), kb.NO_DATA)

    def test_grounded_fields(self):
        for entry in kb.ENTRIES:
            answer = kb.answer_from_dataset([{'role': 'user', 'content': entry['topic']}])
            self.assertTrue(answer)
        for query in ['COUNT()', 'GROUP BY', 'คีย์หลัก', 'LEFT JOIN']:
            entries = kb.search(query, 2)
            answer = kb.answer_from_dataset([{'role': 'user', 'content': query}])
            for entry in entries:
                self.assertIn(entry['description'], answer)
                self.assertIn(entry['source'], answer)

    def test_sources(self):
        manifest = json.loads(Path(kb.MANIFEST_PATH).read_text(encoding='utf-8'))
        self.assertEqual(len(kb.ENTRIES), manifest['topic_count'])
        self.assertTrue(all(e['source'] == 'db_business_textbook_th.md' for e in kb.ENTRIES))
        self.assertEqual([e['topic'] for e in kb.ENTRIES], manifest['topics'])
        # ทุกหัวข้อบอกบทและเลขหน้า และคำตอบต้องแสดงให้ผู้ใช้เห็น
        for e in kb.ENTRIES:
            with self.subTest(topic=e['topic']):
                self.assertRegex(e['references'], r'(บทที่ \d+|ภาคผนวก [กข]) .+ · หน้า \d+(–\d+)? \(PDF หน้า \d+(–\d+)?\)$')
        answer = kb.answer_from_dataset([{'role': 'user', 'content': 'คีย์หลักคืออะไร'}])
        self.assertIn('บทที่ 4 แบบจำลองฐานข้อมูลเชิงสัมพันธ์ · หน้า 69–70 (PDF หน้า 96–97)', answer)


if __name__ == '__main__':
    unittest.main()

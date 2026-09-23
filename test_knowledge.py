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
                                ('what is sql', 'ความหมายของภาษา SQL'), ('7.5', 'นอมอลฟอร์มระดับที่ 1'),
                                ('แบบฝึกหัดบทที่ 7', 'แบบฝึกหัดท้ายบท บทที่ 7')]:
            with self.subTest(query=query):
                self.assertIn(expected, kb.search(query, 1)[0]['topic'])

    def test_unrelated(self):
        # รวมเรื่อง SQL ที่ตำราไม่ได้อธิบาย แม้บางคำจะโผล่ในเนื้อหา (เช่น Transaction ในตาราง)
        for query in ['ราคาทองวันนี้', 'weather today', 'เขียนเพลงรัก', 'quantum computer คืออะไร',
                      'วิธีทำต้มยำกุ้ง', 'ฟุตบอลคืนนี้ใครชนะ', 'python list comprehension',
                      'CTE', 'ROW_NUMBER', 'Transaction', 'stored procedure', 'SQL Injection']:
            with self.subTest(query=query):
                self.assertEqual(kb.search(query), [])
                self.assertEqual(kb.answer_from_dataset([{'role': 'user', 'content': query}]), kb.NO_DATA)

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


if __name__ == '__main__':
    unittest.main()

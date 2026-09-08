import unittest
import knowledge_base as kb


class DatasetTests(unittest.TestCase):
    def test_retrieval(self):
        for query, expected in [('COUNT()', 'COUNT'), ('CTE', 'CTE'),
                                ('ROW_NUMBER', 'Window'), ('SQL Injection', 'Injection'),
                                ('CREATE VIEW', 'VIEW'), ('what is sql', 'SQL คืออะไร')]:
            with self.subTest(query=query):
                self.assertIn(expected, kb.search(query, 1)[0]['topic'])

    def test_unrelated(self):
        for query in ['ราคาทองวันนี้', 'weather today', 'เขียนเพลงรัก', 'quantum computer คืออะไร']:
            self.assertEqual(kb.search(query), [])

    def test_grounded_fields(self):
        for entry in kb.ENTRIES:
            answer = kb.answer_from_dataset([{'role': 'user', 'content': entry['topic']}])
            self.assertTrue(answer)
        for query in ['COUNT()', 'CTE', 'ROW_NUMBER', 'SQL Injection']:
            entries = kb.search(query, 2)
            answer = kb.answer_from_dataset([{'role': 'user', 'content': query}])
            for entry in entries:
                self.assertIn(entry['description'], answer)
                self.assertIn(entry['source'], answer)

    def test_sources(self):
        added = [e for e in kb.ENTRIES if e['source'] == 'sql_handbook_th.md']
        self.assertEqual(len(added), 99)
        self.assertTrue(all('https://' in e['references'] for e in added))


if __name__ == '__main__':
    unittest.main()

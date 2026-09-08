"""Offline route checks: never loads .env or contacts a model."""
import unittest
from unittest.mock import patch

with patch('dotenv.load_dotenv', return_value=False):
    import app as application


class HandbookRoutes(unittest.TestCase):
    def test_downloads_and_catalog(self):
        with application.app.test_client() as client:
            for path in ['/', '/handbook.pdf', '/handbook.md']:
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()
            self.assertEqual(len(client.get('/knowledge/topics').json), 99)

    def test_dataset_answer(self):
        with application.app.test_client() as client, patch.object(application, 'save_web_chat'):
            response = client.post('/chat/stream', json={'message': 'UPSERT ON CONFLICT'})
            self.assertEqual(response.status_code, 200)
            text = response.get_data(as_text=True)
            self.assertIn('sql_handbook_th.md', text)
            self.assertIn('postgresql.org', text)


if __name__ == '__main__':
    unittest.main()

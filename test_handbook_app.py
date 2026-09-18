"""Offline route checks: never loads .env or contacts a model."""
import unittest
from unittest.mock import patch

with patch('dotenv.load_dotenv', return_value=False):
    import app as application


class HandbookRoutes(unittest.TestCase):
    def test_home_page_without_removed_resources(self):
        with application.app.test_client() as client:
            self.assertEqual(client.get('/').status_code, 200)
            for path in ['/handbook.pdf', '/handbook.md', '/knowledge/topics']:
                self.assertEqual(client.get(path).status_code, 404)

    def test_dataset_answer(self):
        with application.app.test_client() as client, patch.object(application, 'save_web_chat'):
            response = client.post('/chat/stream', json={'message': 'UPSERT ON CONFLICT'})
            self.assertEqual(response.status_code, 200)
            text = response.get_data(as_text=True)
            self.assertIn('sql_handbook_th.md', text)
            self.assertIn('postgresql.org', text)


if __name__ == '__main__':
    unittest.main()

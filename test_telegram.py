"""Offline Telegram webhook checks: never contacts Telegram."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

with patch('dotenv.load_dotenv', return_value=False):
    import app as application

REAL_LOAD = application.load_line_history


class TelegramWebhook(unittest.TestCase):
    def post(self, body, secret='s3cret'):
        with application.app.test_client() as client:
            return client.post('/telegram', json=body,
                               headers={'X-Telegram-Bot-Api-Secret-Token': secret})

    def setUp(self):
        patches = [patch.object(application, 'TELEGRAM_BOT_TOKEN', 'token'),
                   patch.object(application, 'TELEGRAM_WEBHOOK_SECRET', 's3cret'),
                   patch.object(application, 'save_line_history'),
                   patch.object(application, 'load_line_history', return_value=[])]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.sent = []
        send = patch.object(application, 'telegram_send', side_effect=lambda c, t: self.sent.append((c, t)))
        send.start()
        self.addCleanup(send.stop)

    def test_answers_from_handbook(self):
        r = self.post({'message': {'chat': {'id': 42}, 'text': 'LEFT JOIN'}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.sent[0][0], 42)
        self.assertIn('LEFT JOIN', self.sent[0][1])
        self.assertNotIn('```', self.sent[0][1])

    def test_long_answer_keeps_source(self):
        self.post({'message': {'chat': {'id': 5}, 'text': '12.5 การสร้างระบบรักษาความปลอดภัยสำหรับผู้ใช้'}})
        text = self.sent[0][1]
        self.assertLessEqual(len(text), 4000)
        self.assertIn(application.TRIMMED_NOTE, text)
        self.assertIn('แหล่งข้อมูล:', text)
        self.assertIn('PDF หน้า', text)   # ตัดข้อความยาวแล้วยังเห็นบทและเลขหน้า

    def test_malformed_updates_are_ignored(self):
        for body in [[1], {'message': 'hi'}, {'message': {'chat': 5, 'text': 'x'}},
                     {'message': {'chat': {'id': 1}, 'text': 5}}]:
            with self.subTest(body=body):
                self.assertEqual(self.post(body).status_code, 200)
        self.assertEqual(self.sent, [])

    def test_corrupted_history_file_still_answers(self):
        # ไฟล์ประวัติเสียเคยทำให้ทุกข้อความของแชตนั้น 500 ตลอดไป
        with tempfile.TemporaryDirectory() as tmp, patch.object(application, 'DATA_DIR', tmp), \
                patch.object(application, 'load_line_history', REAL_LOAD):
            for chat_id, bad in [(9, '{"a": 1}'), (10, '[1, 2, "x"]'), (11, 'not json')]:
                with self.subTest(bad=bad):
                    Path(tmp, f'tg_{chat_id}.json').write_text(bad, encoding='utf-8')
                    self.sent.clear()
                    r = self.post({'message': {'chat': {'id': chat_id}, 'text': 'GROUP BY'}})
                    self.assertEqual(r.status_code, 200)
                    self.assertIn('GROUP BY', self.sent[0][1])

    def test_rejects_wrong_secret(self):
        self.assertEqual(self.post({'message': {'chat': {'id': 1}, 'text': 'x'}}, secret='bad').status_code, 403)
        self.assertEqual(self.sent, [])

    def test_start_and_non_text(self):
        self.post({'message': {'chat': {'id': 7}, 'text': '/start'}})
        self.post({'message': {'chat': {'id': 7}, 'sticker': {}}})
        self.assertEqual(len(self.sent), 1)
        self.assertIn('ครูเอสคิว', self.sent[0][1])

    def test_disabled_without_token(self):
        with patch.object(application, 'TELEGRAM_BOT_TOKEN', ''):
            self.assertEqual(self.post({}).status_code, 404)


if __name__ == '__main__':
    unittest.main()

# Ch-Bot — ครูเอสคิว (ผู้เชี่ยวชาญ SQL)

แชตบอทฐานข้อมูลและ SQL ตอบภาษาไทย โดยดึงคำตอบจากตำรา
**การจัดการระบบฐานข้อมูลเพื่องานธุรกิจ** (ฐาปนี เพ็งสุข, ม.ราชภัฏอุดรธานี, 2562) 426 หน้า
ที่แปลงเป็น [`knowledge/db_business_textbook_th.md`](knowledge/db_business_textbook_th.md) เท่านั้น ไม่ใช้ AI แต่งคำตอบ
ใช้งานได้ทั้งผ่านหน้าเว็บ, LINE และ Telegram

> โปรเจกต์นี้เป็น **Python / Flask** ไม่ใช่ Node.js — ใช้ `npm start` ไม่ได้ครับ

## วิธีรัน

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python app.py
```

แล้วเปิดเบราว์เซอร์ที่ http://127.0.0.1:5001 — ไม่ต้องใช้ API key
ส่วน `LINE_CHANNEL_ACCESS_TOKEN` และ `LINE_CHANNEL_SECRET` ใน `.env` ใส่เฉพาะตอนจะต่อ LINE

## โครงสร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `app.py` | เซิร์ฟเวอร์ Flask, หน้าเว็บ, LINE webhook (`/callback`), Telegram webhook (`/telegram`) |
| `knowledge_base.py` | โหลดตำรา ตรวจ checksum และค้นหัวข้อที่ตรงกับคำถาม |
| `knowledge/db_business_textbook_th.md` | ฐานข้อมูลความรู้ 172 หัวข้อ แปลงจาก PDF ตามสารบัญ (ไฟล์เดียวที่บอทใช้) |
| `output/pdf/db_business_textbook_th.pdf` | ตำรา PDF ต้นฉบับ 426 หน้า ใช้ยืนยันว่าเนื้อหาตรงฉบับ |
| `output/pdf/manifest.json` | ชื่อไฟล์ checksum ของ MD และ PDF และรายชื่อหัวข้อ |
| `templates/index.html` | หน้าเว็บแชต |
| `data/` | ประวัติแชตเป็นไฟล์ JSON (ไม่ขึ้น git) |

## วิธีตอบ

บอทเลือกหัวข้อที่ตรงกับคำถาม แล้วแสดงเนื้อหาหัวข้อนั้นจากตำราตรง ๆ (รวมคำสั่ง SQL ในเล่ม)
ถ้าไม่มีหัวข้อในตำราที่ตรงกับคำถาม จะตอบว่า "ไม่มีข้อมูลเรื่องนี้ในตำราครับ"
คำที่แค่โผล่ในเนื้อหา (เช่น Transaction ในตาราง) ไม่นับว่าตำราอธิบายเรื่องนั้น
บอทจึงไม่แต่งเนื้อหาเอง แต่ก็เขียน query ใหม่ตามโจทย์ให้ไม่ได้

หัวข้อคือหัวข้อย่อยตามสารบัญ (เช่น 4.5, 9.11) บวกบทนำ บทสรุป และแบบฝึกหัดของแต่ละบท
หัวข้อที่ยาวเกิน ~3,500 ตัวอักษรถูกแบ่งตามหัวข้อย่อยในเล่ม เช่น `4.5 ประเภทของคีย์ · 3. คีย์หลัก (Primary Key)`
ถามด้วยเลขหัวข้อ (`7.5`) หรือบท (`แบบฝึกหัดบทที่ 7`) ได้ ภาพและแผนภาพในเล่มไม่ได้ถูกแปลงมา
บน LINE/Telegram คำตอบที่ยาวเกินหนึ่งข้อความจะถูกตัด โดยยังเก็บบรรทัดแหล่งข้อมูลไว้

ก่อนตอบทุกครั้งระบบตรวจว่า MD และ PDF ตรงกับ `manifest.json` ถ้าไม่ตรงจะหยุดตอบ
ดังนั้นเวลาแก้เนื้อหา ต้องแก้ MD และ PDF ไปด้วยกัน แล้วอัปเดต checksum และ `topic_count` ใน manifest ด้วย

## ทดสอบ

```bash
./venv/bin/python -m unittest test_knowledge test_handbook_app test_dataset_only test_telegram -v
```

## Deploy ขึ้น Vercel

Vercel ตรวจจับ Flask ให้อัตโนมัติ (entrypoint `app.py`, ตัวแปร `app`) — ไม่ต้องมี `vercel.json`

1. Import repo นี้ที่ https://vercel.com/new
2. ถ้าใช้ LINE ใส่ `LINE_CHANNEL_ACCESS_TOKEN` และ `LINE_CHANNEL_SECRET` ใน Environment Variables
3. Deploy แล้วตั้ง LINE Webhook URL เป็น `https://<โปรเจกต์>.vercel.app/callback`

### ข้อจำกัดบน Vercel

- **แชตหน้าเว็บ** เก็บประวัติไว้ใน `localStorage` ของเบราว์เซอร์ ไม่หายเมื่อรีเฟรช แต่ถ้าเปลี่ยนเครื่องหรือล้าง cache จะไม่เห็นแชทเก่า
- **ประวัติแชต LINE ไม่ถาวร** — Vercel เขียนไฟล์ได้เฉพาะ `/tmp` ถ้าต้องการให้จำจริงต้องต่อฐานข้อมูลภายนอก แล้วแก้ `load_line_history` / `save_line_history`

## ต่อกับ Telegram

1. ใน Telegram คุยกับ **@BotFather** → พิมพ์ `/newbot` → ตั้งชื่อ → ได้ **bot token**
2. สุ่ม secret ยาว ๆ มาหนึ่งค่า เช่น `python3 -c "import secrets; print(secrets.token_hex(24))"`
3. ใส่ `TELEGRAM_BOT_TOKEN` และ `TELEGRAM_WEBHOOK_SECRET` ใน Vercel → Settings → Environment Variables แล้ว Redeploy
4. บอก Telegram ให้ส่งข้อความมาที่เว็บเรา (รันครั้งเดียวจากเครื่องตัวเอง):

   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://<โปรเจกต์>.vercel.app/telegram" \
     -d "secret_token=<SECRET>"
   ```

   ต้องได้ `{"ok":true,...}` แล้วลองทักบอทใน Telegram ได้เลย
   ตรวจสถานะได้ที่ `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

ถ้าไม่ได้ตั้ง token หรือ secret route `/telegram` จะปิดตัวเอง (ตอบ 404)
ประวัติแชต Telegram เก็บใน `data/tg_<chat_id>.json` และบน Vercel ไม่ถาวรเหมือน LINE

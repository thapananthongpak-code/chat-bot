# Ch-Bot — ครูเอสคิว (ผู้เชี่ยวชาญ SQL)

แชตบอทผู้เชี่ยวชาญด้าน SQL และฐานข้อมูล ตอบภาษาไทย โดยอ้างอิงคลังความรู้จากไฟล์ CSV ใน [`knowledge/`](knowledge/)
ใช้งานได้ทั้งผ่านหน้าเว็บและ LINE

> โปรเจกต์นี้เป็น **Python / Flask** ไม่ใช่ Node.js — ใช้ `npm start` ไม่ได้ครับ

## วิธีรัน

**1. ติดตั้ง dependencies** (ทำครั้งเดียว)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

**2. ใส่ API key** — เปิดไฟล์ `.env` แล้วเติม key ของ Anthropic (https://console.anthropic.com/settings/keys)

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

โมเดลที่ใช้คือ `claude-haiku-4-5` เปลี่ยนได้โดยใส่ `ANTHROPIC_MODEL` ใน `.env`

ส่วน `LINE_CHANNEL_ACCESS_TOKEN` และ `LINE_CHANNEL_SECRET` ใส่เฉพาะตอนจะต่อ LINE ถ้ารันแค่หน้าเว็บ ปล่อยว่างไว้ได้

**3. รันเซิร์ฟเวอร์**

```bash
./venv/bin/python app.py
```

แล้วเปิดเบราว์เซอร์ที่ http://127.0.0.1:5001

## โครงสร้าง

| ไฟล์ | หน้าที่ |
|---|---|
| `app.py` | เซิร์ฟเวอร์ Flask, system prompt, เชื่อม Claude API และ LINE webhook |
| `knowledge_base.py` | โหลด CSV และค้นหาหัวข้อที่ตรงกับคำถาม เพื่อแนบไปกับ prompt |
| `knowledge/*.csv` | คลังความรู้ SQL (หัวข้อ / คำอธิบาย / รูปแบบคำสั่ง / ตัวอย่าง) |
| `templates/index.html` | หน้าเว็บแชต พร้อมไฮไลต์โค้ด SQL |
| `data/` | ประวัติแชตเป็นไฟล์ JSON — `web_<chat_id>.json` และ `line_<user_id>.json` (ไม่ขึ้น git) |

## ขอบเขตคำตอบ

ค่าเริ่มต้นคือ **โหมดเข้ม** (`STRICT_KNOWLEDGE=1`) บอทจะตอบเฉพาะเนื้อหาที่อยู่ใน
`knowledge/` เท่านั้น ถ้าถามเรื่องที่ไม่มีในคลัง จะบอกตรง ๆ ว่าไม่มี แล้วแนะนำหัวข้อ
ใกล้เคียงที่มีอยู่ แทนที่จะตอบจากความรู้ทั่วไปของโมเดล

ตั้ง `STRICT_KNOWLEDGE=0` ใน `.env` ถ้าอยากให้ตอบจากความรู้ SQL ทั่วไปได้ด้วยเมื่อไม่มีในคลัง

## เพิ่มความรู้ให้บอท

วางไฟล์ `.csv` เพิ่มใน `knowledge/` โดยใช้ 4 คอลัมน์เดิม (หัวข้อ, คำอธิบาย, คำสั่ง SQL, ตัวอย่าง)
ช่องที่ไม่มีข้อมูลใส่ `-` ได้ แล้วรันเซิร์ฟเวอร์ใหม่ ระบบจะโหลดให้อัตโนมัติ

## Deploy ขึ้น Vercel

Vercel ตรวจจับ Flask ให้อัตโนมัติ เพราะ entrypoint ชื่อ `app.py` และมีตัวแปรชื่อ `app` — ไม่ต้องมี `vercel.json`

1. Import repo นี้ที่ https://vercel.com/new
2. ใส่ Environment Variables ในหน้า Settings ของโปรเจกต์ (ห้าม commit ไฟล์ `.env` ขึ้น git)

   | ตัวแปร | จำเป็น |
   |---|---|
   | `ANTHROPIC_API_KEY` | ใช่ |
   | `ANTHROPIC_MODEL` | ไม่ (ค่าเริ่มต้น `claude-haiku-4-5`) |
   | `LINE_CHANNEL_ACCESS_TOKEN` | เฉพาะตอนใช้ LINE |
   | `LINE_CHANNEL_SECRET` | เฉพาะตอนใช้ LINE |

3. Deploy แล้วตั้ง LINE Webhook URL เป็น `https://<โปรเจกต์>.vercel.app/callback`

### ข้อจำกัดบน Vercel ที่ควรรู้

- **แชตหน้าเว็บ** เก็บประวัติเป็นไฟล์ JSON ใน `data/` เมื่อรันในเครื่อง แต่บน Vercel เขียนได้แค่ `/tmp` ระบบจะถอยไปใช้ประวัติที่เบราว์เซอร์ส่งมาแทนโดยอัตโนมัติ (ยังคุยต่อเนื่องได้ แต่รายการแชทย้อนหลังจะไม่ถาวร)
- **ประวัติแชต LINE ไม่ถาวร** — Vercel เขียนไฟล์ได้เฉพาะ `/tmp` ซึ่งอยู่แค่ในอายุของ instance นั้น บอทอาจลืมบทสนทนาเก่าเป็นครั้งคราว ถ้าต้องการให้จำจริงต้องต่อฐานข้อมูลภายนอก (เช่น Vercel KV, Upstash Redis หรือ Postgres) แล้วแก้ `load_line_history` / `save_line_history`
- `Procfile` กับ `runtime.txt` มีไว้สำหรับ host แบบอื่น (Railway/Render) Vercel ไม่ได้ใช้

## ต่อกับ LINE

รันเซิร์ฟเวอร์ให้เข้าถึงจากภายนอกได้ (เช่นผ่าน ngrok หรือ deploy ขึ้น host) แล้วตั้ง Webhook URL
ใน LINE Developers Console เป็น `https://<โดเมนของคุณ>/callback`

# SQL และฐานข้อมูลเพิ่มเติม — เอกสารทางการ


## CTE WITH (คิวรีมีชื่อ)

PostgreSQL: WITH ตั้งชื่อผลลัพธ์ย่อยเพื่อใช้ภายในคำสั่งเดียว ช่วยแบ่งคิวรีซับซ้อนเป็นส่วนย่อย ไม่ใช่การสร้างตารางถาวร

### ตัวอย่าง

```sql
WITH n AS (SELECT 1 AS value) SELECT value FROM n;
```

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/queries-with.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Recursive CTE (คิวรีเรียกซ้ำ)

PostgreSQL: WITH RECURSIVE มีส่วนเริ่มต้นและส่วนเรียกซ้ำ เหมาะกับข้อมูลลำดับชั้น ต้องมีเงื่อนไขหยุดหรือป้องกันวงจร

### ตัวอย่าง

```sql
WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<3) SELECT x FROM n;
```

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/queries-with.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Window Functions ROW_NUMBER OVER PARTITION BY (ฟังก์ชันหน้าต่าง)

PostgreSQL: Window function คำนวณข้ามแถวที่เกี่ยวข้องโดยยังเก็บแถวเดิมไว้ ต่างจาก GROUP BY ที่สรุปหลายแถวเป็นกลุ่ม ROW_NUMBER ให้เลขลำดับตาม ORDER BY ภายในหน้าต่าง

### ตัวอย่าง

```sql
SELECT x, ROW_NUMBER() OVER (ORDER BY x) AS rn FROM (VALUES (20),(10)) AS t(x);
```

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/tutorial-window.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Transaction Isolation MVCC (ระดับการแยกธุรกรรม)

PostgreSQL ใช้ Read Committed เป็นค่าเริ่มต้น แต่ละคำสั่งเห็น snapshot เมื่อคำสั่งเริ่ม Repeatable Read ใช้ snapshot ที่คงที่ในธุรกรรม ส่วน Serializable ตรวจความขัดแย้งเพิ่มเติม แอปต้องรองรับการลองธุรกรรมใหม่เมื่อเกิด serialization failure

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/transaction-iso.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## SQL Injection Prepared Statements (ป้องกันการแทรกคำสั่ง)

แยกข้อความคำสั่ง SQL ออกจากค่าที่ผู้ใช้ป้อนด้วย parameterized queries ห้ามต่อสตริงข้อมูลผู้ใช้เข้า SQL ตรง ๆ ชื่อตารางและคอลัมน์ที่เป็นส่วนโครงสร้างควรเลือกจาก allow-list ไม่ใช่รับข้อความอิสระ ใช้สิทธิ์ฐานข้อมูลเท่าที่จำเป็น รูปแบบ placeholder ขึ้นกับ driver

### แหล่งอ้างอิง

https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Normalization 1NF 2NF 3NF (การออกแบบลดความซ้ำซ้อน)

1NF จัดข้อมูลไม่ให้มีกลุ่มซ้ำในแถว 2NF แยกข้อมูลที่ขึ้นต่อเพียงบางส่วนของคีย์ประกอบ 3NF แยกข้อมูลที่ขึ้นต่อข้อมูลอื่นซึ่งไม่ใช่คีย์ จุดมุ่งหมายคือช่วยลดความซ้ำซ้อนและปัญหาเมื่อเพิ่ม แก้ไข หรือลบข้อมูล

### แหล่งอ้างอิง

https://learn.microsoft.com/en-us/previous-versions/troubleshoot/microsoft-365/microsoft-365-apps/access/database-normalization-description
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## EXPLAIN Query Plan (วิเคราะห์แผนคิวรี)

PostgreSQL: EXPLAIN แสดงแผนที่ planner เลือกและต้นทุนประมาณการ EXPLAIN ANALYZE รันคำสั่งจริงเพื่อวัดผล จึงต้องระวังเมื่อใช้กับคำสั่งแก้ข้อมูล ต้นทุนไม่ใช่เวลาเป็นมิลลิวินาทีโดยตรง

### ตัวอย่าง

```sql
EXPLAIN SELECT 1;
```

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/using-explain.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Index Performance (ประสิทธิภาพดัชนี)

ดัชนีช่วยค้นแถวเป้าหมายได้เร็วขึ้น แต่มีต้นทุนในการจัดเก็บและดูแลเมื่อแก้ข้อมูล ไม่ควรสร้างทุกคอลัมน์โดยไม่วัดผล PostgreSQL มีดัชนีหลายชนิด เช่น B-tree, Hash, GiST, GIN และ BRIN

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/indexes.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Partitioning (แบ่งตาราง)

PostgreSQL แบ่งตารางเชิงตรรกะเป็นส่วนย่อยทางกายภาพได้แบบ range, list และ hash มีประโยชน์กับตารางใหญ่และการจัดการข้อมูลเป็นช่วง ต้องเลือก partition key ให้สัมพันธ์กับรูปแบบการใช้งาน ไม่ได้ทำให้ทุกคิวรีเร็วขึ้นโดยอัตโนมัติ

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/ddl-partitioning.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## JSON JSONB (ข้อมูลกึ่งโครงสร้าง)

PostgreSQL รองรับฟังก์ชันและตัวดำเนินการอ่าน JSON เครื่องหมาย -> คืนค่า JSON ส่วน ->> คืนข้อความ หากโครงสร้างไม่ตรงหรือไม่มี key ตัวดำเนินการดึงข้อมูลจะคืน SQL NULL

### ตัวอย่าง

```sql
SELECT '{"name":"Ada"}'::jsonb ->> 'name' AS name;
```

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/functions-json.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Backup Restore PITR (สำรองและกู้คืน)

PostgreSQL มีแนวทางสำรองหลักคือ SQL dump, สำรองระดับระบบไฟล์ และ continuous archiving ซึ่งรองรับ point-in-time recovery การเลือกวิธีต้องสัมพันธ์กับเวลาหยุดระบบและจุดเวลาที่ต้องการกู้คืน ควรทดสอบกระบวนการกู้คืนด้วย

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/backup.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Replication Standby (ทำสำเนาฐานข้อมูล)

PostgreSQL streaming replication ส่ง WAL ไป standby มีทั้งแบบ asynchronous และ synchronous แบบ asynchronous อาจสูญเสียธุรกรรมล่าสุดเมื่อ primary ล่มก่อนส่งข้อมูล ส่วน synchronous เพิ่มการรอยืนยันจาก standby ตามการตั้งค่า

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/warm-standby.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Row Level Security RLS (สิทธิ์ระดับแถว)

PostgreSQL RLS ใช้นโยบายจำกัดแถวที่ผู้ใช้มองเห็นหรือแก้ไข เมื่อเปิด RLS แต่ไม่มี policy จะเป็น default deny ผู้เป็นเจ้าของตารางมักข้าม RLS ได้ตามค่าเริ่มต้น และ superuser หรือบทบาท BYPASSRLS ข้ามได้ ต้องทดสอบด้วยบทบาทผู้ใช้งานจริง

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/ddl-rowsecurity.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## CREATE VIEW (ตารางเสมือน)

PostgreSQL view ปกติเก็บนิยามคิวรี ไม่ได้เก็บผลลัพธ์เป็นสำเนาถาวร เมื่อเรียกใช้จะอ่านผ่านคิวรีที่นิยามไว้ ความสามารถในการแก้ข้อมูลผ่าน view ขึ้นกับรูปแบบคิวรี

### ตัวอย่าง

```sql
CREATE VIEW one_value AS SELECT 1 AS value;
```

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/sql-createview.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Identity AUTO INCREMENT (เลขอัตโนมัติ)

PostgreSQL ใช้ GENERATED ALWAYS หรือ BY DEFAULT AS IDENTITY เพื่อให้ implicit sequence สร้างค่าอัตโนมัติ Identity ไม่ได้บังคับความไม่ซ้ำด้วยตัวเอง ต้องเพิ่ม PRIMARY KEY หรือ UNIQUE หากต้องการ ความสามารถนี้ไม่ใช่ไวยากรณ์ AUTO_INCREMENT ของ MySQL

### ตัวอย่าง

```sql
CREATE TABLE identity_demo (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY);
```

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/ddl-identity-columns.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม

## Subquery EXISTS NOT IN NULL (คิวรีย่อยและค่าว่าง)

PostgreSQL: EXISTS เป็นจริงเมื่อคิวรีย่อยคืนอย่างน้อยหนึ่งแถว NOT IN อาจได้ NULL แทนจริงเมื่อฝั่งคิวรีย่อยมี NULL และไม่มีค่าที่ตรงกัน ต้องพิจารณาพฤติกรรม NULL ก่อนใช้กรองข้อมูล

### ตัวอย่าง

```sql
SELECT EXISTS (SELECT 1 WHERE 1=1) AS found;
```

### แหล่งอ้างอิง

https://www.postgresql.org/docs/current/functions-subquery.html
ตรวจเอกสาร: 2026-09-08 · เรียบเรียงภาษาไทย · ตัวอย่างสาธิตที่จัดทำเพิ่ม



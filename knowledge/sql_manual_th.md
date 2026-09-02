# คลังความรู้ SQL ภาษาไทย

แต่ละหัวข้อขึ้นต้นด้วย `## ` ตามด้วยคำอธิบาย
แล้วใส่ `### รูปแบบคำสั่ง` และ `### ตัวอย่าง` เป็นบล็อกโค้ด ```sql

---

## SQL คืออะไร

SQL ย่อมาจาก Structured Query Language เป็นภาษามาตรฐานสำหรับติดต่อกับระบบจัดการฐานข้อมูลเชิงสัมพันธ์ (RDBMS - Relational Database Management System) ไม่ว่าจะเป็น MySQL, Microsoft SQL Server, Oracle, PostgreSQL หรือ Microsoft Access SQL ทำอะไรได้บ้าง ● ค้นหาและดึงข้อมูล (Query) จากฐานข้อมูล ● เพิ่ม แก้ไข และลบข้อมูลในตาราง ● สร้าง แก้ไข และลบตารางหรือฐานข้อมูล ● กำหนดสิทธิ์การเข้าถึงตารางและมุมมองข้อมูล (View)

---

## ฐานข้อมูล (Database) คืออะไร

ฐานข้อมูล (Database) คือชุดข้อมูลที่มีโครงสร้าง ถูกจัดเก็บอย่างเป็นระบบในคอมพิวเตอร์ และควบคุมดูแลโดยซอฟต์แวร์ที่เรียกว่าระบบจัดการฐานข้อมูล (Database Management System หรือ DBMS) ข้อมูล ซอฟต์แวร์ DBMS และแอปพลิเคชันที่เกี่ยวข้อง เมื่อรวมกันจะเรียกว่า “ระบบฐานข้อมูล” (Database System) ข้อมูลในฐานข้อมูลส่วนใหญ่ในปัจจุบันจะถูกจัดเก็บในรูปแบบตาราง (Table) ที่ประกอบด้วยแถวและคอลัมน์ เพื่อให้สามารถประมวลผลและค้นหาข้อมูลได้อย่างมีประสิทธิภาพ และสามารถเข้าถึง จัดการ แก้ไข ปรับปรุง ควบคุม และจัดระเบียบข้อมูลได้โดยง่าย ฐานข้อมูลส่วนใหญ่ใช้ภาษา SQL (Structured Query Language) เป็นเครื่องมือหลักในการเขียนและค้นหาข้อมูล

---

## RDBMS และแนวคิดตาราง

RDBMS ย่อมาจาก Relational Database Management System เป็นโปรแกรมที่ใช้ดูแลรักษาฐานข้อมูลเชิงสัมพันธ์ และเป็นพื้นฐานของระบบฐานข้อมูลสมัยใหม่แทบทั้งหมด เช่น MySQL, Microsoft SQL Server, Oracle Database และ Microsoft Access ข้อมูลใน RDBMS จะถูกจัดเก็บในอ็อบเจกต์ที่เรียกว่า “ตาราง” (Table) ซึ่งเป็นชุดของข้อมูลที่เกี่ยวข้องกัน ประกอบด้วย: • คอลัมน์ (Column / Field): เป็นแนวตั้งของตาราง ใช้เก็บข้อมูลชุดหนึ่งที่มีลักษณะประเภทเดียวกัน • แถว (Row / Record): เป็นแนวนอนของตาราง ใช้เก็บข้อมูลแต่ละรายการในตาราง ตัวอย่างเช่น ตาราง “Customers” จากฐานข้อมูลตัวอย่าง Northwind มีคอลัมน์ ได้แก่ CustomerID, CustomerName, ContactName, Address, City, PostalCode และ Country โดยมีข้อมูลทั้งหมด 5 แถว หรือ 5 รายการลูกค้า

---

## ฐานข้อมูลเชิงสัมพันธ์ (Relational Database)

ฐานข้อมูลเชิงสัมพันธ์กำหนดความสัมพันธ์ของข้อมูลในรูปแบบของตารางที่เชื่อมโยงกัน โดยอาศัยข้อมูลที่มีร่วมกันระหว่างตาราง (Common data) เช่น ในฐานข้อมูล Northwind ที่มีตาราง Customers, Orders และ Shippers: • ความสัมพันธ์ระหว่างตาราง Customers และ Orders คือ คอลัมน์ CustomerID • ความสัมพันธ์ระหว่างตาราง Orders และ Shippers คือ คอลัมน์ ShipperID การเชื่อมโยงข้อมูลลักษณะนี้อาศัยหลักการของ Primary Key และ Foreign Key ซึ่งเป็นตัวระบุเฉพาะ (Unique identifier) ที่แสดงความสัมพันธ์ระหว่างตารางต่าง ๆ ทำให้สามารถรวมข้อมูลจากหลายตารางเข้าด้วยกันเพื่อสร้างรายงานที่มีคุณค่าได้ เช่น รายงานยอดขายแยกตามอุตสาหกรรมหรือบริษัท

---

## ภาษา SQL คืออะไร

SQL (Structured Query Language) เป็นภาษาโปรแกรมมาตรฐานที่ใช้ในระบบจัดการฐานข้อมูลเชิงสัมพันธ์เกือบทั้งหมด สำหรับค้นหา (Query) จัดการ (Manipulate) และกำหนดโครงสร้างข้อมูล (Define) รวมถึงควบคุมสิทธิ์การเข้าถึงข้อมูล เนื่องจากฐานข้อมูลเชิงสัมพันธ์เกี่ยวข้องอย่างใกล้ชิดกับ SQL จึงมักถูกเรียกว่า “ฐานข้อมูล SQL” เช่นกัน SQL เริ่มพัฒนาขึ้นที่ IBM ในช่วงทศวรรษ 1970 โดยมี Oracle เป็นผู้มีส่วนร่วมสำคัญ ซึ่งนำไปสู่การกำหนดมาตรฐาน SQL ของ ANSI และมีการต่อยอดพัฒนาโดยบริษัทต่าง ๆ เช่น IBM, Oracle และ Microsoft แม้ปัจจุบันจะมีภาษาโปรแกรมใหม่ ๆ เกิดขึ้น แต่ SQL ก็ยังคงถูกใช้งานอย่างแพร่หลาย

---

## ประวัติความเป็นมาของฐานข้อมูลเชิงสัมพันธ์และ SQL

ก่อนจะมีฐานข้อมูลเชิงสัมพันธ์ องค์กรต่าง ๆ ใช้ระบบฐานข้อมูลแบบลำดับชั้น (Hierarchical Database) ที่มีโครงสร้างคล้ายต้นไม้ ซึ่งมีข้อจำกัดด้านความยืดหยุ่นและมักผูกติดกับแอปพลิเคชันเฉพาะ • ปี ค.ศ. 1970 นักวิจัยของ IBM ชื่อ Edgar F. Codd ตีพิมพ์บทความ “A Relational Model of Data for Large Shared Data Banks” ซึ่งเป็นการเสนอแนวคิดโมเดลฐานข้อมูลเชิงสัมพันธ์เป็นครั้งแรก โดยเสนอให้จัดเรียงข้อมูลตามความสัมพันธ์ที่มีความหมาย ในรูปแบบคู่ attribute-value • ปี ค.ศ. 1973 IBM เริ่มโครงการ System R ที่ San Jose Research Laboratory (ปัจจุบันคือ Almaden Research Center) เพื่อพิสูจน์ทฤษฎีเชิงสัมพันธ์ในระดับอุตสาหกรรม และกลายเป็นพื้นที่ทดสอบภาษา SQL จนได้รับการยอมรับอย่างแพร่หลาย • ภาษา SQL ถูกคิดค้นโดย Don Chamberlin และ Ray Boyce แห่ง IBM เดิมเรียกว่า “SEQUEL” แต่ภายหลังเปลี่ยนชื่อเป็น “SQL” เนื่องจากปัญหาด้านเครื่องหมายการค้า • ปี ค.ศ. 1983 IBM เปิดตัวตระกูลผลิตภัณฑ์ DB2 ซึ่งเป็นฐานข้อมูลเชิงสัมพันธ์ตระกูลที่สองของ IBM และยังคงเป็นหนึ่งในผลิตภัณฑ์ที่ประสบความสำเร็จที่สุด รองรับธุรกรรมนับพันล้านรายการต่อวันบนโครงสร้างพื้นฐานคลาวด์จนถึงปัจจุบัน

### ตัวอย่าง

```sql
(tuple)
```

---

## วิวัฒนาการของฐานข้อมูล

• ทศวรรษ 1960: ฐานข้อมูลแบบ Navigational เช่น Hierarchical Database (โครงสร้างต้นไม้ รองรับความสัมพันธ์แบบ one-to-many) และ Network Database (ยืดหยุ่นกว่า รองรับหลายความสัมพันธ์) แต่ยังมีความซับซ้อนและไม่ยืดหยุ่น • ทศวรรษ 1980: ฐานข้อมูลเชิงสัมพันธ์ (Relational Database) ได้รับความนิยมอย่างกว้างขวาง • ทศวรรษ 1990: ฐานข้อมูลเชิงวัตถุ (Object-oriented Database) เริ่มเป็นที่แพร่หลาย • ต่อมา: ฐานข้อมูลแบบกระจาย (Distributed Database) เกิดขึ้นเพื่อรองรับการเติบโตของอินเทอร์เน็ต และความต้องการประมวลผลข้อมูลที่ไม่มีโครงสร้าง (Unstructured data) ได้รวดเร็วขึ้น • ปัจจุบัน: ฐานข้อมูลบนคลาวด์ (Cloud Database) และฐานข้อมูลอัตโนมัติ (Autonomous Database) กำลังเปลี่ยนรูปแบบการจัดเก็บและบริหารจัดการข้อมูล โดยฐานข้อมูลอัตโนมัติตัวแรกถูกประกาศเปิดตัวในช่วงปลายปี ค.ศ. 2017

---

## ระบบจัดการฐานข้อมูล (DBMS)

DBMS (Database Management System) คือซอฟต์แวร์ที่ทำหน้าที่เป็นตัวกลางระหว่างฐานข้อมูลกับผู้ใช้งานหรือโปรแกรมต่าง ๆ ช่วยให้สามารถดึงข้อมูล อัปเดต และจัดการโครงสร้างข้อมูลได้ นอกจากนี้ DBMS ยังช่วยในการบริหารจัดการด้านต่าง ๆ เช่น การตรวจสอบประสิทธิภาพ การปรับแต่ง (Tuning) และการสำรองและกู้คืนข้อมูล (Backup & Recovery) RDBMS คือ DBMS ที่จัดเก็บข้อมูลในรูปแบบตาราง แตกต่างจาก DBMS ทั่วไปที่อาจจัดเก็บข้อมูลในรูปแบบไฟล์ ตัวอย่าง DBMS/RDBMS ที่ได้รับความนิยม ได้แก่ MySQL, Microsoft SQL Server, Oracle Database, IBM DB2, PostgreSQL, Microsoft Access และ FileMaker Pro

---

## คุณสมบัติ ACID ของธุรกรรม (Transaction)

ฐานข้อมูลเชิงสัมพันธ์มักเกี่ยวข้องกับธุรกรรม (Transaction) ซึ่งเป็นชุดคำสั่งที่ต้องทำงานร่วมกันแบบครบถ้วนสมบูรณ์ ตัวอย่างที่นิยมใช้อธิบาย คือ ที่ยอดเงินจะต้องถูกถอนออกจากบัญชีหนึ่งและฝากเข้าอีกบัญชีหนึ่งพร้อมกันเสมอ ไม่สามารถเกิดขึ้นเพียงบางส่วนได้ โดยธุรกรรมที่ดีจะมีคุณสมบัติสำคัญ 4 ประการ เรียกว่า ACID ดังนี้ คุณสมบัติ ความหมาย Atomicity (ความเป็นเอกภาพ) การเปลี่ยนแปลงข้อมูลทั้งหมดในธุรกรรมเกิดขึ้นครบถ้วน หรือไม่เกิดขึ้นเลยแม้แต่ส่วนเดียว Consistency (ความสอดคล้อง) ข้อมูลอยู่ในสถานะที่ถูกต้องตลอดกระบวนการทำงาน รักษาความสมบูรณ์ของข้อมูล Isolation (ความเป็นอิสระ) ธุรกรรมที่ทำงานพร้อมกันจะไม่เห็นสถานะกลางของกันและกัน เสมือนทำงานเรียงลำดับกัน Durability (ความคงทน) เมื่อธุรกรรมเสร็จสมบูรณ์ ข้อมูลจะถูกบันทึกถาวร แม้ระบบจะล้มเหลวในภายหลัง

---

## ประเภทของฐานข้อมูล

9.1 ฐานข้อมูลเชิงสัมพันธ์ (Relational Database) จัดเก็บข้อมูลในรูปแบบตารางที่มีคอลัมน์และแถว เป็นรูปแบบที่ได้รับความนิยมสูงสุดตั้งแต่ทศวรรษ 1980 เนื่องจากมีประสิทธิภาพและความยืดหยุ่นสูงในการเข้าถึงข้อมูลที่มีโครงสร้าง 9.2 ฐานข้อมูลเชิงวัตถุ (Object-oriented Database) จัดเก็บข้อมูลในรูปแบบอ็อบเจกต์ (Object) คล้ายกับแนวคิดการเขียนโปรแกรมเชิงวัตถุ 9.3 ฐานข้อมูลแบบกระจาย (Distributed Database) ประกอบด้วยไฟล์ข้อมูลตั้งแต่ 2 แห่งขึ้นไปที่กระจายอยู่ในสถานที่ต่าง ๆ อาจอยู่ในเครื่องคอมพิวเตอร์หลายเครื่องในสถานที่เดียวกัน หรือกระจายอยู่ในเครือข่ายที่แตกต่างกันก็ได้ 9.4 ฐานข้อมูลแบบ NoSQL (ไม่ใช่เชิงสัมพันธ์) ฐานข้อมูล NoSQL ไม่มีโครงสร้าง Schema ที่ตายตัวเหมือนฐานข้อมูลเชิงสัมพันธ์ ถูกออกแบบมาเพื่อรองรับความยืดหยุ่นและการขยายตัวของข้อมูลที่ไม่มีโครงสร้าง เช่น ข้อความ วิดีโอ และรูปภาพ โดยแบ่งออกเป็นประเภทย่อยได้ดังนี้ • Key-value store: จัดเก็บข้อมูลเป็นคู่ key-value นิยมใช้สำหรับแคชข้อมูลหรือข้อมูลตะกร้าสินค้า ตัวอย่างเช่น Redis และ Memcached • Document store: จัดเก็บข้อมูลในรูปแบบเอกสาร มักอยู่ในรูปแบบ JSON, XML หรือ BSON เหมาะกับข้อมูลกึ่งโครงสร้าง ตัวอย่างเช่น MongoDB • Wide-column store: จัดเก็บข้อมูลเป็นคอลัมน์ ทำให้เข้าถึงเฉพาะคอลัมน์ที่ต้องการได้โดยไม่สิ้นเปลืองหน่วยความจำ ตัวอย่างเช่น Apache HBase และ Apache Cassandra • Graph store: จัดเก็บข้อมูลในรูปแบบโหนด (Node) เส้นเชื่อม (Edge) และคุณสมบัติ (Property) เหมาะสำหรับข้อมูลที่เป็นเครือข่ายความสัมพันธ์ ตัวอย่างเช่น Neo4j ทั้งนี้ ฐานข้อมูลบางประเภทให้ความสำคัญกับความพร้อมใช้งาน (Availability) มากกว่าความสอดคล้องของข้อมูล (Consistency) ตามแนวคิด CAP Theorem (Consistency, Availability, Partition Tolerance) ในขณะที่ฐานข้อมูลเชิงสัมพันธ์มักให้ความสำคัญกับความสอดคล้องของข้อมูลเป็นหลัก

---

## ข้อดีของฐานข้อมูลเชิงสัมพันธ์

• ลดความซ้ำซ้อนของข้อมูล (Data Redundancy) ผ่านกระบวนการ Normalization • รองรับผู้ใช้งานหลายคนพร้อมกัน (Multi-user access) พร้อมระบบควบคุมสิทธิ์การเข้าถึง • มีความเป็นธุรกรรม (Transactional) รับประกันความสอดคล้องของข้อมูลตลอดเวลา • รองรับการสำรองและกู้คืนข้อมูลได้ง่าย แม้ในขณะที่ฐานข้อมูลกำลังทำงานอยู่ • มีชุมชนผู้ใช้งานขนาดใหญ่ เนื่องจากมีการใช้งานมาอย่างยาวนาน • Stored Procedure ช่วยลดงานที่ต้องทำซ้ำ และช่วยบริหารจัดการสิทธิ์การเข้าถึงข้อมูล • การใช้ดัชนี (Index) ช่วยให้ค้นหาข้อมูลได้รวดเร็ว โดยไม่ต้องตรวจสอบข้อมูลทุกแถวในตาราง

---

## ความแตกต่างระหว่างฐานข้อมูลกับสเปรดชีต

ทั้งฐานข้อมูลและสเปรดชีต (เช่น Microsoft Excel) ต่างก็เป็นเครื่องมือที่สะดวกสำหรับจัดเก็บข้อมูล แต่มีความแตกต่างกันในประเด็นสำคัญ ดังนี้ ประเด็น สเปรดชีต (เช่น Excel) ฐานข้อมูล (Database) การจัดเก็บและจัดการข้อมูล เหมาะกับผู้ใช้คนเดียวหรือกลุ่มเล็ก ไม่เหมาะกับข้อมูลที่ซับซ้อนมาก ออกแบบให้จัดเก็บข้อมูลจำนวนมากอย่างเป็นระบบ รองรับการค้นหาที่ซับซ้อน การเข้าถึงข้อมูล เหมาะกับผู้ใช้จำนวนน้อย รองรับผู้ใช้จำนวนมากเข้าถึงพร้อมกันได้อย่างปลอดภัย ผ่านภาษา SQL ปริมาณข้อมูลที่รองรับ มีข้อจำกัดด้านปริมาณข้อมูล รองรับข้อมูลปริมาณมหาศาลได้

---

## ความท้าทายของฐานข้อมูลในปัจจุบัน

• ปริมาณข้อมูลที่เพิ่มขึ้นอย่างรวดเร็วจากเซนเซอร์ เครื่องจักรที่เชื่อมต่อกัน และแหล่งข้อมูลอื่น ๆ ทำให้ผู้ดูแลระบบต้องบริหารจัดการข้อมูลอย่างมีประสิทธิภาพ • ภัยคุกคามด้านความปลอดภัยของข้อมูล (Data Breach) ที่เพิ่มมากขึ้น ทำให้ต้องรักษาความปลอดภัยควบคู่ไปกับการเข้าถึงข้อมูลที่สะดวก • ความต้องการเข้าถึงข้อมูลแบบเรียลไทม์ (Real-time) เพื่อสนับสนุนการตัดสินใจทางธุรกิจที่รวดเร็ว

---

## แนวโน้มในอนาคต: ฐานข้อมูลอัตโนมัติ (Autonomous Database)

ฐานข้อมูลอัตโนมัติใช้เทคโนโลยีคลาวด์และ Machine Learning เพื่อทำงานประจำวันโดยอัตโนมัติ เช่น การปรับแต่งประสิทธิภาพ (Tuning) การรักษาความปลอดภัย การสำรองข้อมูล และการอัปเดตระบบ ช่วยลดภาระงานที่ต้องทำด้วยมือของผู้ดูแลระบบ (Database Administrator) และช่วยเพิ่มประสิทธิภาพ ลดต้นทุน รวมถึงเพิ่มความปลอดภัยของข้อมูลในระยะยาว RDBMS คืออะไร RDBMS คือระบบจัดการฐานข้อมูลที่จัดเก็บข้อมูลในรูปแบบ 'ตาราง' (Table) ซึ่งประกอบด้วยแถว (Row) และคอลัมน์ (Column) โดยแต่ละแถวคือระเบียนข้อมูลหนึ่งรายการ และแต่ละคอลัมน์คือฟิลด์ข้อมูลหนึ่งประเภท RDBMS เป็นพื้นฐานของระบบฐานข้อมูลสมัยใหม่แทบทั้งหมด CustomerID CustomerName City Country 1 Alfreds Futterkiste Berlin Germany 2 Ana Trujillo México D.F. Mexico 3 Antonio Moreno México D.F. Mexico หมายเหตุ: SQL เป็นมาตรฐาน ANSI/ISO แต่ระบบฐานข้อมูลแต่ละยี่ห้ออาจมีส่วนขยายหรือรายละเอียดปลีกย่อยที่แตกต่างกันไปบ้าง อย่างไรก็ตามคำสั่งหลัก เช่น SELECT, UPDATE, DELETE, INSERT ยังคงทำงานในลักษณะใกล้เคียงกันในทุกระบบ

---

## รูปแบบคำสั่ง SQL เบื้องต้น

การกระทำส่วนใหญ่ที่ต้องทำกับฐานข้อมูลจะอยู่ในรูปของ 'คำสั่ง SQL' (SQL Statement) ซึ่งประกอบด้วยคำสงวน (Keyword) ที่เข้าใจง่าย เช่น คำสั่งต่อไปนี้จะเลือกข้อมูลทั้งหมดจากตาราง Customers: ข้อควรทราบ ● คำสงวนของ SQL ไม่คำนึงถึงตัวพิมพ์เล็ก-ใหญ่ (ไม่ case sensitive) เช่น SELECT กับ select ถือว่าเหมือนกัน แต่ในเอกสารนี้จะเขียนคำสงวนด้วยตัวพิมพ์ใหญ่เพื่อความชัดเจน ● ระบบฐานข้อมูลบางระบบกำหนดให้ต้องใส่เครื่องหมายเซมิโคลอน ( ; ) ปิดท้ายทุกคำสั่ง ซึ่งเป็นแนวปฏิบัติที่ดีและแนะนำให้ใส่เสมอเมื่อมีหลายคำสั่งในสคริปต์เดียวกัน คำสั่ง SQL ที่สำคัญ คำสั่ง หน้าที่ SELECT ดึงข้อมูลจากฐานข้อมูล UPDATE แก้ไขข้อมูลในตาราง DELETE ลบข้อมูลออกจากตาราง INSERT INTO เพิ่มข้อมูลใหม่เข้าตาราง CREATE TABLE สร้างตารางใหม่ DROP TABLE ลบตารางทั้งตาราง

### ตัวอย่าง

```sql
SELECT * FROM Customers;
```

---

## คำสั่ง SELECT

คำสั่ง SELECT ใช้สำหรับเลือกข้อมูลจากฐานข้อมูล ผลลัพธ์ที่ได้จะถูกเก็บไว้ในรูปแบบตารางผลลัพธ์ (Result Set) โดย column1, column2 คือชื่อคอลัมน์ที่ต้องการเลือกจากตาราง และ table_name คือชื่อตารางที่ต้องการดึงข้อมูล หากต้องการเลือกทุกคอลัมน์ในตาราง สามารถใช้เครื่องหมายดอกจัน ( * ) แทนการระบุชื่อคอลัมน์ทีละคอลัมน์:

### รูปแบบคำสั่ง

```sql
SELECT column1, column2, ...
FROM table_name;
```

### ตัวอย่าง

```sql
SELECT * FROM Customers;

SELECT CustomerName, City FROM Customers;
```

---

## คำสั่ง SELECT DISTINCT

คำสั่ง SELECT DISTINCT ใช้เพื่อคืนค่าเฉพาะแถวที่มีค่าไม่ซ้ำกัน (Unique Values) เท่านั้น ภายในตารางหนึ่งอาจมีค่าซ้ำกันในหลายแถว ซึ่ง DISTINCT จะช่วยตัดความซ้ำซ้อนของผลลัพธ์ออก คำสั่งต่อไปนี้จะคืนค่าเฉพาะประเทศที่ไม่ซ้ำกันจากตาราง Customers: มาตรฐาน SQL ไม่มีฟังก์ชันนับค่าที่ไม่ซ้ำกันโดยตรงในบางระบบ (เช่น MS Access) จึงมักใช้ COUNT ร่วมกับ DISTINCT เพื่อหาจำนวนค่าที่ไม่ซ้ำกัน:

### รูปแบบคำสั่ง

```sql
SELECT DISTINCT column1, column2, ...
FROM table_name;
```

### ตัวอย่าง

```sql
SELECT DISTINCT Country FROM Customers;

SELECT COUNT(DISTINCT Country) FROM Customers;
```

---

## อนุประโยค WHERE

อนุประโยค WHERE ใช้สำหรับกรองระเบียนข้อมูลให้เหลือเฉพาะแถวที่ตรงตามเงื่อนไขที่กำหนด ข้อความ (Text) กับ ตัวเลข (Numeric) ค่าที่เป็นข้อความในเงื่อนไขต้องอยู่ภายในเครื่องหมายคำพูดเดี่ยว (single quotes) ในขณะที่ค่าตัวเลขไม่จำเป็นต้องใส่เครื่องหมายคำพูด: ตัวดำเนินการที่ใช้ใน WHERE ตัวดำเนินการ ความหมาย = เท่ากับ <> หรือ != ไม่เท่ากับ > มากกว่า < น้อยกว่า >= มากกว่าหรือเท่ากับ <= น้อยกว่าหรือเท่ากับ BETWEEN อยู่ในช่วงที่กำหนด LIKE ค้นหาตามรูปแบบข้อความ IN ระบุค่าที่เป็นไปได้หลายค่า

### รูปแบบคำสั่ง

```sql
SELECT column1, column2, ...
FROM table_name
WHERE condition;
```

### ตัวอย่าง

```sql
SELECT * FROM Customers WHERE Country = 'Mexico';
SELECT * FROM Customers WHERE CustomerID = 1;
```

---

## คำสั่ง ORDER BY

คำสั่ง ORDER BY ใช้สำหรับเรียงลำดับผลลัพธ์ที่ได้จากคำสั่ง SELECT โดยค่าเริ่มต้นจะเรียงจากน้อยไปมาก (ascending) สามารถระบุ ASC หรือ DESC แยกกันในแต่ละคอลัมน์ได้:

### รูปแบบคำสั่ง

```sql
SELECT column1, column2, ...
FROM table_name
ORDER BY column1, column2, ... ASC|DESC;
```

### ตัวอย่าง

```sql
SELECT * FROM Products
ORDER BY Price DESC;

SELECT * FROM Products
ORDER BY ProductName;

SELECT * FROM Customers
ORDER BY Country ASC, CustomerName DESC;
```

---

## ตัวดำเนินการ AND

ตัวดำเนินการ AND ใช้ในอนุประโยค WHERE เพื่อกรองข้อมูลโดยต้องเป็นจริง 'ทุกเงื่อนไข' ที่กำหนดพร้อมกัน จึงจะถูกรวมอยู่ในผลลัพธ์ คำสั่งต่อไปนี้เลือกลูกค้าทั้งหมดจากประเทศสเปนที่ชื่อขึ้นต้นด้วยตัวอักษร 'G': หมายเหตุ: สามารถผสม AND กับ OR ร่วมกันได้ โดยควรใช้วงเล็บ ( ) เพื่อกำหนดลำดับความสำคัญของเงื่อนไขให้ชัดเจน

### รูปแบบคำสั่ง

```sql
SELECT column1, column2, ...
FROM table_name
WHERE condition1 AND condition2 AND condition3 ...;
```

### ตัวอย่าง

```sql
SELECT * FROM Customers
WHERE Country = 'Spain' AND CustomerName LIKE 'G%';
```

---

## ตัวดำเนินการ OR

ตัวดำเนินการ OR ใช้กรองข้อมูลโดยขอเพียง 'อย่างน้อยหนึ่งเงื่อนไข' เป็นจริงเท่านั้น ก็จะถูกรวมอยู่ในผลลัพธ์ คำสั่งต่อไปนี้เลือกลูกค้าทั้งหมดที่มาจากประเทศเยอรมนี หรือ สเปน:

### รูปแบบคำสั่ง

```sql
SELECT column1, column2, ...
FROM table_name
WHERE condition1 OR condition2 OR condition3 ...;
```

### ตัวอย่าง

```sql
SELECT * FROM Customers
WHERE Country = 'Germany' OR Country = 'Spain';

SELECT * FROM Customers
WHERE Country = 'Germany'
AND (City = 'Berlin' OR City = 'München');
```

---

## ตัวดำเนินการ NOT

ตัวดำเนินการ NOT ใช้เพื่อกลับค่าความจริงของเงื่อนไข (negate) หรือใช้ร่วมกับตัวดำเนินการอื่นเพื่อคัดข้อมูลที่ 'ไม่ตรง' ตามเงื่อนไขที่กำหนดออกจากผลลัพธ์ NOT LIKE คัดข้อมูลที่ไม่ตรงกับรูปแบบข้อความที่กำหนด NOT BETWEEN คัดข้อมูลที่อยู่นอกช่วงค่าที่กำหนด NOT IN คัดข้อมูลที่ไม่อยู่ในรายการค่าที่กำหนด NOT >, NOT < กลับความหมายของเงื่อนไขมากกว่า/น้อยกว่า เลือกลูกค้าทั้งหมดที่ชื่อไม่ได้ขึ้นต้นด้วยตัวอักษร 'A': เลือกลูกค้าที่เมืองไม่ใช่ 'Paris' และไม่ใช่ 'London':

### รูปแบบคำสั่ง

```sql
SELECT * FROM Customers
WHERE NOT CustomerName LIKE 'A%';
```

### ตัวอย่าง

```sql
SELECT * FROM Customers
WHERE City NOT IN ('Paris', 'London');
```

---

## คำสั่ง INSERT INTO

คำสั่ง INSERT INTO ใช้สำหรับเพิ่มระเบียนข้อมูลใหม่เข้าไปในตาราง สามารถเขียนได้สองรูปแบบหลัก หากใส่ค่าครบทุกคอลัมน์ของตาราง สามารถละชื่อคอลัมน์ได้ แต่ต้องเรียงลำดับค่าให้ตรงกับลำดับคอลัมน์ในตาราง: สามารถเพิ่มหลายระเบียนได้ในคำสั่งเดียว โดยคั่นแต่ละชุดค่าด้วยเครื่องหมายจุลภาค:

### รูปแบบคำสั่ง

```sql
INSERT INTO table_name (column1, column2, column3, ...)
VALUES (value1, value2, value3, ...);
```

### ตัวอย่าง

```sql
INSERT INTO table_name VALUES (value1, value2, value3, ...);

INSERT INTO Customers (CustomerName, City, Country)
VALUES ('Cardinal', 'Stavanger', 'Norway');

INSERT INTO Customers (CustomerName, City, Country)
VALUES
('Cardinal', 'Stavanger', 'Norway'),
('Greasy Burger', 'Feltre', 'Italy'),
('Tasty Tee', 'Bologna', 'Italy');
```

---

## ค่า NULL

ค่า NULL หมายถึงฟิลด์ที่ไม่มีค่าอยู่เลย เป็นการแสดงถึงข้อมูลที่ไม่ทราบ ไม่มี หรือไม่สามารถใช้ได้ ไม่ใช่ค่าว่างเปล่า (empty string) หรือค่าศูนย์ NULL เป็นเพียงตัวบ่งชี้ว่า 'ไม่มีข้อมูล' ในฟิลด์นั้น ไม่สามารถใช้ตัวดำเนินการเปรียบเทียบทั่วไป เช่น = หรือ <> กับค่า NULL ได้ จำเป็นต้องใช้ตัวดำเนินการ IS NULL และ IS NOT NULL แทน เลือกลูกค้าทั้งหมดที่ไม่มีข้อมูลในฟิลด์ Address:

### รูปแบบคำสั่ง

```sql
SELECT column_names
FROM table_name
WHERE column_name IS NULL;
SELECT column_names
FROM table_name
WHERE column_name IS NOT NULL;
```

### ตัวอย่าง

```sql
SELECT CustomerName, Address
FROM Customers
WHERE Address IS NULL;
```

---

## คำสั่ง UPDATE

คำสั่ง UPDATE ใช้สำหรับแก้ไขข้อมูลที่มีอยู่แล้วในตาราง หมายเหตุ: หากไม่ระบุอนุประโยค WHERE คำสั่ง UPDATE จะแก้ไขข้อมูล 'ทุกแถว' ในตาราง ควรตรวจสอบเงื่อนไขให้ถูกต้องทุกครั้งก่อนรันคำสั่งจริง

### รูปแบบคำสั่ง

```sql
UPDATE table_name
SET column1 = value1, column2 = value2, ...
WHERE condition;
```

### ตัวอย่าง

```sql
UPDATE Customers
SET ContactName = 'Alfred Schmidt', City = 'Frankfurt'
WHERE CustomerID = 1;

UPDATE Customers
SET ContactName = 'Juan'
WHERE Country = 'Mexico';
```

---

## คำสั่ง DELETE

คำสั่ง DELETE ใช้สำหรับลบระเบียนข้อมูลที่มีอยู่แล้วออกจากตาราง สามารถลบทุกแถวในตารางได้โดยไม่ระบุ WHERE ซึ่งจะเหลือตารางเปล่าไว้ (โครงสร้างตารางยังคงอยู่): หากต้องการลบทั้งตารางและโครงสร้าง ให้ใช้คำสั่ง DROP TABLE แทน:

### รูปแบบคำสั่ง

```sql
DELETE FROM table_name WHERE condition;
```

### ตัวอย่าง

```sql
DELETE FROM Customers WHERE CustomerName = 'Alfreds Futterkiste';

DELETE FROM table_name;

DROP TABLE table_name;
```

---

## การจำกัดจำนวนผลลัพธ์ (SELECT TOP / LIMIT)

ในบางกรณีต้องการจำกัดจำนวนระเบียนที่คืนกลับมา ไวยากรณ์ที่ใช้จะแตกต่างกันไปตามระบบฐานข้อมูล SQL Server /

MS

Access — ใช้ TOP MySQL /

PostgreSQL — ใช้

LIMIT

Oracle — ใช้ FETCH FIRST สามารถระบุเงื่อนไขและการเรียงลำดับร่วมกับการจำกัดจำนวนผลลัพธ์ได้ เช่น เลือก 3 อันดับแรกที่เรียงตามชื่อลูกค้า (ตัวอย่างสำหรับ MySQL): LIMIT 3;

### ตัวอย่าง

```sql
SELECT TOP 3 * FROM Customers;
SELECT TOP 50 PERCENT * FROM Customers;

SELECT * FROM Customers LIMIT 3;

SELECT * FROM Customers FETCH FIRST 3 ROWS ONLY;

SELECT * FROM Customers
ORDER BY CustomerName
```

---

## ฟังก์ชันรวมข้อมูล (Aggregate Functions)

ฟังก์ชันรวมข้อมูลใช้สำหรับคำนวณค่าสรุปจากกลุ่มของแถวข้อมูล เช่น หาค่าน้อยที่สุด มากที่สุด นับจำนวน หรือรวมผลรวม ฟังก์ชันเหล่านี้มักใช้ร่วมกับอนุประโยค GROUP BY เพื่อสรุปผลแยกตามกลุ่มข้อมูล ฟังก์ชัน หน้าที่ MIN() คืนค่าน้อยที่สุดของคอลัมน์ที่เลือก MAX() คืนค่ามากที่สุดของคอลัมน์ที่เลือก COUNT() นับจำนวนแถวที่ตรงตามเงื่อนไข SUM() รวมค่าตัวเลขทั้งหมดในคอลัมน์ AVG() หาค่าเฉลี่ยของคอลัมน์ตัวเลข หมายเหตุ: ฟังก์ชันรวมข้อมูล (ยกเว้น COUNT(*)) จะไม่นำค่า NULL มาคำนวณด้วย

---

## ฟังก์ชัน MIN()

ฟังก์ชัน MIN() คืนค่าที่น้อยที่สุดของคอลัมน์ที่เลือก สามารถใช้ได้กับข้อมูลประเภทตัวเลข ข้อความ และวันที่ หาราคาต่ำสุดของสินค้าแยกตามแต่ละหมวดหมู่:

### รูปแบบคำสั่ง

```sql
SELECT MIN(column_name)
FROM table_name
WHERE condition;
```

### ตัวอย่าง

```sql
SELECT MIN(Price) FROM Products;

SELECT MIN(Price) AS SmallestPrice
FROM Products;

SELECT MIN(BirthDate) AS EarliestBirthdate
FROM Employees;

SELECT MIN(Price) AS SmallestPrice, CategoryID
FROM Products
GROUP BY CategoryID;
```

---

## ฟังก์ชัน MAX()

ฟังก์ชัน MAX() คืนค่าที่มากที่สุดของคอลัมน์ที่เลือก ใช้ได้กับข้อมูลประเภทตัวเลข ข้อความ และวันที่ เช่นเดียวกับ MIN()

### รูปแบบคำสั่ง

```sql
SELECT MAX(column_name)
FROM table_name
WHERE condition;
```

### ตัวอย่าง

```sql
SELECT MAX(Price) FROM Products;

SELECT MAX(Price) AS HighestPrice
FROM Products;

SELECT MAX(BirthDate) AS LatestBirthdate
FROM Employees;

SELECT MAX(Price) AS HighestPrice, CategoryID
FROM Products
GROUP BY CategoryID;
```

---

## ฟังก์ชัน COUNT()

ฟังก์ชัน COUNT() ใช้นับจำนวนแถวที่ตรงตามเงื่อนไขที่กำหนด พฤติกรรมของฟังก์ชันจะขึ้นอยู่กับอาร์กิวเมนต์ที่ใส่ในวงเล็บ

COUNT(*) — นับทุกแถว นับจำนวนแถวทั้งหมดในตาราง รวมถึงแถวที่มีค่า NULL ด้วย:

COUNT(column_name) — นับเฉพาะค่าที่ไม่ใช่ NULL

COUNT(DISTINCT column_name) — นับค่าที่ไม่ซ้ำกัน นับเฉพาะค่าที่ไม่ซ้ำกันและไม่เป็น NULL ในคอลัมน์:

### รูปแบบคำสั่ง

```sql
SELECT COUNT(column_name)
FROM table_name
WHERE condition;
```

### ตัวอย่าง

```sql
SELECT COUNT(*) FROM Products;

SELECT COUNT(ProductName) FROM Products;

SELECT COUNT(DISTINCT Price) FROM Products;

SELECT COUNT(*) AS TotalProducts
FROM Products
WHERE Price > 20;
```

---

## ฟังก์ชัน SUM()

ฟังก์ชัน SUM() ใช้คำนวณผลรวมของค่าตัวเลขทั้งหมดในคอลัมน์ที่ระบุ โดยจะไม่นำค่า NULL มารวมด้วย หาผลรวมจำนวนสินค้าที่สั่งซื้อทั้งหมดจากตาราง OrderDetails: พารามิเตอร์ภายในฟังก์ชัน SUM() สามารถเป็นนิพจน์ทางคณิตศาสตร์ได้ เช่น การคูณจำนวนสินค้ากับราคาต่อหน่วยเพื่อหายอดรวมมูลค่า:

### รูปแบบคำสั่ง

```sql
SELECT SUM(column_name)
FROM table_name
WHERE condition;
```

### ตัวอย่าง

```sql
SELECT SUM(Quantity) FROM OrderDetails;

SELECT SUM(Quantity)
FROM OrderDetails
WHERE ProductId = 11;

SELECT SUM(Quantity) AS TotalQuantity
FROM OrderDetails;

SELECT OrderID, SUM(Quantity) AS [Total Quantity]
FROM OrderDetails
GROUP BY OrderID;
```

---

## ฟังก์ชัน AVG()

ฟังก์ชัน AVG() ใช้คำนวณค่าเฉลี่ยของคอลัมน์ตัวเลข โดยจะไม่นำค่า NULL มารวมคำนวณด้วย สามารถใช้ AVG() ร่วมกับคำสั่งย่อย (Subquery) เพื่อหาแถวที่มีค่าสูงกว่าค่าเฉลี่ยทั้งหมดได้:

### รูปแบบคำสั่ง

```sql
SELECT AVG(column_name)
FROM table_name
WHERE condition;
```

### ตัวอย่าง

```sql
SELECT AVG(Price) FROM Products;

SELECT AVG(Price)
FROM Products
WHERE CategoryID = 1;

SELECT AVG(Price) AS [average price]
FROM Products;

SELECT * FROM Products
WHERE Price > (SELECT AVG(Price) FROM Products);
```

---

## ตัวดำเนินการ LIKE และไวลด์การ์ด

ตัวดำเนินการ LIKE ใช้ในอนุประโยค WHERE เพื่อค้นหาข้อมูลตามรูปแบบที่กำหนด (Pattern Matching) มักใช้งานร่วมกับสัญลักษณ์ไวลด์การ์ด (Wildcard) เพื่อแทนตัวอักษรที่ไม่ทราบแน่ชัด สัญลักษณ์ไวลด์การ์ดหลัก สัญลักษณ์ ความหมาย % แทนตัวอักษรจำนวนเท่าใดก็ได้ ตั้งแต่ศูนย์ตัวขึ้นไป _ แทนตัวอักษรเพียง 1 ตัว สัญลักษณ์ ความหมาย [charlist] แทนตัวอักษรตัวใดตัวหนึ่งในกลุ่มที่ระบุ (รองรับเฉพาะบางระบบ เช่น SQL Server/MS Access) [!charlist] หรือ [^charlist] แทนตัวอักษรที่ไม่อยู่ในกลุ่มที่ระบุ ค้นหาลูกค้าที่เมืองมีคำว่า 'on' ปรากฏอยู่ตรงไหนก็ได้: ค้นหาลูกค้าที่เมืองขึ้นต้นด้วยตัวอักษรใดก็ได้ 1 ตัว ตามด้วย 'ondon': ค้นหาลูกค้าที่ชื่อขึ้นต้นด้วย 'a' และมีความยาวอย่างน้อย 3 ตัวอักษร: การใช้งานกลุ่มตัวอักษร [] (SQL Server / MS Access) ค้นหาลูกค้าที่ชื่อขึ้นต้นด้วยตัวอักษร b, s หรือ p: ค้นหาลูกค้าที่ชื่อขึ้นต้นด้วยตัวอักษรในช่วง a ถึง f: หมายเหตุ: ถ้าไม่ใส่สัญลักษณ์ไวลด์การ์ดเลย ข้อความในเงื่อนไข LIKE จะต้องตรงกันแบบทั้งหมด (exact match) จึงจะได้ผลลัพธ์

### รูปแบบคำสั่ง

```sql
SELECT column1, column2, ...
FROM table_name
WHERE columnN LIKE pattern;
```

### ตัวอย่าง

```sql
SELECT * FROM Customers
WHERE CustomerName LIKE 'a%';

SELECT * FROM Customers
WHERE City LIKE '%on%';

SELECT * FROM Customers
WHERE CustomerName LIKE '%es';

SELECT * FROM Customers
WHERE City LIKE '_ondon';
```

---

## ตัวดำเนินการ IN

ตัวดำเนินการ IN ใช้เป็นทางลัดแทนการเขียนเงื่อนไข OR หลายค่าติดกัน ทำให้คำสั่งกระชับและอ่านง่ายขึ้น เลือกลูกค้าที่มาจากประเทศเยอรมนี ฝรั่งเศส หรือสหราชอาณาจักร: NOT IN คัดลูกค้าที่ไม่ได้มาจากประเทศเหล่านั้นออก: IN ร่วมกับ Subquery สามารถใช้ IN ร่วมกับคำสั่งย่อยเพื่อเลือกลูกค้าที่มีคำสั่งซื้ออยู่ในตาราง Orders:

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table_name
WHERE column_name IN (value1, value2, ...);
```

### ตัวอย่าง

```sql
SELECT * FROM Customers
WHERE Country IN ('Germany', 'France', 'UK');

SELECT * FROM Customers
WHERE Country NOT IN ('Germany', 'France', 'UK');

SELECT * FROM Customers
WHERE CustomerID IN (SELECT CustomerID FROM Orders);
```

---

## ตัวดำเนินการ BETWEEN

ตัวดำเนินการ BETWEEN ใช้ในอนุประโยค WHERE เพื่อเลือกค่าที่อยู่ภายในช่วงที่กำหนด โดยรวมค่าเริ่มต้นและค่าสิ้นสุดของช่วงด้วย (inclusive) ใช้ได้ทั้งกับตัวเลข ข้อความ และวันที่ NOT BETWEEN BETWEEN ร่วมกับ IN BETWEEN กับข้อความ BETWEEN กับวันที่

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table_name
WHERE column_name BETWEEN value1 AND value2;
```

### ตัวอย่าง

```sql
SELECT * FROM Products
WHERE Price BETWEEN 10 AND 20;

SELECT * FROM Products
WHERE Price NOT BETWEEN 10 AND 20;

SELECT * FROM Products
WHERE Price BETWEEN 10 AND 20
AND CategoryID NOT IN (1, 2, 3);

SELECT * FROM Products
WHERE ProductName BETWEEN 'Carnarvon Tigers' AND 'Mozzarella di Giovanni'
ORDER BY ProductName;
```

---

## นามแฝง (Aliases)

นามแฝง (Alias) ใช้เพื่อตั้งชื่อชั่วคราวให้กับคอลัมน์หรือตาราง เพื่อให้ผลลัพธ์อ่านง่ายขึ้นหรือคำสั่งกระชับขึ้น โดยนามแฝงจะมีผลเฉพาะในคำสั่งนั้น ๆ เท่านั้น นามแฝงสำหรับคอลัมน์ นามแฝงที่มีช่องว่าง หากต้องการใช้ชื่อที่มีช่องว่าง ให้ครอบด้วยเครื่องหมายวงเล็บเหลี่ยมหรือเครื่องหมายคำพูด: Address + ', ' + PostalCode + ' ' + City + ', ' + Country AS Address นามแฝงสำหรับตาราง นามแฝงของตารางมีประโยชน์มากเมื่อคำสั่งเกี่ยวข้องกับหลายตาราง เพราะช่วยให้คำสั่งสั้นและอ่านง่ายขึ้น:

### ตัวอย่าง

```sql
SELECT CustomerID AS ID, CustomerName AS Customer
FROM Customers;

SELECT ProductName AS [My Great Products]
FROM Products;

SELECT CustomerName,

FROM Customers;
```

---

## อนุประโยค JOIN

อนุประโยค JOIN ใช้สำหรับรวมข้อมูลจากสองตารางหรือมากกว่าเข้าด้วยกัน โดยอาศัยคอลัมน์ที่มีความสัมพันธ์กันระหว่างตาราง ประเภทของ JOIN ในภาษา SQL ประเภท ความหมาย (INNER) JOIN คืนเฉพาะแถวที่มีค่าตรงกันในทั้งสองตาราง LEFT (OUTER) JOIN คืนทุกแถวจากตารางซ้าย และแถวที่ตรงกันจากตารางขวา RIGHT (OUTER) JOIN คืนทุกแถวจากตารางขวา และแถวที่ตรงกันจากตารางซ้าย FULL (OUTER) JOIN คืนทุกแถวเมื่อมีค่าตรงกันในตารางใดตารางหนึ่ง

---

## INNER JOIN

INNER JOIN คืนเฉพาะแถวที่มีค่าตรงกันในทั้งสองตารางเท่านั้น สามารถเขียนสั้น ๆ เป็น JOIN ได้เช่นกัน เนื่องจากเป็นชนิดการเชื่อมตารางเริ่มต้น เชื่อมตาราง Products และ Categories ผ่านคอลัมน์ CategoryID ที่สัมพันธ์กัน: สามารถใส่อนุประโยค INNER JOIN หลายครั้งเพื่อเชื่อมมากกว่าสองตาราง เช่น รวมข้อมูลคำสั่งซื้อกับข้อมูลลูกค้าและผู้ขนส่ง:

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table1
INNER JOIN table2
ON table1.column_name = table2.column_name;
```

### ตัวอย่าง

```sql
SELECT ProductID, ProductName, CategoryName
FROM Products
INNER JOIN Categories ON Products.CategoryID = Categories.CategoryID;

SELECT Orders.OrderID, Customers.CustomerName, Shippers.ShipperName
FROM Orders
INNER JOIN Customers ON Orders.CustomerID = Customers.CustomerID
INNER JOIN Shippers ON Orders.ShipperID = Shippers.ShipperID;
```

---

## LEFT JOIN

LEFT JOIN คืนค่าทุกแถวจากตารางซ้าย (table1) และแถวที่มีค่าตรงกันจากตารางขวา (table2) หากไม่มีค่าตรงกันในตารางขวา ผลลัพธ์ของคอลัมน์จากตารางขวาจะเป็น NULL คำสงวน LEFT OUTER JOIN และ LEFT JOIN มีความหมายเดียวกัน แสดงลูกค้าทุกคนพร้อมคำสั่งซื้อ รวมถึงลูกค้าที่ยังไม่เคยสั่งซื้อสินค้าเลย: หากต้องการหาเฉพาะลูกค้าที่ยังไม่เคยสั่งซื้อ ให้เพิ่มเงื่อนไข WHERE เพื่อกรองค่า NULL ในฝั่งตารางขวา:

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table1
LEFT JOIN table2
ON table1.column_name = table2.column_name;
```

### ตัวอย่าง

```sql
SELECT Customers.CustomerName, Orders.OrderID
FROM Customers
LEFT JOIN Orders ON Customers.CustomerID = Orders.CustomerID
ORDER BY Customers.CustomerName;

SELECT Customers.CustomerName, Orders.OrderID
FROM Customers
LEFT JOIN Orders ON Customers.CustomerID = Orders.CustomerID
WHERE Orders.OrderID IS NULL;
```

---

## RIGHT JOIN

RIGHT JOIN คืนค่าทุกแถวจากตารางขวา (table2) และแถวที่มีค่าตรงกันจากตารางซ้าย (table1) หากไม่มีค่าตรงกันในตารางซ้าย ผลลัพธ์ของคอลัมน์จากตารางซ้ายจะเป็น NULL คำสงวน RIGHT OUTER JOIN และ RIGHT JOIN มีความหมายเดียวกัน แสดงพนักงานทุกคนพร้อมคำสั่งซื้อที่พวกเขารับผิดชอบ รวมถึงพนักงานที่ยังไม่เคยรับคำสั่งซื้อใดเลย:

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table1
RIGHT JOIN table2
ON table1.column_name = table2.column_name;
```

### ตัวอย่าง

```sql
SELECT Orders.OrderID, Employees.LastName, Employees.FirstName
FROM Orders
RIGHT JOIN Employees ON Orders.EmployeeID = Employees.EmployeeID
ORDER BY Orders.OrderID;
```

---

## FULL JOIN (FULL OUTER JOIN)

FULL JOIN คืนค่าทุกแถวเมื่อมีความตรงกันในตารางใดตารางหนึ่ง (ตารางซ้ายหรือตารางขวา) หากแถวใดในตารางซ้ายไม่มีคู่ตรงกันในตารางขวา คอลัมน์จากตารางขวาจะเป็น NULL และในทางกลับกันก็เช่นเดียวกัน หมายเหตุ: FULL JOIN อาจคืนผลลัพธ์ที่มีขนาดใหญ่มากได้ เนื่องจากรวมทุกแถวจากทั้งสองตารางเข้าด้วยกัน ควรใช้อย่างระมัดระวังกับตารางขนาดใหญ่

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table1
FULL OUTER JOIN table2
ON table1.column_name = table2.column_name
WHERE condition;
```

### ตัวอย่าง

```sql
SELECT Customers.CustomerName, Orders.OrderID
FROM Customers
FULL OUTER JOIN Orders ON Customers.CustomerID = Orders.CustomerID
ORDER BY Customers.CustomerName;
```

---

## Self Join

Self Join คือการเชื่อมตารางกับตัวเอง โดยใช้หลักการเดียวกับ JOIN ทั่วไป แต่ตารางต้นทางและตารางปลายทางเป็นตารางเดียวกัน จึงจำเป็นต้องตั้งนามแฝง (Alias) ที่แตกต่างกันให้กับตารางทั้งสองฝั่งเพื่อแยกความแตกต่าง ค้นหาลูกค้าที่อยู่ในเมืองเดียวกัน โดยเชื่อมตาราง Customers กับตัวเอง: B.CustomerName AS CustomerName2, A.City

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table1 T1, table1 T2
WHERE condition;
```

### ตัวอย่าง

```sql
SELECT A.CustomerName AS CustomerName1,

FROM Customers A, Customers B
WHERE A.CustomerID <> B.CustomerID
AND A.City = B.City
ORDER BY A.City;
```

---

## ตัวดำเนินการ UNION

ตัวดำเนินการ UNION ใช้รวมผลลัพธ์จากคำสั่ง SELECT ตั้งแต่สองคำสั่งขึ้นไปเข้าด้วยกัน โดยจะคัดค่าที่ซ้ำกันออกโดยอัตโนมัติ (คืนเฉพาะค่าที่ไม่ซ้ำกัน) เงื่อนไขการใช้งาน UNION ● แต่ละคำสั่ง SELECT ที่นำมารวมกันต้องมีจำนวนคอลัมน์เท่ากัน ● คอลัมน์ต้องมีชนิดข้อมูลที่ใกล้เคียงหรือเข้ากันได้ ● คอลัมน์ในแต่ละคำสั่ง SELECT ต้องเรียงลำดับตรงกัน รวมรายชื่อประเทศที่ไม่ซ้ำกันจากตาราง Customers และ Suppliers: UNION ร่วมกับ WHERE

### รูปแบบคำสั่ง

```sql
SELECT column_name(s) FROM table1
UNION
SELECT column_name(s) FROM table2;
```

### ตัวอย่าง

```sql
SELECT Country FROM Customers
UNION
SELECT Country FROM Suppliers
ORDER BY Country;

SELECT City, Country FROM Customers
WHERE Country = 'Germany'
UNION
SELECT City, Country FROM Suppliers
WHERE Country = 'Germany'
ORDER BY City;
```

---

## ตัวดำเนินการ UNION ALL

UNION ALL ทำงานคล้ายกับ UNION แต่จะคืนค่าทุกแถวรวมถึงค่าที่ซ้ำกันด้วย โดยไม่มีการตัดข้อมูลซ้ำออก ทำให้ประมวลผลได้เร็วกว่า UNION ในกรณีที่ไม่จำเป็นต้องคัดค่าซ้ำ UNION ALL ร่วมกับ WHERE

### รูปแบบคำสั่ง

```sql
SELECT column_name(s) FROM table1
UNION ALL
SELECT column_name(s) FROM table2;
```

### ตัวอย่าง

```sql
SELECT Country FROM Customers
UNION ALL
SELECT Country FROM Suppliers
ORDER BY Country;

SELECT City, Country FROM Customers
WHERE Country = 'Germany'
UNION ALL
SELECT City, Country FROM Suppliers
WHERE Country = 'Germany'
ORDER BY City;
```

---

## คำสั่ง GROUP BY

คำสั่ง GROUP BY ใช้จัดกลุ่มแถวที่มีค่าเหมือนกันในคอลัมน์ที่ระบุ ให้กลายเป็นแถวสรุปเดียว มักใช้ร่วมกับฟังก์ชันรวมข้อมูล เช่น COUNT(), SUM(), AVG() เพื่อสรุปผลแยกตามกลุ่ม GROUP BY ร่วมกับ JOIN นับจำนวนคำสั่งซื้อที่จัดส่งโดยผู้ให้บริการขนส่งแต่ละราย:

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table_name
WHERE condition
GROUP BY column_name(s)
ORDER BY column_name(s);
```

### ตัวอย่าง

```sql
SELECT COUNT(CustomerID), Country
FROM Customers
GROUP BY Country;

SELECT COUNT(CustomerID), Country
FROM Customers
GROUP BY Country
ORDER BY COUNT(CustomerID) DESC;

SELECT Shippers.ShipperName, COUNT(Orders.OrderID) AS NumberOfOrders
FROM Orders
LEFT JOIN Shippers ON Orders.ShipperID = Shippers.ShipperID
GROUP BY ShipperName;
```

---

## อนุประโยค HAVING

อนุประโยค HAVING ใช้กรองผลลัพธ์ที่ได้จากการจัดกลุ่มด้วย GROUP BY โดยอิงจากค่าที่ได้จากฟังก์ชันรวมข้อมูล ในขณะที่ WHERE ไม่สามารถใช้กรองผลลัพธ์ของฟังก์ชันรวมข้อมูลได้โดยตรง จึงต้องใช้ HAVING แทน จัดเรียงผลลัพธ์จากมากไปน้อย พร้อมกรองเฉพาะประเทศที่มีลูกค้ามากกว่า 5 ราย: HAVING ร่วมกับ JOIN แสดงเฉพาะพนักงานที่จัดการคำสั่งซื้อมากกว่า 10 รายการ: หมายเหตุ: ความแตกต่างสำคัญ: WHERE ใช้กรองแถวข้อมูลก่อนจัดกลุ่ม ส่วน HAVING

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table_name
WHERE condition
GROUP BY column_name(s)
HAVING condition
ORDER BY column_name(s);
```

### ตัวอย่าง

```sql
SELECT COUNT(CustomerID), Country
FROM Customers
GROUP BY Country
HAVING COUNT(CustomerID) > 5;

SELECT COUNT(CustomerID), Country
FROM Customers
GROUP BY Country
HAVING COUNT(CustomerID) > 5
ORDER BY COUNT(CustomerID) DESC;

SELECT Employees.LastName, COUNT(Orders.OrderID) AS NumberOfOrders
FROM Orders
INNER JOIN Employees ON Orders.EmployeeID = Employees.EmployeeID
GROUP BY LastName
HAVING COUNT(Orders.OrderID) > 10;
```

---

## ตัวดำเนินการ EXISTS

ตัวดำเนินการ EXISTS ใช้ตรวจสอบว่าคำสั่งย่อย (Subquery) คืนค่าอย่างน้อยหนึ่งแถวหรือไม่ หากมีอย่างน้อยหนึ่งแถว ผลลัพธ์จะเป็น TRUE มิฉะนั้นจะเป็น FALSE

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table_name
WHERE EXISTS
(SELECT column_name FROM table_name WHERE condition);
```

### ตัวอย่าง

```sql
SELECT SupplierName
FROM Suppliers
WHERE EXISTS
(SELECT ProductName FROM Products
WHERE Products.SupplierID = Suppliers.supplierID AND Price < 20);
```

---

## ตัวดำเนินการ ANY

ตัวดำเนินการ ANY ใช้ตรวจสอบเงื่อนไขกับค่าจากคำสั่งย่อย โดยจะเป็น TRUE หากมีค่าอย่างน้อยหนึ่งค่าในผลลัพธ์ของคำสั่งย่อยที่ตรงตามเงื่อนไข เลือกสินค้าที่มีปริมาณสั่งซื้อเท่ากับ 10 อย่างน้อยหนึ่งรายการในตาราง OrderDetails:

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table_name
WHERE column_name operator ANY
(SELECT column_name FROM table_name WHERE condition);
```

### ตัวอย่าง

```sql
SELECT ProductName
FROM Products
WHERE ProductID = ANY
(SELECT ProductID FROM OrderDetails WHERE Quantity = 10);
```

---

## ตัวดำเนินการ ALL

ตัวดำเนินการ ALL ใช้ตรวจสอบเงื่อนไขกับค่าจากคำสั่งย่อย โดยจะเป็น TRUE ก็ต่อเมื่อ 'ทุกค่า' ในผลลัพธ์ของคำสั่งย่อยตรงตามเงื่อนไขที่กำหนด เลือกสินค้าที่มีปริมาณสั่งซื้อเท่ากับ 10 ในทุกรายการของตาราง OrderDetails:

### รูปแบบคำสั่ง

```sql
SELECT column_name(s)
FROM table_name
WHERE column_name operator ALL
(SELECT column_name FROM table_name WHERE condition);
```

### ตัวอย่าง

```sql
SELECT ProductName
FROM Products
WHERE ProductID = ALL
(SELECT ProductID FROM OrderDetails WHERE Quantity = 10);
```

---

## คำสั่ง SELECT INTO

คำสั่ง SELECT INTO ใช้คัดลอกข้อมูลจากตารางหนึ่งไปสร้างเป็นตารางใหม่ โดยตารางใหม่ที่ได้จะมีโครงสร้างคอลัมน์และชนิดข้อมูลตรงกับผลลัพธ์ของคำสั่ง SELECT นั้น INTO NewTable นิยมใช้ SELECT INTO เพื่อสำรองข้อมูลก่อนทำการแก้ไขหรือย้ายฐานข้อมูล: สามารถใช้ร่วมกับ JOIN เพื่อรวมข้อมูลจากหลายตารางเข้าไปในตารางใหม่ได้: INTO CustomersOrderBackup

### ตัวอย่าง

```sql
SELECT * INTO NewTable FROM Customers;

SELECT CustomerName, ContactName

FROM Customers;

SELECT * INTO NewTable
FROM Customers
WHERE Country = 'Germany';
```

---

## คำสั่ง INSERT INTO SELECT

คำสั่ง INSERT INTO SELECT ใช้คัดลอกข้อมูลจากตารางหนึ่งไปเพิ่มเข้าในอีกตารางหนึ่งที่มีอยู่แล้ว โดยข้อมูลเดิมที่มีอยู่ในตารางปลายทางจะไม่ได้รับผลกระทบใด ๆ คัดลอกข้อมูลซัพพลายเออร์ไปเป็นลูกค้าใหม่ในตาราง Customers:

### ตัวอย่าง

```sql
INSERT INTO table2
SELECT * FROM table1;

INSERT INTO table2 (column1, column2, column3, ...)
SELECT column1, column2, column3, ...
FROM table1
WHERE condition;

INSERT INTO Customers (CustomerName, City, Country)
SELECT SupplierName, City, Country
FROM Suppliers;

INSERT INTO Customers (CustomerName, City, Country)
SELECT SupplierName, City, Country
FROM Suppliers
WHERE Country = 'Germany';
```

---

## นิพจน์ CASE

นิพจน์ CASE ใช้สำหรับตรวจสอบเงื่อนไขแบบมีทางเลือกหลายทาง (คล้ายกับ if-else ในภาษาโปรแกรมทั่วไป) โดยจะไล่ตรวจเงื่อนไขทีละข้อ เมื่อพบเงื่อนไขแรกที่เป็นจริงจะคืนค่าที่กำหนดไว้ทันที และหยุดตรวจเงื่อนไขถัดไป หากไม่มีเงื่อนไขใดเป็นจริงเลย จะคืนค่าใน ELSE (ถ้ามี) แสดงชื่อลูกค้าพร้อมข้อความอธิบายปริมาณสั่งซื้อในแต่ละคำสั่งซื้อ: ใช้ CASE ร่วมกับ ORDER BY เพื่อเรียงลำดับข้อมูลตามเงื่อนไขเฉพาะ:

### รูปแบบคำสั่ง

```sql
CASE
WHEN condition1 THEN result1
WHEN condition2 THEN result2
WHEN conditionN THEN resultN
ELSE result
END;
```

### ตัวอย่าง

```sql
SELECT OrderID, Quantity,
CASE
WHEN Quantity > 30 THEN 'The quantity is greater than 30'
WHEN Quantity = 30 THEN 'The quantity is 30'
ELSE 'The quantity is under 30'
END AS QuantityText
FROM OrderDetails;

SELECT CustomerName, City, Country
FROM Customers
ORDER BY
(CASE
WHEN City IS NULL THEN Country
ELSE City
END);
```

---

## การจัดการค่า NULL: COALESCE(), IFNULL(), ISNULL(), NVL()

การคำนวณที่เกี่ยวข้องกับค่า NULL อาจให้ผลลัพธ์ที่ไม่คาดคิด เช่น หากนำค่าตัวเลขไปบวกกับ NULL ผลลัพธ์ที่ได้จะเป็น NULL เสมอ ภาษา SQL จึงมีฟังก์ชันสำหรับแทนที่ค่า NULL ด้วยค่าอื่นที่กำหนดไว้

COALESCE() — มาตรฐานที่แนะนำ ฟังก์ชัน COALESCE() เป็นฟังก์ชันมาตรฐานที่ใช้ได้กับ MySQL, SQL Server และ

Oracle

IFNULL() — สำหรับ

MySQL

ISNULL() — สำหรับ

SQL

Server

NVL() — สำหรับ Oracle หมายเหตุ: ฟังก์ชัน ISNULL() ในฐานข้อมูล Microsoft Access มีความหมายต่างออกไป คือใช้ตรวจสอบว่านิพจน์เป็น NULL หรือไม่ (คืนค่า TRUE/FALSE) ไม่ใช่การแทนที่ค่า NULL

### ตัวอย่าง

```sql
SELECT ProductName, (UnitPrice * (UnitsInStock + COALESCE(UnitsOnOrder, 0)))
FROM Products;

SELECT ProductName, (UnitPrice * (UnitsInStock + IFNULL(UnitsOnOrder, 0)))
FROM Products;

SELECT ProductName, (UnitPrice * (UnitsInStock + ISNULL(UnitsOnOrder, 0)))
FROM Products;

SELECT ProductName, (UnitPrice * (UnitsInStock + NVL(UnitsOnOrder, 0)))
FROM Products;
```

---

## โพรซีเยอร์ (Stored Procedure)

Stored Procedure คือชุดคำสั่ง SQL ที่ถูกคอมไพล์ไว้ล่วงหน้าและสามารถบันทึกไว้เพื่อเรียกใช้งานซ้ำได้ ช่วยให้สามารถนำโค้ดเดิมกลับมาใช้ซ้ำได้จากหลายแอปพลิเคชัน และช่วยเพิ่มความปลอดภัยและประสิทธิภาพในการทำงานกับฐานข้อมูล sql_statement Stored Procedure ที่มีพารามิเตอร์หลายตัว @City nvarchar(30), @PostalCode nvarchar(10)

### รูปแบบคำสั่ง

```sql
CREATE PROCEDURE procedure_name
AS
```

### ตัวอย่าง

```sql
GO;

EXEC procedure_name;

DROP PROCEDURE procedure_name;

CREATE PROCEDURE GetCustomersByCity @City nvarchar(30)
AS
SELECT * FROM Customers WHERE City = @City
GO;
EXEC GetCustomersByCity @City = 'London';
```

---

## คอมเมนต์ในภาษา SQL

คอมเมนต์ใช้เพื่ออธิบายโค้ด SQL หรือใช้ระงับการทำงานของบางส่วนในคำสั่งชั่วคราว (สำหรับการดีบัก) โดยตัวประมวลผลฐานข้อมูลจะข้ามส่วนที่เป็นคอมเมนต์ไปทั้งหมด SQL รองรับทั้งคอมเมนต์บรรทัดเดียวและคอมเมนต์หลายบรรทัด หมายเหตุ: ฐานข้อมูล Microsoft Access ไม่รองรับการใช้คอมเมนต์ คอมเมนต์บรรทัดเดียว ( -- ) ข้อความหลังเครื่องหมาย -- จนถึงท้ายบรรทัดจะถูกละเว้น: -- เลือกลูกค้าทั้งหมดจากประเทศเม็กซิโก คอมเมนต์หลายบรรทัด ( /* ... */ ) /* เลือกทุกคอลัมน์จากลูกค้าที่ อยู่ในเมือง Berlin */ ใช้เพื่อปิดการทำงานของคำสั่ง SQL หลายคำสั่งพร้อมกัน:

### ตัวอย่าง

```sql
SELECT * FROM Customers WHERE Country = 'Mexico';

SELECT * FROM Customers
-- WHERE City='Berlin';

SELECT * FROM Customers WHERE City = 'Berlin';

/*SELECT * FROM Customers;
SELECT * FROM Orders;*/
SELECT * FROM Suppliers;
```

---

## ตัวดำเนินการในภาษา SQL (SQL Operators)

ตัวดำเนินการ SQL คือคำสงวนและสัญลักษณ์ที่ใช้ในการกระทำต่าง ๆ กับค่าข้อมูล มักปรากฏอยู่ในอนุประโยค WHERE, HAVING และคำสั่งอื่น ๆ สามารถแบ่งออกเป็นหลายประเภทดังนี้ ตัวดำเนินการทางคณิตศาสตร์ (Arithmetic Operators) ตัวดำเนินการ ความหมาย + บวก - ลบ * คูณ / หาร % หารเอาเศษ ตัวดำเนินการเปรียบเทียบ (Comparison Operators) ตัวดำเนินการ ความหมาย = เท่ากับ > มากกว่า < น้อยกว่า >= มากกว่าหรือเท่ากับ <= น้อยกว่าหรือเท่ากับ <> หรือ != ไม่เท่ากับ ตัวดำเนินการผสม (Compound Operators) ตัวดำเนินการ ความหมาย += บวกแล้วกำหนดค่า -= ลบแล้วกำหนดค่า *= คูณแล้วกำหนดค่า /= หารแล้วกำหนดค่า ตัวดำเนินการระดับบิต (Bitwise Operators) ตัวดำเนินการ ความหมาย & Bitwise AND | Bitwise OR ^ Bitwise XOR ~ Bitwise NOT ตัวดำเนินการเชิงตรรกะ (Logical Operators) ตัวดำเนินการ ความหมาย AND เป็นจริงเมื่อทุกเงื่อนไขที่คั่นด้วย AND เป็นจริง OR เป็นจริงเมื่อมีอย่างน้อยหนึ่งเงื่อนไขเป็นจริง NOT กลับค่าความจริงของเงื่อนไข ANY เป็นจริงเมื่อมีค่าใดค่าหนึ่งจาก subquery ตรงตามเงื่อนไข ALL เป็นจริงเมื่อทุกค่าจาก subquery ตรงตามเงื่อนไข ตัวดำเนินการ ความหมาย BETWEEN เป็นจริงเมื่อค่าตัวดำเนินการอยู่ในช่วงที่กำหนด LIKE เป็นจริงเมื่อค่าตรงกับรูปแบบที่กำหนด IN เป็นจริงเมื่อค่าตรงกับค่าใดค่าหนึ่งในรายการ

---

## คำสั่ง CREATE DATABASE

คำสั่ง CREATE DATABASE ใช้สร้างฐานข้อมูล SQL ใหม่ โดยผู้ใช้ต้องมีสิทธิ์ของผู้ดูแลระบบฐานข้อมูล (Administrator) จึงจะสามารถสร้างหรือลบฐานข้อมูลได้ ตรวจสอบรายชื่อฐานข้อมูล สำหรับ SQL Server: สำหรับ MySQL:

### รูปแบบคำสั่ง

```sql
CREATE DATABASE databasename;
```

### ตัวอย่าง

```sql
CREATE DATABASE testDB;

SELECT name FROM sys.databases;

SHOW DATABASES;
```

---

## คำสั่ง DROP DATABASE

คำสั่ง DROP DATABASE ใช้ลบฐานข้อมูลที่มีอยู่ออกอย่างถาวร ควรใช้ด้วยความระมัดระวังเป็นอย่างมาก เนื่องจากจะลบข้อมูลทั้งหมดในฐานข้อมูลนั้นและไม่สามารถกู้คืนได้

### รูปแบบคำสั่ง

```sql
DROP DATABASE databasename;
```

### ตัวอย่าง

```sql
DROP DATABASE testDB;
```

---

## คำสั่ง BACKUP DATABASE

คำสั่ง BACKUP DATABASE ใช้ใน SQL Server เพื่อสำรองข้อมูลฐานข้อมูลทั้งหมดแบบเต็มรูปแบบ (Full Backup) เก็บไว้ในไฟล์ปลายทางที่กำหนด จะเก็บเฉพาะข้อมูลที่เปลี่ยนแปลงไปนับตั้งแต่การสำรองแบบเต็มรูปแบบครั้งล่าสุด โดยจำเป็นต้องมีการสำรองแบบเต็มรูปแบบมาก่อนอย่างน้อยหนึ่งครั้ง:

### รูปแบบคำสั่ง

```sql
BACKUP DATABASE databasename
TO DISK = 'filepath';
```

### ตัวอย่าง

```sql
BACKUP DATABASE testDB
TO DISK = 'D:\\backups\\testDB.bak';

BACKUP DATABASE testDB
TO DISK = 'D:\\backups\\testDB.bak'
WITH DIFFERENTIAL;
```

---

## คำสั่ง CREATE TABLE

คำสั่ง CREATE TABLE ใช้สร้างตารางใหม่ในฐานข้อมูล column1 datatype constraint, column2 datatype constraint, column3 datatype constraint, .... พารามิเตอร์ table_name คือชื่อตารางใหม่ที่ต้องการสร้าง ส่วน datatype คือชนิดข้อมูลของแต่ละคอลัมน์ (เช่น varchar, int, date) และ constraint คือกฎเพิ่มเติมที่กำหนดให้กับคอลัมน์นั้น สามารถใช้ SELECT INTO หรือ CREATE TABLE ... AS SELECT เพื่อสร้างตารางใหม่พร้อมคัดลอกโครงสร้างและข้อมูลจากตารางเดิม:

### รูปแบบคำสั่ง

```sql
CREATE TABLE table_name (
```

### ตัวอย่าง

```sql
);

CREATE TABLE Persons (
PersonID int,
LastName varchar(255),
FirstName varchar(255),
Address varchar(255),
City varchar(255)
);

CREATE TABLE TestTable AS
SELECT customername, contactname
FROM customers;
```

---

## คำสั่ง DROP TABLE และ TRUNCATE TABLE

คำสั่ง DROP TABLE ใช้ลบตารางออกจากฐานข้อมูลอย่างถาวร ทั้งโครงสร้างตารางและข้อมูลทั้งหมดภายในจะถูกลบไปด้วย คำสั่ง TRUNCATE TABLE หากต้องการเพียงลบข้อมูลทั้งหมดภายในตารางออก แต่ยังคงเก็บโครงสร้างตารางไว้ ให้ใช้คำสั่ง TRUNCATE TABLE แทน: หมายเหตุ: DROP TABLE ลบทั้งโครงสร้างและข้อมูล ในขณะที่ TRUNCATE TABLE ลบเฉพาะข้อมูลแต่ยังคงโครงสร้างตารางไว้ให้ใช้งานต่อได้

### รูปแบบคำสั่ง

```sql
DROP TABLE table_name;
```

### ตัวอย่าง

```sql
DROP TABLE Shippers;

TRUNCATE TABLE table_name;
```

---

## คำสั่ง ALTER TABLE

คำสั่ง ALTER TABLE ใช้เพิ่ม ลบ หรือแก้ไขคอลัมน์ในตารางที่มีอยู่แล้ว รวมถึงจัดการข้อจำกัด (Constraint) ต่าง ๆ ของตาราง ตัวอย่าง: เพิ่มคอลัมน์ Email ในตาราง Customers: เปลี่ยนชื่อคอลัมน์ สำหรับ MySQL / Oracle: ADD CONSTRAINT CHK_Age CHECK (Age >= 18); เปลี่ยนชื่อตาราง ตัวอย่าง: เปลี่ยนชื่อตาราง Customers เป็น Clients:

### ตัวอย่าง

```sql
ALTER TABLE table_name ADD column_name datatype;

ALTER TABLE Customers ADD Email varchar(255);

ALTER TABLE table_name DROP COLUMN column_name;
ALTER TABLE Customers DROP COLUMN Email;

ALTER TABLE table_name RENAME COLUMN old_name to new_name;
```

---

## ข้อจำกัดของ SQL (SQL Constraints)

ข้อจำกัด (Constraint) คือกฎที่ใช้ควบคุมข้อมูลในตาราง เพื่อจำกัดประเภทของข้อมูลที่สามารถบันทึกลงในตารางได้ ช่วยรักษาความถูกต้องและความน่าเชื่อถือของข้อมูลในฐานข้อมูล ข้อจำกัดสามารถกำหนดได้ทั้งตอนสร้างตาราง (CREATE TABLE) หรือภายหลังด้วยคำสั่ง ALTER TABLE ประเภทของข้อจำกัดที่ใช้งานบ่อย ข้อจำกัด ความหมาย NOT NULL ห้ามคอลัมน์มีค่าเป็น NULL UNIQUE ค่าทุกแถวในคอลัมน์ต้องไม่ซ้ำกัน PRIMARY KEY ระบุคีย์หลักที่ใช้ระบุความเป็นเอกลักษณ์ของแต่ละแถว (รวม NOT NULL และ UNIQUE) ข้อจำกัด ความหมาย FOREIGN KEY เชื่อมโยงข้อมูลระหว่างสองตาราง เพื่อป้องกันการกระทำที่ทำลายความสัมพันธ์ระหว่างตาราง CHECK กำหนดเงื่อนไขที่ค่าของคอลัมน์ต้องเป็นจริง DEFAULT กำหนดค่าเริ่มต้นให้กับคอลัมน์เมื่อไม่มีการระบุค่า CREATE INDEX สร้างดัชนีเพื่อช่วยให้การค้นหาข้อมูลในฐานข้อมูลรวดเร็วขึ้น

---

## ข้อจำกัด NOT NULL

ข้อจำกัด NOT NULL บังคับว่าคอลัมน์นั้นจะต้องมีค่าเสมอ ไม่สามารถเว้นว่างหรือมีค่าเป็น NULL ได้ โดยค่าเริ่มต้นของทุกคอลัมน์สามารถมีค่า NULL ได้ เว้นแต่จะระบุข้อจำกัดนี้ไว้ สำหรับ SQL Server / MS Access: สำหรับ MySQL: สำหรับ SQL Server / MS Access:

### ตัวอย่าง

```sql
CREATE TABLE Persons (
ID int NOT NULL,
LastName varchar(255) NOT NULL,
FirstName varchar(255) NOT NULL,
Age int
);

ALTER TABLE Persons ALTER COLUMN Age int NOT NULL;

ALTER TABLE Persons MODIFY COLUMN Age int NOT NULL;

ALTER TABLE Persons ALTER COLUMN Age int NULL;
```

---

## ข้อจำกัด UNIQUE

ข้อจำกัด UNIQUE รับประกันว่าค่าทุกค่าในคอลัมน์ (หรือกลุ่มคอลัมน์) จะไม่ซ้ำกัน ต่างจาก PRIMARY KEY ตรงที่ตารางหนึ่งสามารถมีข้อจำกัด UNIQUE ได้หลายคอลัมน์ แต่มี PRIMARY KEY ได้เพียงหนึ่งเดียว สำหรับ MySQL: สำหรับ SQL Server / Oracle / MS Access:

### ตัวอย่าง

```sql
CREATE TABLE Persons (
ID int NOT NULL UNIQUE,
LastName varchar(255) NOT NULL,
FirstName varchar(255),
Age int
);

CREATE TABLE Persons (
ID int NOT NULL,
LastName varchar(255) NOT NULL,
FirstName varchar(255),
Age int,
CONSTRAINT UC_Person UNIQUE (ID, LastName)
);

ALTER TABLE Persons ADD UNIQUE (ID);

ALTER TABLE Persons DROP INDEX UC_Person;
```

---

## ข้อจำกัด PRIMARY KEY

ข้อจำกัด PRIMARY KEY ใช้ระบุความเป็นเอกลักษณ์เฉพาะของแต่ละแถวในตาราง คอลัมน์ที่เป็น PRIMARY KEY จะต้องมีค่าไม่ซ้ำกันและห้ามเป็นค่า NULL ตารางหนึ่งสามารถมี PRIMARY KEY ได้เพียงหนึ่งเดียวเท่านั้น แต่สามารถประกอบด้วยหลายคอลัมน์รวมกันได้ (composite key) PRIMARY KEY จากหลายคอลัมน์ สำหรับ SQL Server / Oracle / MS Access: สำหรับ MySQL:

### ตัวอย่าง

```sql
CREATE TABLE Persons (
ID int NOT NULL,
LastName varchar(255) NOT NULL,
FirstName varchar(255),
Age int,
PRIMARY KEY (ID)
);

CREATE TABLE Persons (
ID int NOT NULL,
LastName varchar(255) NOT NULL,
FirstName varchar(255),
Age int,
CONSTRAINT PK_Person PRIMARY KEY (ID, LastName)
);

ALTER TABLE Persons ADD PRIMARY KEY (ID);

ALTER TABLE Persons DROP CONSTRAINT PK_Person;
```

---

## ข้อจำกัด FOREIGN KEY

ข้อจำกัด FOREIGN KEY ใช้เชื่อมโยงข้อมูลระหว่างสองตาราง โดยคอลัมน์ในตารางหนึ่ง (ตารางลูก) จะอ้างอิงไปยังคอลัมน์ PRIMARY KEY ของอีกตารางหนึ่ง (ตารางแม่) เพื่อป้องกันการกระทำที่จะทำลายความสัมพันธ์ระหว่างสองตาราง เช่น การลบข้อมูลในตารางแม่ที่ยังมีข้อมูลอ้างอิงอยู่ในตารางลูก สมมติว่ามีตาราง Persons (ตารางแม่) และตาราง Orders (ตารางลูก) โดยคอลัมน์ PersonID ในตาราง Orders อ้างอิงไปยังคอลัมน์ PersonID ในตาราง Persons: ADD FOREIGN KEY (PersonID) REFERENCES Persons(PersonID); สำหรับ SQL Server / Oracle / MS Access: สำหรับ MySQL:

### ตัวอย่าง

```sql
CREATE TABLE Orders (
OrderID int NOT NULL PRIMARY KEY,
OrderNumber int NOT NULL,
PersonID int,
FOREIGN KEY (PersonID) REFERENCES Persons(PersonID)
);

ALTER TABLE Orders

ALTER TABLE Orders DROP CONSTRAINT FK_PersonOrder;

ALTER TABLE Orders DROP FOREIGN KEY FK_PersonOrder;
```

---

## ข้อจำกัด CHECK

ข้อจำกัด CHECK ใช้กำหนดเงื่อนไขที่ค่าของคอลัมน์จะต้องเป็นจริงเสมอ หากมีการพยายามบันทึกค่าที่ไม่ผ่านเงื่อนไขนี้ ระบบจะปฏิเสธการบันทึกข้อมูลนั้น ตัวอย่าง: กำหนดว่าคอลัมน์ Age ต้องมีค่ามากกว่าหรือเท่ากับ 18 เท่านั้น: สำหรับ SQL Server / Oracle / MS Access: สำหรับ MySQL:

### ตัวอย่าง

```sql
CREATE TABLE Persons (
ID int NOT NULL,
LastName varchar(255) NOT NULL,
Age int,
CHECK (Age >= 18)
);

CREATE TABLE Persons (
ID int NOT NULL,
LastName varchar(255) NOT NULL,
Age int,
City varchar(255),
CONSTRAINT CHK_Person CHECK (Age >= 18 AND City = 'Sandnes')
);

ALTER TABLE Persons ADD CHECK (Age >= 18);

ALTER TABLE Persons DROP CONSTRAINT CHK_Person;
```

---

## ข้อจำกัด DEFAULT

ข้อจำกัด DEFAULT ใช้กำหนดค่าเริ่มต้นให้กับคอลัมน์ โดยค่าดังกล่าวจะถูกใส่ให้กับทุกระเบียนใหม่โดยอัตโนมัติ หากไม่มีการระบุค่าอื่นตอนเพิ่มข้อมูล สามารถใช้ค่า DEFAULT ร่วมกับฟังก์ชันระบบ เช่น การแทรกวันที่ปัจจุบันโดยอัตโนมัติ สำหรับ SQL Server: ADD CONSTRAINT df_City DEFAULT 'Sandnes' FOR City; สำหรับ SQL Server:

### ตัวอย่าง

```sql
CREATE TABLE Persons (
ID int NOT NULL,
LastName varchar(255) NOT NULL,
City varchar(255) DEFAULT 'Sandnes'
);

CREATE TABLE Orders (
ID int NOT NULL,
OrderDate date DEFAULT CURDATE()
);

ALTER TABLE Persons

ALTER TABLE Persons DROP CONSTRAINT df_City;
```

---

## คำสั่ง CREATE INDEX

ดัชนี (Index) ใช้เพื่อค้นหาข้อมูลในฐานข้อมูลได้รวดเร็วยิ่งขึ้น ผู้ใช้งานจะไม่เห็นดัชนีโดยตรง แต่เป็นเบื้องหลังที่ช่วยเร่งความเร็วในการค้นหาหรือคิวรีข้อมูล ดัชนีมีสองประเภทหลัก คือแบบไม่ซ้ำกัน (Non-unique) ซึ่งอนุญาตให้มีค่าซ้ำกันได้ และแบบไม่ซ้ำกันเลย (Unique) ซึ่งบังคับให้ค่าในคอลัมน์ต้องไม่ซ้ำกัน สร้างดัชนีแบบไม่ซ้ำกัน (Non-unique) บนคอลัมน์ LastName ของตาราง Persons: คำสั่ง DROP INDEX สำหรับ SQL Server: สำหรับ MySQL: สำหรับ MS Access: สำหรับ DB2 / Oracle: สรุป เอกสารฉบับนี้ได้เรียบเรียงเนื้อหาภาษา SQL อย่างครอบคลุม ตั้งแต่แนวคิดพื้นฐานของฐานข้อมูลเชิงสัมพันธ์ คำสั่งดึงข้อมูลด้วย SELECT การกรองข้อมูลด้วย WHERE, AND, OR, NOT, LIKE, IN, BETWEEN การเรียงลำดับด้วย ORDER BY การจัดการข้อมูลด้วย INSERT INTO, UPDATE, DELETE การจัดการค่า NULL (รวมถึง COALESCE, IFNULL, ISNULL, NVL) การจำกัดจำนวนผลลัพธ์ ฟังก์ชันรวมข้อมูล MIN(), MAX(), COUNT(), SUM(), AVG() การใช้นามแฝง (Aliases) การเชื่อมตารางด้วย JOIN ทุกรูปแบบ การรวมผลลัพธ์ด้วย UNION และ UNION ALL การจัดกลุ่มข้อมูลด้วย GROUP BY และ HAVING ตัวดำเนินการกับคำสั่งย่อยอย่าง EXISTS, ANY, ALL การคัดลอกข้อมูลด้วย SELECT INTO และ INSERT INTO SELECT นิพจน์ CASE โพรซีเยอร์ (Stored Procedure) นอกจากนี้ยังครอบคลุมคำสั่งจัดการโครงสร้างฐานข้อมูลและตาราง ได้แก่ CREATE DATABASE, TABLE, ALTER TABLE รวมถึงข้อจำกัด (Constraints) ที่สำคัญ ได้แก่ NOT NULL, UNIQUE, PRIMARY KEY, FOREIGN KEY, CHECK, DEFAULT และการสร้างดัชนีด้วย CREATE INDEX เนื้อหาทั้งหมดนี้ครอบคลุมพื้นฐานสำคัญของภาษา SQL ที่ใช้งานจริงในการพัฒนาและดูแลระบบฐานข้อมูลเชิงสัมพันธ์ แหล่งอ้างอิง: https://www.w3schools.com/sql/

### รูปแบบคำสั่ง

```sql
CREATE INDEX index_name ON table_name (column1, column2, ...);
```

### ตัวอย่าง

```sql
CREATE UNIQUE INDEX index_name ON table_name (column1, column2, ...);

CREATE INDEX idx_lastname ON Persons (LastName);

CREATE INDEX idx_pname ON Persons (LastName, FirstName);

DROP INDEX table_name.index_name;
```

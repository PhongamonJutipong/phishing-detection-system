# คู่มือติดตั้งและเริ่มพัฒนาต่อ — PhishMail

เอกสารนี้สำหรับคนที่เพิ่งได้รับโปรเจคนี้มาและต้องการรันให้ขึ้นแล้วพัฒนาต่อ
ทำตามตั้งแต่ต้นจนจบใช้เวลาประมาณ 20–30 นาที ส่วนใหญ่เป็นเวลารอติดตั้ง

---

## ระบบนี้คืออะไร

ระบบตรวจจับอีเมลฟิชชิงด้วยการประมวลผลภาษาธรรมชาติ รองรับทั้งภาษาไทยและอังกฤษ
ประกอบด้วย 4 ส่วนที่ทำงานร่วมกัน

| ส่วน | โฟลเดอร์ | หน้าที่ |
|---|---|---|
| ML pipeline | `ml/` | เตรียมข้อมูล เทรนโมเดล TF-IDF + Naive Bayes แยกตามภาษา |
| Backend API | `backend/` | FastAPI + PostgreSQL รับข้อความอีเมลแล้วตอบคะแนนความเสี่ยง |
| หน้าเว็บ | `backend/app/web/` | หน้าเว็บวางข้อความแล้วกดตรวจสอบ เสิร์ฟจาก backend ตัวเดียวกัน |
| ส่วนขยาย Chrome | `extension/` | ตรวจอัตโนมัติขณะเปิดอ่านอีเมลใน Gmail |

หน้าเว็บกับส่วนขยายเรียก `POST /api/v1/analyze` ตัวเดียวกัน จึงได้ผลลัพธ์ตรงกันเสมอ

---

## สิ่งที่ต้องมีก่อน

| โปรแกรม | เวอร์ชัน | หมายเหตุ |
|---|---|---|
| **Python** | **3.11** | ทดสอบกับ 3.11 เท่านั้น เวอร์ชันอื่นอาจติดปัญหา dependency |
| **Docker Desktop** | ล่าสุด | ใช้รัน PostgreSQL และ backend |
| **Git** | ล่าสุด | สำหรับ clone และ commit |
| **Google Chrome** | ล่าสุด | เฉพาะตอนจะทดสอบส่วนขยาย |

ดาวน์โหลด Python 3.11: <https://www.python.org/downloads/release/python-3119/>
ตอนติดตั้ง **ต้องติ๊ก "Add python.exe to PATH"** ไม่งั้นคำสั่งข้างล่างจะหา Python ไม่เจอ

ดาวน์โหลด Docker Desktop: <https://www.docker.com/products/docker-desktop/>

---

## ติดตั้งแบบรวดเดียว (Windows)

```powershell
git clone https://github.com/PhongamonJutipong/phishing-detection-system.git
cd phishing-detection-system
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

สคริปต์จะทำให้ครบทุกอย่าง

1. ตรวจว่ามี Python 3.11
2. สร้าง virtual environment ที่ `.venv`
3. ติดตั้ง dependencies ทั้งหมด
4. สร้าง `backend\.env` **พร้อมสุ่มกุญแจเข้ารหัสและ admin token ให้เอง**
5. เทรนโมเดลจากชุดข้อมูลจำลอง
6. รันเทสต์เพื่อยืนยันว่าใช้งานได้จริง
7. ตรวจว่า Docker พร้อม

สคริปต์**ไม่เขียนทับ**ไฟล์ที่มีอยู่แล้ว รันซ้ำได้ปลอดภัย ถ้ามี `.venv` หรือ `backend\.env`
หรือโมเดลอยู่แล้วจะข้ามขั้นตอนนั้นไป

จบแล้วต้องเห็นข้อความ `พร้อมใช้งานแล้ว` และเทสต์ผ่าน 33 ข้อ

---

## ติดตั้งเอง (macOS / Linux หรือเมื่อสคริปต์มีปัญหา)

```bash
# 1. virtual environment
python3.11 -m venv .venv
source .venv/bin/activate          # Windows ใช้ .venv\Scripts\activate

# 2. dependencies
pip install -r backend/requirements.txt -r ml/requirements.txt -r requirements-dev.txt

# 3. ไฟล์ตั้งค่า
cp backend/.env.example backend/.env
```

เปิด `backend/.env` แล้วเติมสองค่านี้ (สร้างด้วยคำสั่งข้างล่าง)

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"                                # ADMIN_TOKEN
```

```bash
# 4. เทรนโมเดล (สำคัญมาก ดูหัวข้อถัดไป)
cd ml
python preprocess.py --include-mock
python train.py
cd ..

# 5. ยืนยัน
python -m pytest
```

### ทำไมต้องเทรนโมเดลเอง

ไฟล์โมเดล `backend/ml_model/**/*.pkl` **อยู่ใน `.gitignore`** เพราะเป็นผลลัพธ์ที่สร้างใหม่ได้
ไม่ใช่ซอร์สโค้ด การ clone มาเฉย ๆ จะยังไม่มีโมเดล และ backend จะขึ้นไม่ได้

**ไม่ต้องกังวล ใช้เวลารวมประมาณ 5 วินาที** ไม่ได้ใช้ GPU และไม่ต้องดาวน์โหลดอะไรเพิ่ม

ลำดับการทำงาน

```
ml/data/mock_email_dataset.xlsx                    อยู่ใน git (23 KB)
        |
        |  preprocess.py --include-mock            ~4 วินาที
        |  ทำความสะอาด ตัดคำ แยกภาษา แบ่ง 80/20
        v
ml/data/processed/{en,th}/train.csv + test.csv     ไม่อยู่ใน git
        |
        |  train.py                                ~1 วินาที
        |  สร้าง TF-IDF แล้วเทรน Naive Bayes แยกภาษา
        v
backend/ml_model/{en,th}/                          ไม่อยู่ใน git
        ├── tfidf_vectorizer.pkl     ~36 KB   คลังคำและน้ำหนักของแต่ละคำ
        ├── naive_bayes_model.pkl    ~29 KB   ตัวจำแนกที่เรียนรู้แล้ว
        └── model_metadata.json               เทรนเมื่อไร ด้วยข้อมูลกี่แถว ได้ผลเท่าไร
```

backend จะโหลดไฟล์ `.pkl` เหล่านี้ตอนเริ่มทำงาน **ถ้าไม่มี** จะเกิดอาการนี้

- `GET /api/v1/health` ตอบ `"models_loaded": []`
- `POST /api/v1/analyze` ตอบ **503** พร้อมข้อความว่าโมเดลยังไม่พร้อม
- หน้าเว็บกับส่วนขยายจะขึ้นว่าวิเคราะห์ไม่สำเร็จ

เหตุผลที่ไม่เก็บลง git เหมือน `.venv/` คือเป็นไฟล์ไบนารีที่ถูกเขียนใหม่ทั้งไฟล์ทุกครั้งที่เทรน
ถ้าเก็บลง git ประวัติจะบวมเร็วมากโดยไม่ได้ประโยชน์ ในเมื่อสร้างใหม่ได้ใน 5 วินาที

`--include-mock` จะอ่านสองไฟล์รวมกัน

| ไฟล์ | ที่มา | จำนวน |
|---|---|---|
| `ml/data/mock_email_dataset.xlsx` | ชุดจำลองเดิมของโครงงาน | ~230 ฉบับ |
| `ml/data/synthetic_email_dataset.csv` | เขียนขึ้นเองเพื่อขยายคลังคำ ไม่ได้มาจากอีเมลจริง | 120 ฉบับ (ฟิชชิง 60 / ปกติ 60) |

ไฟล์ที่สองครอบคลุมหัวข้อที่ชุดเดิมไม่มี เช่น พัสดุตกค้าง ภาษี ค่าไฟ เงินกู้ การลงทุน
บัตรเครดิต และอีเมลปกติจากบริบทมหาวิทยาลัยกับที่ทำงาน ทำให้คลังคำกว้างขึ้นกว่าเท่าตัว

> **ข้อควรระวังสำคัญ** ทั้งสองไฟล์เป็นข้อมูลที่สร้างขึ้น ไม่ใช่อีเมลจริง
> ใช้ทดสอบว่า pipeline ทำงานได้และลดปัญหาคำที่ไม่เคยเห็นเท่านั้น
> **ห้ามนำค่าความแม่นยำที่ได้ไปรายงาน**

### เทรนด้วยชุดข้อมูลจริง

วางไฟล์ `.csv` หรือ `.xlsx` ที่มีคอลัมน์ข้อความกับป้ายกำกับไว้ใน `ml/data/raw/`
แล้วรัน `preprocess.py` **โดยไม่ใส่** `--include-mock`

ถ้าชุดข้อมูลอยู่นอกโปรเจค (เช่นไฟล์ใหญ่ที่ไม่อยากคัดลอกเข้ามา) ใช้ `--extra-dir` ชี้ไปที่โฟลเดอร์นั้นได้

```bash
cd ml
python preprocess.py --extra-dir "C:/path/to/dataset-folder"
python train.py
```

ชื่อคอลัมน์ยืดหยุ่นได้ ระบบรับ `text` / `body` / `content` เป็นข้อความ
และ `label` / `is_phishing` เป็นป้ายกำกับ ค่าป้ายกำกับรับทั้งตัวเลข `1`/`0`
และคำเช่น `spam`/`ham`, `phishing`/`legitimate` แถวที่อ่านป้ายกำกับไม่ออกจะถูกตัดทิ้งพร้อมแจ้งจำนวน

> **ข้อควรระวังเรื่องการตีความ** ชุดข้อมูลสาธารณะจำนวนมากติดป้ายว่า **spam**
> ซึ่งกว้างกว่า **phishing** เพราะรวมโฆษณาที่ไม่ได้หลอกเอาข้อมูลเข้าไปด้วย
> ถ้าเทรนด้วยชุดแบบนั้น โมเดลจะเรียนรู้ว่า "อีเมลไม่พึงประสงค์" มากกว่า "อีเมลหลอกเอาข้อมูล"
> ต้องเขียนกำกับความแตกต่างนี้ไว้ในเอกสารตอนรายงานผล
> ค่าที่ใช้รายงานต้องมาจากชุดข้อมูลจริงประมาณ 18,500 ฉบับ ตามบทที่ 3.3.2
> ถ้ามีชุดข้อมูลจริงให้วางไฟล์ `(text,label)` ใน `ml/data/raw/` แล้วรัน `preprocess.py` โดยไม่ใส่ `--include-mock`

---

## รันระบบ

เปิด **Docker Desktop** ก่อน รอจนไอคอนวาฬนิ่ง แล้วสั่ง

```bash
docker compose up -d --build
```

ตรวจว่าขึ้นครบ

```bash
docker compose ps
```

ต้องเห็นทั้งสองตัวเป็น `Up ... (healthy)`

```
phishing_backend    Up (healthy)   0.0.0.0:8000->8000/tcp
phishing_postgres   Up (healthy)   0.0.0.0:5432->5432/tcp
```

เปิดใช้งานได้ที่

| ที่อยู่ | คือ |
|---|---|
| <http://127.0.0.1:8000/> | หน้าแรกแนะนำระบบ |
| <http://127.0.0.1:8000/scan.html> | **หน้าตรวจสอบอีเมล** วางข้อความแล้วกดตรวจ |
| <http://127.0.0.1:8000/dashboard.html> | หน้าภาพรวมผู้ดูแล (แบบร่าง ใช้ข้อมูลตัวอย่าง) |
| <http://127.0.0.1:8000/docs> | เอกสาร API แบบกดทดลองได้ |

### คำสั่งที่ใช้บ่อย

| คำสั่ง | ผล |
|---|---|
| `docker compose logs -f backend` | ดู log แบบเรียลไทม์ |
| `docker compose restart backend` | รีสตาร์ทเฉพาะ backend |
| `docker compose stop` | หยุดชั่วคราว ข้อมูลอยู่ครบ |
| `docker compose down` | ลบคอนเทนเนอร์ **ข้อมูลยังอยู่** |
| `docker compose down -v` | **ลบข้อมูลทั้งหมดด้วย ใช้เมื่อตั้งใจล้างเท่านั้น** |

---

## ติดตั้งส่วนขยาย Chrome

1. เปิด `chrome://extensions`
2. เปิดสวิตช์ **Developer mode** มุมขวาบน
3. กด **Load unpacked** แล้วเลือกโฟลเดอร์ `extension` (โฟลเดอร์ที่มี `manifest.json` อยู่ข้างใน ไม่ใช่โฟลเดอร์โปรเจคชั้นนอก)
4. เปิด <https://mail.google.com> แล้ว **กด F5 รีโหลด** ถ้าเปิดค้างไว้อยู่ก่อนแล้ว
5. ครั้งแรกจะมีหน้าต่างขอความยินยอม กด **อนุญาต**
6. เปิดอ่านอีเมล จะเห็นป้ายระดับความเสี่ยงมุมขวาล่าง

ส่วนขยายทำงานเฉพาะบน `https://mail.google.com` และ**ต้องมี backend รันอยู่** ไม่งั้นจะขึ้นว่าวิเคราะห์ไม่สำเร็จ

---

## พัฒนาต่อ

### รันแบบ dev (แก้โค้ดแล้วเห็นผลทันที)

รัน Postgres ในคอนเทนเนอร์ แต่รัน backend บนเครื่องเพื่อให้ hot reload ทำงาน

```bash
docker compose up -d postgres
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head     # ครั้งแรก หรือเมื่อ models.py เปลี่ยน
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

> **ต้องสั่งจากโฟลเดอร์ `backend` เท่านั้น** เพราะ `app/config.py` อ่าน `.env` แบบอิงจากโฟลเดอร์ปัจจุบัน
> ถ้าสั่งจากโฟลเดอร์โปรเจคชั้นนอก ระบบจะหา `.env` ไม่เจอแล้ว **กุญแจเข้ารหัสจะกลายเป็นค่าว่างโดยไม่มีข้อความเตือนชัดเจน**
> แต่ `DATABASE_URL` จะยังใช้ค่า default ที่ชี้ Postgres ได้ ทำให้ดูเหมือนทำงานปกติ หาสาเหตุยากมาก

แต่ตอนรันแบบ dev นี้ `DATABASE_URL` ใน `backend/.env` ต้องชี้ `localhost` ไม่ใช่ `postgres`
(ชื่อ `postgres` ใช้ได้เฉพาะภายในเครือข่ายของ Docker)

### รันเทสต์

```bash
.venv\Scripts\python.exe -m pytest          # จากโฟลเดอร์โปรเจคชั้นนอก
```

เทสต์ใช้ SQLite ชั่วคราวและเทรนโมเดลจิ๋วตอนรัน **ไม่ต้องมี Docker หรือ PostgreSQL**
ปัจจุบันมี 33 ข้อ ทุกข้อต้องผ่านก่อน commit

### แก้โครงสร้างฐานข้อมูล

โครงสร้างตารางเป็นของ **Alembic** ไม่ใช่ `create_all()` ถ้าแก้ `backend/app/db/models.py` ต้องทำ migration ด้วย

```bash
cd backend
../.venv/Scripts/python.exe -m alembic revision --autogenerate -m "อธิบายสั้น ๆ"
../.venv/Scripts/python.exe -m alembic upgrade head
```

ถ้าลืมทำ migration ระบบจะขึ้นได้ตามปกติแล้วไปพังตอนเขียนข้อมูลแทน

คอนเทนเนอร์ backend รัน `alembic upgrade head` ให้เองตอนเริ่มทำงาน จึงไม่ต้องสั่งเองเมื่อใช้ Docker

### วัดผลตามบทที่ 3.4

```bash
python evaluation/benchmark_latency.py --limit 200      # ความแม่นยำ >= 85%, Mean Latency <= 2 วินาที
python evaluation/survey_analysis.py responses.csv --group-column "สถานะ"
```

---

## ค่าตั้งต้นด้านความเป็นส่วนตัว

ระบบตั้งค่าไว้แบบ **ไม่เก็บข้อมูลส่วนบุคคลก่อน** ถ้าจะเก็บต้องเปิดเองและต้องแจ้งผู้ใช้

| ค่าใน `backend/.env` | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `STORE_EMAIL_CONTENT` | `false` | ไม่เก็บเนื้อหาอีเมล (เมื่อเปิด จะเข้ารหัสด้วย Fernet ก่อนบันทึก) |
| `STORE_NLP_ARTIFACTS` | `false` | ไม่เก็บคำที่ตัดได้รายอีเมล |
| `DATA_RETENTION_DAYS` | `90` | ลบข้อมูลอัตโนมัติเมื่อครบกำหนด |
| `ANALYZE_RATE_LIMIT_PER_MINUTE` | `60` | จำกัดคำขอต่อผู้เรียกต่อนาที |

> **ถ้าจะเก็บข้อมูลไปทำวิจัยบทที่ 4 ต้องตั้ง `STORE_NLP_ARTIFACTS=true`**
> แต่ต้องรู้ว่าคอลัมน์ `word` เก็บคำของอีเมลเป็นข้อความธรรมดาผูกกับ `email_id`
> ใครอ่านฐานข้อมูลได้ก็ประกอบเนื้อหาอีเมลกลับได้ แม้เนื้อหาหลักจะเข้ารหัสไว้
> **ห้ามเปิดค่านี้บนระบบที่ให้คนอื่นใช้จริง**

รายละเอียดทั้งหมดอยู่ใน [privacy-policy.md](privacy-policy.md)

---

## ปัญหาที่เจอบ่อย

### `docker compose up` แล้วขึ้น error หา `backend/.env` ไม่เจอ

ต้องสร้างไฟล์นี้**ก่อน** สั่ง `up` เสมอ เพราะ `docker-compose.yml` อ่านค่าความลับจากไฟล์นี้ผ่าน `env_file`

```bash
cp backend/.env.example backend/.env
```

แล้วเติม `ENCRYPTION_KEY` กับ `ADMIN_TOKEN` (ดูคำสั่งสร้างในหัวข้อติดตั้งเอง)

### `cannot find the file specified` ตอนสั่ง docker

Docker Desktop ยังไม่ได้เปิด เปิดโปรแกรมแล้วรอจนขึ้นว่า Engine running

### backend ขึ้นแล้วแต่ `/api/v1/health` ตอบว่าโมเดลไม่พร้อม

ยังไม่ได้เทรนโมเดล กลับไปทำขั้นตอนเทรนโมเดล แล้วสั่ง `docker compose restart backend`

### ระบบช้าประมาณ 2 วินาทีทุกคำขอบน Windows

ใช้ `localhost` แทน `127.0.0.1` อยู่ — บน Windows การต่อผ่านชื่อ `localhost` จะลอง IPv6 (`::1`) ก่อน
แล้วค่อยถอยมา IPv4 เสียเวลาคงที่ประมาณ 2 วินาทีต่อคำขอ ทั้งที่เวลาประมวลผลจริงอยู่ระดับ 7 มิลลิวินาที

**ใช้ `127.0.0.1` เสมอ** ทั้งในเบราว์เซอร์ ในสคริปต์วัดผล และในค่า `API_ENDPOINT` ของส่วนขยาย
ถ้าวัดผลผ่าน `localhost` จะสรุปผิดว่าไม่ผ่านเกณฑ์ข้อ 1.4.2

### รันสคริปต์ Python แล้วขึ้น `UnicodeEncodeError: 'charmap' codec`

หน้าต่างคำสั่งบน Windows ใช้ cp1252 ซึ่งพิมพ์ภาษาไทยไม่ได้ แก้ด้วยการตั้งตัวแปรก่อนรัน

```powershell
$env:PYTHONIOENCODING = "utf-8"
```

### แก้ไฟล์ในส่วนขยายแล้วไม่เห็นผล

ต้องกดไอคอนรีเฟรชบนการ์ดส่วนขยายใน `chrome://extensions` **แล้วรีโหลดแท็บ Gmail อีกครั้ง**

### เขียนสคริปต์ PowerShell ที่มีภาษาไทยแล้วพาร์สไม่ผ่าน

Windows PowerShell 5.1 อ่านไฟล์ `.ps1` เป็น cp1252 ถ้าไม่มี BOM
ต้องบันทึกไฟล์เป็น **UTF-8 with BOM** ไม่ใช่ UTF-8 เปล่า

---

## สิ่งที่ยังค้างอยู่

รายการงานที่รู้อยู่แล้วว่าต้องทำต่อ เรียงตามความสำคัญ

1. **โมเดลเทรนจากข้อมูลจำลอง** — ต้องหาชุดข้อมูลจริงมาเทรนใหม่ก่อนนำผลไปรายงาน
   ค่าความแม่นยำ `1.0` ใน `ml/results/` ไม่มีความหมาย เพราะข้อมูลน้อยเกินไป
2. **หน้าเว็บยังไม่รองรับสองภาษา** — หน้า `index.html`, `dashboard.html`, `login.html`
   ยังเป็นภาษาไทยอย่างเดียว ส่วน `scan.html` กับส่วนขยายสลับภาษาได้แล้ว
   ถ้าจะทำต้องแยกกลไก i18n ออกจาก `app.js` ก่อน เพราะตอนนี้ผูกกับ DOM ของหน้าสแกน
3. **`dashboard.html` ยังเป็นข้อมูลตัวอย่าง** — ยังไม่ได้ต่อกับ `GET /api/v1/stats`
4. **`login.html` เป็นแบบร่าง** — ฟอร์มไม่ส่งข้อมูลไปไหน ยังไม่มีระบบยืนยันตัวตนจริง
   และการตรวจอีเมลไม่ได้บังคับให้เข้าสู่ระบบ
5. **rate limit นับในโปรเซสเดียว** — ถ้าขยายเป็นหลาย worker ต้องย้ายไปใช้ Redis
   หรือจำกัดที่ reverse proxy แทน

---

## เอกสารอื่น

| ไฟล์ | เนื้อหา |
|---|---|
| [`README.md`](../README.md) | ภาพรวมระบบ โครงสร้างโฟลเดอร์ และรายการ API |
| [`privacy-policy.md`](privacy-policy.md) | นโยบายความเป็นส่วนตัว ไทยและอังกฤษ |
| [`chrome-web-store-listing.md`](chrome-web-store-listing.md) | ข้อความสำหรับส่งส่วนขยายขึ้น Chrome Web Store |
| [`agents/`](agents/) | คู่มือสำหรับ AI agent ที่มาช่วยพัฒนาต่อ |

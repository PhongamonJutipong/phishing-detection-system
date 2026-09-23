# ระบบตรวจจับอีเมลฟิชชิงโดยใช้การประมวลผลภาษาธรรมชาติ (หน้าเว็บ + Chrome Extension)

โค้ดชุดนี้พัฒนาตามเอกสารโครงงาน บทที่ 1–3 (ขอบเขต 1.5, แผนภาพยูสเคส/คลาส/ลำดับงาน/กิจกรรม,
ER diagram + พจนานุกรมข้อมูล, การออกแบบหน้าจอ และวิธีการวัดผล 3.4)

> ### เพิ่งได้รับโปรเจคนี้มา เริ่มที่นี่
>
> อ่าน **[docs/SETUP.md](docs/SETUP.md)** — คู่มือติดตั้งตั้งแต่ต้นจนรันได้ พร้อมปัญหาที่เจอบ่อยและสิ่งที่ยังค้างอยู่
>
> ติดตั้งและเริ่มระบบด้วยคำสั่งเดียวบน Windows:
> ```
> scripts\setup.bat
> ```
>
> สคริปต์จะทำให้ครบตั้งแต่สร้าง virtual environment ติดตั้ง dependencies
> สร้างไฟล์ตั้งค่าพร้อมสุ่มกุญแจเข้ารหัส เทรนโมเดล รันเทสต์ เปิด Docker Desktop
> สร้าง image เริ่มระบบ รอจนพร้อม แล้วเปิดหน้าเว็บให้อัตโนมัติ
>
> **สำคัญ:** ไฟล์โมเดล `.pkl` ไม่ได้อยู่ใน git ต้องเทรนเองก่อนถึงจะรันระบบได้
> (สคริปต์ข้างบนทำให้แล้ว)

```
phishing-detection-system/
├── common/                      # โค้ดที่ ml/ และ backend/ ใช้ร่วมกัน (single source of truth)
│   ├── text_cleaning.py         # กำจัดข้อมูลขยะ, ตัดคำ (pythainlp + คลังคำ), ลบคำหยุด, ตรวจภาษา
│   └── resources/               # stopwords_th.txt, custom_dict_th.txt
│
├── ml/                          # บทที่ 3.3.2–3.3.3
│   ├── data/mock_email_dataset.xlsx   # ชุดข้อมูลจำลอง (อังกฤษ + ไทย) สำหรับทดสอบ pipeline
│   ├── preprocess.py            # EDA + ทำความสะอาด + แบ่ง 80/20 แยกภาษา -> data/processed/{en,th}/
│   ├── evaluate.py              # เปรียบเทียบ 5 อัลกอริทึม x 6 ตัวชี้วัด -> results/
│   └── train.py                 # TF-IDF + Naive Bayes ต่อภาษา -> backend/ml_model/{en,th}/
│
├── backend/                     # FastAPI + PostgreSQL (คลาสตามแผนภาพคลาส รูปที่ 3.2)
│   └── app/
│       ├── config.py            # Class Config (MIN_RISK_THRESHOLD, getConfig)
│       ├── core/logger.py       # Class Logger (logError, logInfo)
│       ├── nlp/nlp_process.py   # Class NLPProcess (tokenize, removeStopWords, vectorize)
│       ├── ml/phishing_model.py # Class PhishingModel (loadModel, predict)
│       ├── ml/model_registry.py # โมเดลแยกภาษาไทย/อังกฤษ + reload โมเดลใหม่
│       ├── db/models.py         # 6 ตารางตาม ER diagram (ตารางที่ 3.9–3.14)
│       ├── db/database_manager.py  # Class DatabaseManager (checkData, encrypt, saveSecureLog, getFeedbackData)
│       ├── services/phishing_analyzer.py  # Class PhishingAnalyzer (processRequest, generateResponse)
│       ├── api/routes.py        # REST API
│       └── web/                 # ผลลัพธ์ build ของ Angular (ไม่อยู่ใน git สร้างด้วย npm run build)
│
├── frontend/                    # หน้าเว็บ Angular 22 (standalone components + signals)
│   └── src/app/
│       ├── core/               # ApiService, I18nService (ไทย/อังกฤษ), ชนิดข้อมูลของ API
│       ├── shared/             # แถบนำทาง ส่วนท้าย ไอคอน
│       └── pages/              # home, scan, dashboard, login (lazy load ทุกหน้า)
│
├── extension/                   # Chrome Extension (Manifest V3)
│   ├── config.js                # Class Config
│   ├── email.js                 # Class Email (getDetails)
│   ├── email_scanner.js         # Class EmailScanner (scanDOM, fetchEmailBody, sendToBackend)
│   ├── user_interface.js        # Class UserInterface (showResult, renderRiskSummary, showDetailedAnalysis)
│   ├── privacy_consent.js       # หน้าจอนโยบายความเป็นส่วนตัว (รูปที่ 3.15–3.16)
│   ├── i18n.js                  # ข้อความไทย/อังกฤษ
│   ├── background.js            # service worker เรียก API + จัดการข้อผิดพลาด
│   └── popup.*                  # ตั้งค่า API, ภาษา, เปิด/ปิด, สถานะการเชื่อมต่อ
│
├── evaluation/                  # บทที่ 3.4
│   ├── benchmark_latency.py     # ค่าความแม่นยำ (3.1), Individual/Mean Latency (3.2–3.3)
│   └── survey_analysis.py       # ค่าเฉลี่ย, S.D., ร้อยละ, อันตรภาคชั้น + แปลผลตามตารางที่ 3.15
│
├── scripts/setup.bat            # ติดตั้งและเริ่มระบบด้วยคำสั่งเดียว (เรียก setup.ps1)
├── docs/                        # SETUP.md (คู่มือติดตั้ง), privacy-policy.md, chrome-web-store-listing.md
│
├── pyproject.toml               # แหล่งข้อมูลเดียวของ dependencies + ตั้งค่า pytest + ประกาศแพ็กเกจ
├── .github/workflows/ci.yml     # CI/CD: test, build Docker image, สั่งเทรนโมเดลใหม่
└── docker-compose.yml           # postgres + backend
```

### การจัดการ dependencies

`pyproject.toml` ที่ระดับ repo root เป็น**แหล่งข้อมูลเดียว** ของทั้งรายการ dependencies
การตั้งค่า pytest และการประกาศว่าอะไรเป็นแพ็กเกจ

```bash
pip install -e ".[ml,dev]"    # ติดตั้งครบสำหรับพัฒนา
pip install .                 # เฉพาะที่ระบบต้องใช้ตอนให้บริการ (Docker ใช้แบบนี้)
```

| กลุ่ม | มีอะไร | ใช้เมื่อ |
|---|---|---|
| หลัก | fastapi, sqlalchemy, alembic, scikit-learn, pythainlp | รันเซิร์ฟเวอร์ |
| `[ml]` | pandas, openpyxl | เตรียมข้อมูลและเทรนโมเดล |
| `[dev]` | pytest, httpx | รันเทสต์ |

การติดตั้งแบบ editable ทำให้ `import app.*` และ `import common.*` ใช้ได้เหมือนกัน
ไม่ว่าจะรันจากโฟลเดอร์ไหน จึงไม่ต้องเติม `sys.path` ด้วยมือในแต่ละไฟล์อีกต่อไป

ไฟล์ `requirements*.txt` ทั้งสามยังอยู่เพื่อความเข้ากันได้ แต่ข้างในเป็นเพียงตัวชี้มาที่ `pyproject.toml`
ไม่ได้ระบุเวอร์ชันซ้ำ จึงไม่มีทางที่สองที่จะไม่ตรงกัน

## ช่องทางการใช้งาน 2 แบบ

| แบบ | ใช้เมื่อ | ขั้นตอน |
|---|---|---|
| **หน้าเว็บ** `http://127.0.0.1:8000/scan` | ตรวจอีเมลที่คัดลอกมาจากที่ไหนก็ได้ / ใช้ตอนสาธิตและเก็บผลประเมิน | วางข้อความ -> กด **ตรวจสอบอีเมล** (หรือ Ctrl+Enter) |
| **ส่วนขยาย Chrome** | ตรวจอัตโนมัติขณะเปิดอ่านใน Gmail | ติดตั้งครั้งเดียว แล้วเปิดอีเมลได้เลย |

ทั้งสองแบบเรียก `POST /api/v1/analyze` ตัวเดียวกัน จึงได้ผลลัพธ์เหมือนกัน

### หน้าเว็บ

หน้าเว็บเป็น **Angular 22** (โค้ดอยู่ใน `frontend/`) build เป็นไฟล์ static แล้วเสิร์ฟจาก backend ตัวเดียวกับ API
จึงไม่ต้องตั้งค่าที่อยู่เซิร์ฟเวอร์และไม่ติดปัญหา CORS

เปิด `http://127.0.0.1:8000/scan` หลังรัน backend — ไม่ต้องติดตั้งหรือล็อกอิน มีปุ่ม **ใส่ตัวอย่างอีเมล** สำหรับสาธิต
และสลับภาษาไทย/อังกฤษได้ที่มุมขวาบน ผลลัพธ์แสดงวงกลมเปอร์เซ็นต์ความเสี่ยง 3 สี, ประเภทของอีเมล,
รายละเอียดการวิเคราะห์ และเนื้อหาอีเมลที่ไฮไลต์คำเสี่ยงไว้ (มุมขวาบนมีไฟสถานะบอกว่าระบบพร้อมใช้งานหรือไม่)

ทุกหน้าสลับภาษาไทย/อังกฤษได้ทั้งหมด รวมหัวข้อในตารางของหน้าภาพรวม

หน้าอื่นในชุดเดียวกัน: `/` หน้าแรกแนะนำระบบ, `/dashboard` หน้าภาพรวมผู้ดูแล (แบบร่าง ใช้ข้อมูลตัวอย่าง),
`/login` หน้าเข้าสู่ระบบ (แบบร่าง ไม่บังคับใช้งาน — ตรวจอีเมลได้โดยไม่ต้องเข้าสู่ระบบ)

## การทำงานของระบบ (UC-01)

1. ผู้ใช้เปิดอีเมลใน Gmail (ครั้งแรกจะมีหน้าต่างนโยบายความเป็นส่วนตัวให้กด **อนุญาต/ปฏิเสธ**)
2. `EmailScanner` ดึงหัวข้อ/ผู้ส่ง/เนื้อหา -> `Email.getDetails()` เป็นเจสัน -> ส่งไป `POST /api/v1/analyze`
3. `PhishingAnalyzer` ตัดคำ/ลบคำหยุด (`NLPProcess`) -> คำนวณความน่าจะเป็นด้วยโมเดลของแต่ละภาษาที่พบในอีเมล
   -> เลือกค่าความเสี่ยงสูงสุด (UC-04 ข้อ 9–11)
4. `DatabaseManager` ตรวจว่าเคยพบอีเมลนี้หรือไม่ ถ้าไม่เคย: บันทึกเนื้อหา (เข้ารหัส), คำที่ตัดแล้ว, ค่า TF-IDF,
   feature vector; ทุกครั้ง: บันทึก detection_result
5. ส่วนขยายแสดงป้าย **ระดับความเสี่ยง AI: xx%** มุมขวาล่าง 3 สี (แดง ≥ 50%, เหลือง ≥ 30%, เขียว) ไฮไลต์คำเสี่ยง
   และกด **ดูรายละเอียด** เพื่อเปิดรายงานการวิเคราะห์ (ประเภทของอีเมล, คำเสี่ยง, คำแนะนำ)

### API

| Method | Path | คำอธิบาย |
|---|---|---|
| GET | `/` | หน้าแรก (แนะนำระบบ) |
| GET | `/scan` `/dashboard` `/login` | เส้นทางของ Angular — เซิร์ฟเวอร์คืน `index.html` ให้แล้วแอปจัดการเส้นทางเอง |
| POST | `/api/v1/analyze` | body: `{subject, sender, body_content, email_id?, time_stamp?}` -> `risk_score, risk_percentage, risk_level, classification, language, highlights, indicators, ...` (503 ถ้าโมเดลยังไม่พร้อม) |
| GET | `/api/v1/health` | สถานะโมเดลแต่ละภาษา + ฐานข้อมูล |
| GET | `/api/v1/model-info` | metadata ของโมเดลที่ใช้งานอยู่ |
| POST | `/api/v1/model/reload` | โหลดโมเดลรุ่นใหม่โดยไม่ต้องรีสตาร์ต (header `X-Admin-Token`) |
| GET | `/api/v1/stats` | สถิติการสแกน (header `X-Admin-Token`) |

## ขั้นตอนการใช้งาน

0. **สร้าง virtual environment** (Python 3.11) — ทำครั้งเดียว
   ```bash
   py -3.11 -m venv .venv                 # Windows: .venv\Scripts\python.exe คือ python ที่ใช้รันทุกคำสั่งด้านล่าง
   .venv\Scripts\python.exe -m pip install -e ".[ml,dev]"
   ```

1. **เตรียมข้อมูลและเทรนโมเดล**
   ```bash
   cd ml
   python preprocess.py --include-mock   # หรือวางชุดข้อมูลจริง (text,label) ใน ml/data/raw/ แล้วไม่ต้องใส่ --include-mock
   python evaluate.py                    # ตารางเปรียบเทียบ 5 อัลกอริทึม -> ml/results/
   python train.py                       # -> backend/ml_model/en/, backend/ml_model/th/
   ```
   > ชุดข้อมูลจำลองใช้ทดสอบ pipeline เท่านั้น ค่าความแม่นยำที่ใช้รายงานต้องมาจากชุดข้อมูลจริง (~18,500 ฉบับ ตามบทที่ 3.3.2)

2. **รัน backend**

   **แบบคอนเทนเนอร์ทั้งระบบ (แนะนำ — ใกล้เคียงการใช้งานจริงที่สุด)**
   ```bash
   cp backend/.env.example backend/.env   # ต้องทำก่อน ตั้ง ENCRYPTION_KEY และ ADMIN_TOKEN
   docker compose up -d --build
   ```
   - ต้องมี `backend/.env` **ก่อน** สั่ง `up` เพราะ service backend อ่านค่าความลับจากไฟล์นั้นผ่าน `env_file`
   - คอนเทนเนอร์ backend รัน `alembic upgrade head` ให้เองก่อนเปิดรับคำขอ ไม่ต้องสั่งเพิ่ม
   - `DATABASE_URL`, `MODEL_DIR`, `LOG_FILE` ถูกทับด้วยค่าใน `docker-compose.yml` เพราะ path
     และชื่อโฮสต์ใน container ต่างจากบนเครื่อง ค่าที่เหลือทั้งหมดมาจาก `backend/.env`
   - ข้อมูลอยู่ใน named volume `phishing_pg_data` จึงไม่หายเมื่อ `docker compose down`
     **หายก็ต่อเมื่อสั่ง `docker compose down -v` เท่านั้น**

   คำสั่งที่ใช้บ่อย

   | คำสั่ง | ผล |
   |---|---|
   | `docker compose ps` | ดูสถานะทั้งสอง container |
   | `docker compose logs -f backend` | ดู log แบบเรียลไทม์ |
   | `docker compose stop` | หยุดชั่วคราว ข้อมูลอยู่ครบ |
   | `docker compose down` | ลบ container แต่ข้อมูลยังอยู่ |
   | `docker compose down -v` | **ลบข้อมูลทั้งหมดด้วย** |

   **แบบ dev (รัน uvicorn บนเครื่อง ใช้ Postgres จากคอนเทนเนอร์)**
   - `docker compose up -d postgres` แล้ว
     ```bash
     cd backend && cp .env.example .env   # ตั้ง ENCRYPTION_KEY และ ADMIN_TOKEN
     # DATABASE_URL ต้องชี้ไป PostgreSQL (ค่าตัวอย่างอยู่ใน .env.example)
     python -m alembic upgrade head       # สร้าง/อัปเดตตารางให้ตรงกับ models.py
     uvicorn app.main:app --reload
     ```
   - **ต้องรัน `alembic upgrade head` ทุกครั้งที่ `models.py` เปลี่ยน** — ตอนเริ่มระบบมี
     `create_all()` ที่สร้างเฉพาะตารางที่ยังไม่มี แต่ไม่เคย ALTER ตารางเดิม
     ถ้าเพิ่มคอลัมน์แล้วไม่ทำ migration ระบบจะพังตอนเขียนข้อมูล
   - ค่าเริ่มต้นตั้งไว้แบบเน้นความเป็นส่วนตัว: **ไม่เก็บเนื้อหาอีเมล ไม่เก็บคำที่ตัดได้
     และลบข้อมูลอัตโนมัติเมื่อครบ 90 วัน** ถ้าต้องเก็บข้อมูลเพื่อทำวิจัยให้ตั้ง
     `STORE_EMAIL_CONTENT=true` และ `STORE_NLP_ARTIFACTS=true` (ดูคำเตือนใน `.env.example`)
   - หน้าแรก: http://127.0.0.1:8000/ · หน้าตรวจสอบอีเมล: http://127.0.0.1:8000/scan · Swagger UI: http://127.0.0.1:8000/docs
   - **บน Windows ให้ใช้ `127.0.0.1` แทน `localhost`** — การต่อผ่านชื่อ localhost จะลอง IPv6 (`::1`) ก่อน
     แล้วค่อยถอยมาใช้ IPv4 ซึ่งวัดได้ว่าเสียเวลาคงที่ประมาณ 2 วินาทีต่อ request (เวลาประมวลผลจริงของระบบ
     อยู่ที่ระดับ 10 มิลลิวินาที) ถ้าวัดผลผ่าน localhost จะสรุปผิดว่าไม่ผ่านเกณฑ์ข้อ 1.4.2

3. **ติดตั้งส่วนขยาย**: `chrome://extensions` -> Developer mode -> Load unpacked -> เลือกโฟลเดอร์ `extension/`
   -> เปิด Gmail แล้วเปิดอีเมล

4. **วัดผลตามบทที่ 3.4**
   ```bash
   python evaluation/benchmark_latency.py --limit 200     # ความแม่นยำ >= 85%, Mean Latency <= 2 วินาที
   python evaluation/survey_analysis.py responses.csv --group-column "สถานะ"
   ```
   ไฟล์ CSV แบบประเมินให้ตั้งชื่อคอลัมน์คำถามเป็น `"<ด้าน>: <ข้อคำถาม>"` เช่น `"ด้านความง่ายต่อการใช้งาน: ใช้งานง่าย"`

5. **Test**: จาก repo root
   `.venv\Scripts\python.exe -m pytest`  (ผลล่าสุด: ผ่าน 27 ข้อ)
   (ใช้ SQLite ชั่วคราว + โมเดลขนาดเล็กที่เทรนตอนรัน test ไม่ต้องมี PostgreSQL หรือไฟล์โมเดลจริง)

## หมายเหตุ

- ตาราง `email` มีคอลัมน์ `body_encrypted` เพิ่มจากพจนานุกรมข้อมูล เพื่อเก็บเนื้อหาแบบเข้ารหัสตามเมธอด
  `encrypt()` ของ DatabaseManager (`body_hash` ใช้ตรวจอีเมลซ้ำ) ปิดการเก็บเนื้อหาได้ด้วย `STORE_EMAIL_CONTENT=false`
- ถ้าไม่ตั้ง `ENCRYPTION_KEY` ระบบจะใช้กุญแจชั่วคราว (ข้อมูลที่เข้ารหัสจะถอดไม่ได้หลังรีสตาร์ต)
- ก่อน publish ส่วนขยายจริง ต้องแก้ `API_ENDPOINT` ใน `extension/config.js` เป็น HTTPS และเพิ่ม origin ใน
  `manifest.json` -> `host_permissions`
- Production ควรใช้ Alembic migration แทน `Base.metadata.create_all()` (ตารางเดิม `email_logs` ของเวอร์ชันก่อนไม่ถูกใช้แล้ว)
- selector ของ Gmail (`extension/email_scanner.js`) อาจต้องปรับเมื่อ Gmail เปลี่ยน UI

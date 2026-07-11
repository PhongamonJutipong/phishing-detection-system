# ระบบตรวจจับอีเมลฟิชชิงโดยใช้ NLP (Chrome Extension)

โครงสร้างโปรเจกต์ ประกอบด้วย 4 ส่วนหลัก (แก้ไขจากเวอร์ชัน scaffold เดิม — ดูหัวข้อ
"สิ่งที่แก้ไขจากโครงสร้างเดิม" ด้านล่างว่าทำไม):

```
phishing-detection-system/
├── common/                  # โค้ดที่ ml/ และ backend/ ใช้ร่วมกัน (single source of truth)
│   ├── resources/
│   │   └── stopwords_th.txt
│   ├── text_cleaning.py     # ฟังก์ชันทำความสะอาดข้อความ (ใช้ทั้งตอนเทรนและตอนใช้งานจริง)
│   └── tests/
│
├── ml/                      # Pipeline เตรียมข้อมูล + เทรนโมเดล (TF-IDF + Naive Bayes)
│   ├── data/
│   │   ├── raw/             # วางไฟล์ dataset ดิบที่นี่ (.csv คอลัมน์ text,label)
│   │   └── processed/       # ข้อมูลหลังทำความสะอาด + แบ่ง train/test
│   ├── preprocess.py        # ทำความสะอาดข้อความ + แบ่งข้อมูล (import จาก common/)
│   ├── train.py             # เทรน TF-IDF + Naive Bayes, บันทึกโมเดล + model_metadata.json
│   ├── evaluate.py          # เปรียบเทียบ 5 อัลกอริทึม (SVM, RF, LR, NB, KNN)
│   ├── tests/
│   └── requirements.txt
│
├── backend/                 # FastAPI + PostgreSQL
│   ├── Dockerfile           # build context = repo root (ต้อง COPY common/ เข้า image ด้วย)
│   ├── .dockerignore
│   ├── app/
│   │   ├── main.py          # entry point, CORS (รองรับ wildcard origin ถูกต้อง), routers
│   │   ├── config.py        # การตั้งค่า (.env)
│   │   ├── schemas.py       # Pydantic request/response models
│   │   ├── db/
│   │   ├── ml/
│   │   │   ├── preprocessing.py  # shim -> re-export จาก common/text_cleaning.py
│   │   │   └── model_service.py  # โหลดโมเดล + ทำนาย + หาคำเสี่ยง + อ่าน metadata
│   │   └── api/
│   │       └── routes.py    # POST /api/v1/analyze, GET /api/v1/health, GET /api/v1/model-info
│   ├── ml_model/             # ใส่ .pkl + model_metadata.json จาก ml/train.py ที่นี่
│   ├── tests/                # pytest smoke tests (ไม่ต้องมี Postgres/โมเดลจริงก็รันได้)
│   ├── requirements.txt
│   └── .env.example
│
├── extension/                # Chrome Extension (Manifest V3)
│   ├── manifest.json
│   ├── config.js             # DEFAULT_API_URL — จุดเดียวที่ต้องแก้ก่อน publish จริง
│   ├── background.js         # service worker, เรียก backend API
│   ├── content.js            # ดึงเนื้อหาอีเมลจาก Gmail + ไฮไลต์คำเสี่ยง
│   ├── popup.html/js/css     # หน้าต่างแสดงผล % ความเสี่ยง
│   └── icons/
│
├── requirements-dev.txt      # pytest, httpx (สำหรับรัน test เท่านั้น)
├── pytest.ini
└── docker-compose.yml        # postgres + backend (รันทั้งระบบจริงได้ ไม่ใช่แค่ dev DB)
```

## ลำดับการเริ่มงานที่แนะนำ

1. **ml/**: วาง dataset (คอลัมน์ `text,label`) ใน `ml/data/raw/`, รัน `python preprocess.py`
   แล้ว `python train.py` (รันจากในโฟลเดอร์ `ml/`) จะได้ไฟล์โมเดล `.pkl` +
   `model_metadata.json` ไปวางที่ `backend/ml_model/` ให้อัตโนมัติ
2. **backend/** (dev แบบไม่ผ่าน Docker):
   `pip install -r backend/requirements.txt`, ตั้งค่า `.env` จาก `.env.example`,
   รัน `docker-compose up -d postgres` เพื่อเปิดแค่ฐานข้อมูล แล้ว
   `cd backend && uvicorn app.main:app --reload`
3. **backend/** (รันทั้งระบบแบบ production-like ด้วย Docker):
   จาก repo root รัน `docker-compose up -d --build` — จะ build image ของ backend
   (ตาม `backend/Dockerfile`) และรัน Postgres คู่กันให้ครบ ไม่ต้องติดตั้ง Python เอง
4. ทดสอบ API ด้วย `curl` หรือ Swagger UI ที่ `http://localhost:8000/docs`,
   เช็คว่าโมเดลที่รันอยู่คือรุ่นไหนที่ `GET /api/v1/model-info`
5. **extension/**: เปิด `chrome://extensions` → Developer mode → Load unpacked →
   เลือกโฟลเดอร์ `extension/` → เปิด Gmail แล้วทดสอบ
6. **tests**: จาก repo root รัน
   `pip install -r backend/requirements.txt -r requirements-dev.txt && pytest`

## สิ่งที่แก้ไขจากโครงสร้างเดิม (และเหตุผล)

- **ย้ายฟังก์ชันทำความสะอาดข้อความมารวมที่ `common/text_cleaning.py`** — เดิมโค้ด
  ชุดเดียวกันถูก copy ไว้ 2 ที่ (`ml/preprocess.py` และ `backend/app/ml/preprocessing.py`)
  ซึ่ง README เดิมก็เตือนเองว่า "ต้องเหมือนกันทุกตัวอักษร" มิเช่นนั้นโมเดลจะทำนายผิดเพี้ยน
  แบบเงียบ ๆ — ตอนนี้มีจุดเดียว แก้ที่เดียวจบทั้งสองฝั่ง
- **แก้ path ของ `stopwords_th.txt` ที่เคยอ้างออกนอกโฟลเดอร์ `backend/`** — เดิม
  `backend/app/ml/preprocessing.py` อ้างไฟล์ผ่าน `../../../../ml/stopwords_th.txt`
  ซึ่งถ้า deploy backend เป็น container เดี่ยว ๆ (ไม่มีโฟลเดอร์ `ml/` ติดไปด้วย) แอปจะ
  หาไฟล์นี้ไม่เจอตอน runtime — ย้ายมาไว้ใน `common/resources/` แล้วให้ Dockerfile
  COPY `common/` เข้า image ไปด้วยเสมอ
- **เพิ่ม `backend/Dockerfile` และแก้ `docker-compose.yml`** — เดิม docker-compose มีแค่
  Postgres ไม่มีทางรัน backend เป็น container ได้จริงเลย ("deploy" ทำไม่ได้จริง)
- **แก้ CORS bug** — `allow_origins=["chrome-extension://*"]` ที่ผ่านมาไม่ทำงานจริง
  (Starlette CORSMiddleware ไม่รองรับ wildcard กลางสตริงใน `allow_origins`) ตอนนี้
  ใช้ `allow_origin_regex` แทนสำหรับ origin ที่มี `*`
- **รวม `DEFAULT_API_URL` ของ extension เป็นไฟล์เดียว (`extension/config.js`)** —
  เดิม hardcode แยกกันใน `background.js` กับ `popup.js`
- **เพิ่ม `model_metadata.json`** — ตอนนี้ `train.py` บันทึกเวลาที่เทรน, metric,
  จำนวนข้อมูล ไว้ข้าง ๆ ไฟล์ `.pkl` เสมอ ดูได้ผ่าน `GET /api/v1/model-info` —
  ช่วยตรวจสอบได้ว่าโมเดลที่ deploy อยู่จริงคือรุ่นไหน
- **เพิ่ม test scaffold** (`common/tests/`, `backend/tests/`, `ml/tests/`) — เดิมไม่มี
  test เลยทั้งโปรเจกต์ ตอนนี้มี pytest smoke test ที่รันได้โดยไม่ต้องพึ่ง Postgres หรือ
  ไฟล์โมเดลจริง (ใช้ SQLite ชั่วคราว + fake model ผ่าน dependency override)

## หมายเหตุสำคัญ

- ชุดข้อมูลภาษาไทยที่จะสร้างเองควรมีคอลัมน์ `text,label` เหมือนกับ dataset ภาษาอังกฤษ เพื่อรวมกันได้ก่อนเทรน
- ก่อน publish extension ขึ้น Chrome Web Store จริง ต้องแก้ `extension/config.js` ให้ชี้ไป HTTPS
  endpoint ของ production backend และเพิ่ม origin นั้นใน `manifest.json` -> `host_permissions`
- Production จริงควรใช้ Alembic migration แทน `Base.metadata.create_all()` ที่ auto-create ตารางตอน
  startup (ยังไม่ได้ทำในเวอร์ชันนี้ — เหมาะสำหรับ dev/scaffold เท่านั้น)
- โค้ดชุดนี้ยังต้องปรับปรุงเพิ่มเติมในหลายจุด (การ tokenize ภาษาไทยที่แม่นยำขึ้น, การดึง DOM
  ของ Gmail ให้ครอบคลุมทุก layout, การจัดการ error, HTTPS สำหรับ production เป็นต้น)

"""
common — โค้ดที่ ml/ และ backend/ ใช้ร่วมกัน (single source of truth)

เหตุผลที่แยกมาไว้ตรงนี้: ก่อนหน้านี้ฟังก์ชันทำความสะอาดข้อความถูก copy ไว้ 2 ที่
(ml/preprocess.py และ backend/app/ml/preprocessing.py) ซึ่งเสี่ยงมากที่โค้ดจะ
"เพี้ยน" ไปคนละทางเมื่อมีคนแก้ที่เดียวแล้วลืมอีกที่ — ทำให้โมเดลตอนเทรนกับตอนใช้งาน
จริงประมวลผลข้อความไม่เหมือนกัน (ผลลัพธ์การทำนายจะผิดเพี้ยนแบบเงียบ ๆ ไม่มี error ให้เห็น)

Backend Dockerfile จะ COPY โฟลเดอร์นี้เข้าไปใน image ด้วย จึงไม่ต้องพึ่ง path ที่ชี้
ออกไปนอกโฟลเดอร์ backend/ ตอน deploy จริง (ก่อนหน้านี้ backend/app/ml/preprocessing.py
เคยอ้าง "../../../../ml/stopwords_th.txt" ซึ่งถ้า deploy backend แยกเป็น container
เดี่ยว ๆ ไฟล์นั้นจะไม่มีอยู่และแอปจะพังตอน runtime)
"""

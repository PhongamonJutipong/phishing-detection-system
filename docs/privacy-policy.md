# นโยบายความเป็นส่วนตัว — PhishMail

**ปรับปรุงล่าสุด:** 22 กันยายน 2569

PhishMail เป็นส่วนขยาย Chrome ที่ตรวจจับอีเมลฟิชชิงขณะผู้ใช้เปิดอ่านอีเมลใน Gmail
เอกสารนี้อธิบายว่าส่วนขยายอ่านข้อมูลอะไร ส่งไปที่ใด และเก็บอะไรไว้บ้าง

---

## 1. การขอความยินยอมก่อนเริ่มทำงาน

ส่วนขยาย **ไม่อ่านเนื้อหาอีเมลใด ๆ จนกว่าผู้ใช้จะกด "อนุญาต"** ในหน้าจอข้อตกลงที่แสดงขึ้นครั้งแรก

- หากกด **ปฏิเสธ** ส่วนขยายจะไม่อ่านและไม่ส่งข้อมูลใด ๆ ทั้งสิ้น
- ผู้ใช้ยกเลิกความยินยอมได้ตลอดเวลาจากปุ่ม **รีเซ็ตความยินยอม** ในหน้าต่างตั้งค่าของส่วนขยาย
- ผู้ใช้ปิดการสแกนชั่วคราวได้จากสวิตช์ในหน้าต่างตั้งค่า

## 2. ข้อมูลที่ส่วนขยายอ่าน

เมื่อได้รับความยินยอมแล้ว ส่วนขยายจะอ่านข้อมูลของ**อีเมลฉบับที่เปิดอยู่เท่านั้น** ได้แก่

| ข้อมูล | ใช้ทำอะไร |
|---|---|
| หัวข้ออีเมล | วิเคราะห์ข้อความหาสัญญาณฟิชชิง |
| ที่อยู่ผู้ส่ง | ประกอบการวิเคราะห์ |
| เนื้อหาอีเมล | วิเคราะห์ข้อความหาสัญญาณฟิชชิง |

ส่วนขยาย **ไม่อ่าน** รายการอีเมลทั้งกล่อง ไม่อ่านไฟล์แนบ ไม่อ่านรายชื่อผู้ติดต่อ
ไม่อ่านอีเมลฉบับอื่นที่ไม่ได้เปิด และไม่เข้าถึงบัญชี Google ของผู้ใช้

## 3. ข้อมูลถูกส่งไปที่ใด

ข้อมูลถูกส่งไปยัง **ปลายทาง API ที่ผู้ใช้กำหนดเองในหน้าต่างตั้งค่า** เท่านั้น

ค่าเริ่มต้นคือ `http://127.0.0.1:8000/api/v1/analyze` ซึ่งหมายถึง
**เซิร์ฟเวอร์ที่ทำงานอยู่บนเครื่องของผู้ใช้เอง** ในการตั้งค่าเริ่มต้นนี้
ข้อมูลจึงไม่ออกจากเครื่องของผู้ใช้เลย

หากผู้ใช้หรือผู้ดูแลระบบเปลี่ยนค่าไปเป็นเซิร์ฟเวอร์อื่น ข้อมูลจะถูกส่งไปยังเซิร์ฟเวอร์นั้น
ผู้ดูแลเซิร์ฟเวอร์ปลายทางเป็นผู้รับผิดชอบข้อมูลดังกล่าว

ส่วนขยาย **ไม่ส่งข้อมูลไปยังบุคคลที่สามใด ๆ** ไม่มีบริการวิเคราะห์พฤติกรรม
ไม่มีโฆษณา และไม่มีการติดตามผู้ใช้

## 4. ข้อมูลที่เซิร์ฟเวอร์จัดเก็บ

| ข้อมูล | รายละเอียด |
|---|---|
| ค่าแฮชของเนื้อหา | SHA-256 ของหัวข้อและเนื้อหารวมกัน ใช้ตรวจว่าเคยวิเคราะห์อีเมลนี้แล้วหรือไม่ |
| เนื้อหาอีเมลที่เข้ารหัส | หัวข้อและเนื้อหา **เข้ารหัสด้วย Fernet (AES-128-CBC + HMAC)** ก่อนบันทึกเสมอ |
| เวลาที่รับข้อมูล | วันเวลาที่ระบบได้รับคำขอ |
| คำที่ตัดได้ ค่า TF-IDF และเวกเตอร์คุณลักษณะ | ใช้ปรับปรุงความแม่นยำของโมเดล |
| ผลการตรวจ | ค่าความน่าจะเป็น ผลการจำแนกประเภท และเวลาที่ตรวจ |

**ข้อมูลที่ระบบไม่จัดเก็บ:** ที่อยู่ผู้ส่ง ที่อยู่ผู้รับ ไฟล์แนบ
ชื่อบัญชีหรืออีเมลของผู้ใช้ และที่อยู่ IP

ที่อยู่ผู้ส่งถูกส่งมาเพื่อใช้วิเคราะห์เท่านั้น **ไม่มีคอลัมน์สำหรับเก็บที่อยู่ผู้ส่งในฐานข้อมูล**

ผู้ดูแลระบบสามารถปิดการเก็บเนื้อหาอีเมลทั้งหมดได้โดยตั้งค่า `STORE_EMAIL_CONTENT=false`
ซึ่งจะทำให้ระบบบันทึกเฉพาะผลการตรวจโดยไม่เก็บเนื้อหาใด ๆ

## 5. ข้อมูลที่เก็บไว้ในเครื่องผู้ใช้

ส่วนขยายเก็บค่าต่อไปนี้ไว้ใน `chrome.storage.local` บนเครื่องผู้ใช้
**ข้อมูลเหล่านี้ไม่เคยถูกส่งออกไปที่ใด**

- ที่อยู่ API ที่ตั้งไว้
- เกณฑ์ระดับความเสี่ยง
- สถานะเปิด/ปิดการสแกน
- ภาษาที่เลือก (ไทย/อังกฤษ)
- สถานะความยินยอม

## 6. วัตถุประสงค์การใช้ข้อมูล

ข้อมูลที่จัดเก็บถูกใช้เพื่อ **2 วัตถุประสงค์เท่านั้น**

1. ให้บริการตรวจจับอีเมลฟิชชิงแก่ผู้ใช้
2. ปรับปรุงความแม่นยำของแบบจำลองตรวจจับ

ข้อมูลจะ **ไม่ถูกขาย ไม่ถูกให้เช่า ไม่ถูกใช้เพื่อการโฆษณา**
และไม่ถูกใช้เพื่อวัตถุประสงค์อื่นนอกเหนือจากที่ระบุไว้ข้างต้น

## 7. การเก็บรักษาและการลบข้อมูล

ข้อมูลถูกเก็บในฐานข้อมูลที่ผู้ดูแลระบบควบคุม ผู้ใช้สามารถ

- หยุดการเก็บข้อมูลเพิ่มเติมได้ทันทีโดยกดรีเซ็ตความยินยอมหรือปิดการสแกน
- ขอให้ลบข้อมูลที่เกี่ยวข้องได้โดยติดต่อผู้ดูแลระบบตามช่องทางในข้อ 9

ในการติดตั้งเพื่อการศึกษาซึ่งเซิร์ฟเวอร์ทำงานบนเครื่องผู้ใช้เอง
ผู้ใช้ลบข้อมูลทั้งหมดได้ด้วยการลบฐานข้อมูลบนเครื่องของตน

## 8. ความปลอดภัย

- เนื้อหาอีเมลถูกเข้ารหัสด้วย Fernet ก่อนบันทึกลงฐานข้อมูลเสมอ
- กุญแจเข้ารหัสถูกเก็บแยกจากฐานข้อมูลในไฟล์ตั้งค่าของเซิร์ฟเวอร์
- ปลายทางสำหรับการใช้งานจริงควรเป็น HTTPS เท่านั้น

## 9. การติดต่อ

หากมีคำถามเกี่ยวกับนโยบายนี้ หรือต้องการขอให้ลบข้อมูล
กรุณาติดต่อผ่าน GitHub repository ของโครงงาน

<https://github.com/PhongamonJutipong/phishing-detection-system>

---
---

# Privacy Policy — PhishMail

**Last updated:** 22 September 2026

PhishMail is a Chrome extension that detects phishing emails while the user reads
mail in Gmail. This document explains what the extension reads, where it sends
that data, and what is retained.

## 1. Consent is required first

The extension **does not read any email content until the user clicks "Allow"**
on the consent screen shown on first use.

If the user declines, nothing is read and nothing is transmitted. Consent can be
withdrawn at any time via **Reset consent** in the extension popup, and scanning
can be switched off entirely from the same popup.

## 2. What the extension reads

Once consent is given, the extension reads **only the currently open email**:
its subject, sender address, and body text.

It does **not** read the mailbox listing, attachments, contacts, other messages,
or the user's Google account.

## 3. Where data is sent

Data is sent **only to the API endpoint configured by the user** in the popup.

The default is `http://127.0.0.1:8000/api/v1/analyze` — a server running on the
user's **own machine**. Under this default configuration, data never leaves the
user's computer.

If the endpoint is changed to a remote server, data is sent there instead, and
the operator of that server is responsible for it.

The extension sends data to **no third parties**. There is no analytics,
no advertising, and no user tracking.

## 4. What the server stores

| Data | Detail |
|---|---|
| Content hash | SHA-256 of subject + body, used for duplicate detection |
| Encrypted content | Subject and body, **always encrypted with Fernet (AES-128-CBC + HMAC)** before storage |
| Receive timestamp | When the request was received |
| Tokens, TF-IDF values, feature vectors | Used to improve model accuracy |
| Detection result | Probability, classification, scan time |

**Not stored:** sender address, recipient address, attachments, the user's
account name or email address, and IP addresses.

The sender address is transmitted for analysis only — **the database schema has
no column for it**.

Operators may disable content storage entirely by setting
`STORE_EMAIL_CONTENT=false`, in which case only detection results are recorded.

## 5. Data stored locally

The extension stores the following in `chrome.storage.local` on the user's
device. **None of it is ever transmitted:** configured API endpoint, risk
thresholds, scan on/off state, selected language, and consent status.

## 6. Limited use of data

Collected data is used **solely** to (1) provide the phishing detection feature
to the user, and (2) improve the accuracy of the detection model.

Data is **never sold, rented, or used for advertising**, and is not used for any
purpose beyond those stated above.

## 7. Retention and deletion

Users can stop further collection immediately by resetting consent or disabling
scanning, and may request deletion of related data via the contact below.

In the educational deployment, where the server runs on the user's own machine,
deleting the local database removes all stored data.

## 8. Security

Email content is always encrypted with Fernet before being written to the
database. The encryption key is stored separately from the database in the
server's configuration file. Production endpoints should use HTTPS only.

## 9. Contact

For questions about this policy or deletion requests, please open an issue at

<https://github.com/PhongamonJutipong/phishing-detection-system>

# นโยบายความเป็นส่วนตัว — PhishMail

**ปรับปรุงล่าสุด:** 24 กันยายน 2569 (ฉบับ `2026-09-24`)

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
| ค่าแฮชของเนื้อหา | **HMAC-SHA256** ที่มีกุญแจลับของเซิร์ฟเวอร์ ใช้ตรวจว่าเคยวิเคราะห์อีเมลนี้แล้วหรือไม่ ผู้อื่นที่มีสำเนาอีเมลอยู่แล้วไม่สามารถคำนวณค่านี้มาเทียบได้ |
| เวลาที่รับข้อมูล | วันเวลาที่ระบบได้รับคำขอ |
| กำหนดวันลบ | วันที่ข้อมูลชุดนี้จะถูกลบอัตโนมัติ |
| ผลการตรวจ | ค่าความน่าจะเป็น ผลการจำแนกประเภท และเวลาที่ตรวจ |

**โดยค่าเริ่มต้น ระบบไม่เก็บเนื้อหาอีเมล และไม่เก็บคำที่ตัดได้**
ผู้ดูแลระบบเปิดการเก็บเพิ่มได้ 2 ระดับ ซึ่งต้องแจ้งผู้ใช้ก่อนเสมอ

| ตัวเลือก | ผลเมื่อเปิด |
|---|---|
| `STORE_EMAIL_CONTENT=true` | เก็บหัวข้อและเนื้อหาโดย**เข้ารหัสด้วย Fernet (AES-128-CBC + HMAC)** ก่อนบันทึก |
| `STORE_NLP_ARTIFACTS=true` | เก็บคำที่ตัดได้ ค่า TF-IDF และเวกเตอร์คุณลักษณะรายอีเมล เพื่อใช้ปรับปรุงโมเดล **คำเหล่านี้เก็บเป็นข้อความธรรมดา** ผู้ที่อ่านฐานข้อมูลได้จึงประกอบเนื้อหาอีเมลกลับได้ เปิดเฉพาะเมื่อทำวิจัยและได้รับความยินยอมแล้วเท่านั้น |

**ข้อมูลที่ระบบไม่จัดเก็บจากการตรวจอีเมล:** ที่อยู่ผู้ส่ง ที่อยู่ผู้รับ ไฟล์แนบ
ชื่อบัญชีหรืออีเมลของผู้ใช้ และที่อยู่ IP ผลการตรวจไม่ผูกกับบัญชีผู้ใช้ แม้ผู้ใช้จะเข้าสู่ระบบอยู่ก็ตาม

ที่อยู่ผู้ส่งถูกส่งมาเพื่อใช้วิเคราะห์เท่านั้น **ไม่มีคอลัมน์สำหรับเก็บที่อยู่ผู้ส่งในฐานข้อมูล**

ค่าเริ่มต้นคือบันทึกเฉพาะผลการตรวจโดยไม่เก็บเนื้อหาใด ๆ

### 4.1 บัญชีผู้ใช้บนหน้าเว็บ (ไม่บังคับ)

การตรวจอีเมลใช้ได้โดยไม่ต้องสมัครสมาชิก ผู้ที่เลือกสมัครต้องกดยอมรับนโยบายนี้ก่อน
ระบบบันทึกฉบับของนโยบายที่ยอมรับและเวลาที่ยอมรับไว้เป็นหลักฐาน

| ข้อมูล | วิธีจัดเก็บ |
|---|---|
| อีเมล | **เข้ารหัสด้วย Fernet** ก่อนบันทึก และเก็บ **HMAC-SHA256** ไว้ค้นหาตอนเข้าสู่ระบบ ฐานข้อมูลไม่มีอีเมลเป็นข้อความธรรมดา |
| รหัสผ่าน | เก็บเฉพาะค่าแฮช **scrypt** ที่มี salt สุ่มต่อบัญชี ไม่มีผู้ใดดูรหัสผ่านจริงได้ |
| ความยินยอม | ฉบับของนโยบายและเวลาที่ยอมรับ |
| วันที่สมัคร | วันเวลาที่สร้างบัญชี |
| การเข้าสู่ระบบ | เก็บเฉพาะค่าแฮช SHA-256 ของ token และวันหมดอายุ (12 ชั่วโมง หรือ 30 วันเมื่อเลือกจดจำ) ถูกลบเมื่อออกจากระบบหรือหมดอายุ |

ระบบ**ไม่ขอ**ชื่อ เบอร์โทรศัพท์ หรือข้อมูลอื่นนอกเหนือจากนี้

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

ระบบกำหนดวันลบให้ข้อมูลทุกชุดตั้งแต่ตอนบันทึก ตามค่า `DATA_RETENTION_DAYS`
(ค่าเริ่มต้น **90 วัน**) และลบข้อมูลที่เลยกำหนดออกโดยอัตโนมัติ

ข้อมูลถูกเก็บในฐานข้อมูลที่ผู้ดูแลระบบควบคุม ผู้ใช้สามารถ

- หยุดการเก็บข้อมูลเพิ่มเติมได้ทันทีโดยกดรีเซ็ตความยินยอมหรือปิดการสแกน
- ดูข้อมูลทั้งหมดที่ระบบเก็บเกี่ยวกับบัญชีได้ที่หน้า "บัญชีของฉัน" (`/account`)
- ลบบัญชีได้เองที่หน้าเดียวกัน ข้อมูลบัญชีและการเข้าสู่ระบบทั้งหมดถูกลบทันที ไม่มีการเก็บสำเนา
  การลบบัญชีถือเป็นการถอนความยินยอม
- ขอให้ลบข้อมูลที่เกี่ยวข้องได้โดยติดต่อผู้ดูแลระบบตามช่องทางในข้อ 9

ในการติดตั้งเพื่อการศึกษาซึ่งเซิร์ฟเวอร์ทำงานบนเครื่องผู้ใช้เอง
ผู้ใช้ลบข้อมูลทั้งหมดได้ด้วยการลบฐานข้อมูลบนเครื่องของตน

## 8. ความปลอดภัย

- ค่าเริ่มต้นไม่เก็บเนื้อหาอีเมล และเมื่อเปิดให้เก็บ เนื้อหาจะถูกเข้ารหัสด้วย Fernet ก่อนบันทึกเสมอ
- จำกัดจำนวนคำขอต่อผู้เรียกเพื่อกันการยิงถล่ม และเก็บตัวระบุผู้เรียกเป็นค่าแฮช ไม่ใช่ IP ดิบ
- กุญแจเข้ารหัสถูกเก็บแยกจากฐานข้อมูลในไฟล์ตั้งค่าของเซิร์ฟเวอร์
- ปลายทางสำหรับการใช้งานจริงควรเป็น HTTPS เท่านั้น

## 9. การติดต่อ

หากมีคำถามเกี่ยวกับนโยบายนี้ หรือต้องการขอให้ลบข้อมูล
กรุณาติดต่อผ่าน GitHub repository ของโครงงาน

<https://github.com/PhongamonJutipong/phishing-detection-system>

---
---

# Privacy Policy — PhishMail

**Last updated:** 24 September 2026 (version `2026-09-24`)

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
| Content hash | **HMAC-SHA256** keyed with a server secret, used for duplicate detection. Someone holding a copy of the email cannot compute this value to check whether it passed through the system |
| Receive timestamp | When the request was received |
| Deletion deadline | When this record will be deleted automatically |
| Detection result | Probability, classification, scan time |

**By default the system stores neither email content nor tokenized words.**
Operators can enable two additional levels of storage, and must inform users before doing so.

| Option | Effect when enabled |
|---|---|
| `STORE_EMAIL_CONTENT=true` | Stores subject and body, **encrypted with Fernet (AES-128-CBC + HMAC)** before writing |
| `STORE_NLP_ARTIFACTS=true` | Stores per-email tokens, TF-IDF values and feature vectors for model improvement. **These words are stored in plaintext**, so anyone with database read access can reconstruct the substance of the email. Enable only for research, with consent |

**Not stored from scans:** sender address, recipient address, attachments, the user's
account name or email address, and IP addresses. Scan results are never linked to a
user account, even while the user is logged in.

The sender address is transmitted for analysis only — **the database schema has
no column for it**.

The default configuration records only detection results and no content.

### 4.1 Optional web accounts

Emails can be checked without an account. Anyone who signs up must first accept
this policy; the accepted version and time are recorded as proof of consent.

| Data | How it is stored |
|---|---|
| Email | **Encrypted with Fernet** before writing, plus an **HMAC-SHA256** used for lookup at login. The database never holds the email in plain text |
| Password | Only a **scrypt** hash with a random per-account salt. Nobody can read the actual password |
| Consent | Policy version and time of acceptance |
| Sign-up date | When the account was created |
| Logins | Only a SHA-256 hash of the token and its expiry (12 hours, or 30 days with "keep me logged in"). Removed on logout or expiry |

The system does **not** ask for a name, phone number, or anything else.

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

Every record is given a deletion deadline when it is written, based on
`DATA_RETENTION_DAYS` (default **90 days**), and expired records are deleted
automatically.

Users can stop further collection immediately by resetting consent or disabling
scanning, and may request deletion of related data via the contact below.
Account holders can see everything stored about their account on the "My account"
page (`/account`) and delete the account there themselves. Account data and all
logins are removed immediately with no copies kept; deleting the account withdraws consent.

In the educational deployment, where the server runs on the user's own machine,
deleting the local database removes all stored data.

## 8. Security

By default no email content is stored at all; when storage is enabled, content is
always encrypted with Fernet before being written. Requests are rate limited per
caller, and the caller identifier is hashed rather than stored as a raw IP address. The encryption key is stored separately from the database in the
server's configuration file. Production endpoints should use HTTPS only.

## 9. Contact

For questions about this policy or deletion requests, please open an issue at

<https://github.com/PhongamonJutipong/phishing-detection-system>

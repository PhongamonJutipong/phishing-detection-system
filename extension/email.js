/**
 * Class Email (แผนภาพคลาส รูปที่ 3.2)
 */
class Email {
  constructor({ emailId = null, subject = "", sender = null, bodyContent = "", timeStamp = new Date() } = {}) {
    this.emailId = emailId;
    this.subject = subject;
    this.sender = sender;
    this.bodyContent = bodyContent;
    this.timeStamp = timeStamp;
  }

  /** getDetails(): แปลงข้อมูลให้อยู่ในรูปแบบ JSON ตามโครงสร้างที่ API กำหนด */
  getDetails() {
    return {
      email_id: this.emailId,
      subject: this.subject,
      sender: this.sender,
      body_content: this.bodyContent,
      time_stamp: this.timeStamp.toISOString(),
    };
  }

  /** คีย์สำหรับตรวจว่าเป็นอีเมลฉบับเดิมหรือไม่ (ไม่วิเคราะห์ซ้ำ) */
  contentKey() {
    const raw = `${this.emailId || ""}|${this.subject}|${this.bodyContent}`;
    let hash = 0;
    for (let i = 0; i < raw.length; i++) {
      hash = (hash << 5) - hash + raw.charCodeAt(i);
      hash |= 0;
    }
    return `${raw.length}:${hash}`;
  }
}

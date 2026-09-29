/**
 * Class EmailScanner (แผนภาพคลาส รูปที่ 3.2, UC-03 Scan Email Content)
 *
 * ตรรกะการเฝ้าดู DOM เหมือนกันทุกผู้ให้บริการ ส่วนที่ต่างกัน (selector, การอ่านรหัสข้อความ)
 * อยู่ในตารางผู้ให้บริการที่ providers.js — เพิ่มเจ้าใหม่ให้แก้ที่ไฟล์นั้น ไม่ใช่ไฟล์นี้
 *
 * หมายเหตุ: หน้าอีเมลเป็น SPA ที่เปลี่ยน DOM บ่อยและ class name เปลี่ยนไปตามเวอร์ชัน
 * ควรตรวจสอบ selector ในตารางเป็นระยะเมื่อผู้ให้บริการอัปเดต UI
 */
class EmailScanner {
  constructor(ui, provider) {
    this.ui = ui;
    // ไม่รู้จักโฮสต์นี้ = null แล้ว scanDOM() จะไม่เริ่มเฝ้าดูเลย
    this.provider = provider !== undefined ? provider : Providers.forHost();
    this.observer = null;
    this.lastKey = null;
    this.debounceTimer = null;
    this.currentBodyEl = null;
    this.requestSeq = 0;
  }

  /** scanDOM(): ตรวจจับการเปลี่ยนแปลงของโครงสร้างในหน้าอีเมล เพื่อหาตำแหน่งของเนื้อหาอีเมล */
  scanDOM() {
    if (this.observer) return;
    if (!this.provider) {
      Logger.logInfo("ไม่รองรับผู้ให้บริการอีเมลของหน้านี้");
      return;
    }
    this.observer = new MutationObserver((mutations) => {
      // ไม่สนใจการเปลี่ยนแปลงที่ส่วนขยายสร้างเอง (ป้าย/ไฮไลต์/หน้าต่าง)
      const external = mutations.some((m) => !(m.target.closest && m.target.closest(".pd-badge, .pd-overlay, mark.pd-highlight")));
      if (!external) return;
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => this.check(), 500);
    });
    this.observer.observe(document.body, { childList: true, subtree: true });
    this.check();
  }

  stop() {
    if (this.observer) this.observer.disconnect();
    this.observer = null;
    clearTimeout(this.debounceTimer);
  }

  async check() {
    const email = this.fetchEmailBody();
    if (!email) {
      if (this.lastKey !== null) {
        this.lastKey = null;
        this.ui.clear();
      }
      return;
    }
    const key = email.contentKey();
    if (key === this.lastKey) return; // อีเมลเดิม ไม่ต้องวิเคราะห์ซ้ำ
    this.lastKey = key;
    await this.sendToBackend(email);
  }

  /** fetchEmailBody(): นำข้อความดิบออกจาก DOM และสร้าง Object Email */
  fetchEmailBody() {
    const provider = this.provider;
    if (!provider) return null;
    const selectors = provider.selectors;

    const bodies = queryAll(document, selectors.body).filter(
      (node) => node.offsetParent !== null && node.innerText.trim()
    );
    if (!bodies.length) return null;

    // เปิด thread ที่มีหลายข้อความ: วิเคราะห์ข้อความล่าสุดที่กางอยู่
    const bodyEl = bodies[bodies.length - 1];
    const messageEl = closestAny(bodyEl, selectors.message) || document;
    const subjectEl = queryFirst(document, selectors.subject);
    const senderEl = queryFirst(messageEl, selectors.sender) || queryFirst(document, selectors.sender);

    this.currentBodyEl = bodyEl;
    return new Email({
      emailId: provider.emailId(bodyEl),
      subject: subjectEl ? subjectEl.innerText.trim() : "",
      sender: senderEl ? provider.senderAddress(senderEl) : null,
      bodyContent: bodyEl.innerText.trim(),
      timeStamp: new Date(),
    });
  }

  /** sendToBackend(email): ส่งข้อมูลเจสันไปยังหลังบ้าน (ผ่าน service worker) */
  async sendToBackend(email) {
    const seq = ++this.requestSeq;
    const bodyEl = this.currentBodyEl;
    this.ui.onRetry = () => {
      this.lastKey = null;
      this.check();
    };
    this.ui.showLoading();

    let response;
    try {
      response = await chrome.runtime.sendMessage({ type: "ANALYZE_EMAIL", payload: email.getDetails() });
    } catch (err) {
      Logger.logError("ส่งข้อมูลไปยัง service worker ไม่สำเร็จ", err);
      response = { ok: false, code: "NETWORK_ERROR" };
    }
    if (seq !== this.requestSeq) return; // ผู้ใช้เปิดอีเมลฉบับอื่นไปแล้ว

    if (response && response.ok) {
      await this.ui.showResult(response.data, bodyEl);
    } else {
      Logger.logError("วิเคราะห์อีเมลไม่สำเร็จ", response);
      // คง lastKey ไว้ เพื่อไม่ให้ยิง request ซ้ำทุกครั้งที่หน้าเว็บเปลี่ยน DOM — ลองใหม่เมื่อผู้ใช้กด "ลองใหม่"
      this.ui.showError(response ? response.code : "SERVER_ERROR");
    }
  }
}

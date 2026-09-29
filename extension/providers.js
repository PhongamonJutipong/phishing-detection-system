/**
 * ตารางผู้ให้บริการอีเมลที่ส่วนขยายรองรับ
 *
 * แยกออกมาจาก EmailScanner เพราะตรรกะการเฝ้าดู DOM เหมือนกันทุกเจ้า
 * ต่างกันแค่ selector กับวิธีอ่านรหัสข้อความ การเพิ่มเจ้าใหม่จึงแก้ที่ไฟล์นี้ไฟล์เดียว
 * (ยกเว้น host_permissions กับ content_scripts.matches ใน manifest.json ที่ต้องเติมด้วย)
 *
 * selector ของทุกเจ้าเป็นคลาสที่ผ่าน minify มา เปลี่ยนได้ทุกเมื่อที่เขาอัปเดตหน้าเว็บ
 * แต่ละช่องจึงรับเป็น "รายการ" ได้ ระบบจะไล่ใช้ตัวแรกที่เจอ เวลาเขาเปลี่ยน UI
 * จะได้ยังมีตัวสำรองให้ลอง ไม่ดับทันทีทั้งเจ้า
 */

/** element แรกที่ตรงกับ selector ตัวใดตัวหนึ่ง (รับทั้งสตริงเดี่ยวและอาร์เรย์) */
function queryFirst(root, selector) {
  for (const sel of Array.isArray(selector) ? selector : [selector]) {
    const found = root.querySelector(sel);
    if (found) return found;
  }
  return null;
}

/** element ทั้งหมดของ selector ตัวแรกที่ให้ผลลัพธ์ */
function queryAll(root, selector) {
  for (const sel of Array.isArray(selector) ? selector : [selector]) {
    const found = [...root.querySelectorAll(sel)];
    if (found.length) return found;
  }
  return [];
}

/** ancestor ที่ใกล้ที่สุดซึ่งตรงกับ selector ตัวใดตัวหนึ่ง */
function closestAny(el, selector) {
  for (const sel of Array.isArray(selector) ? selector : [selector]) {
    const found = el.closest(sel);
    if (found) return found;
  }
  return null;
}

const PROVIDERS = [
  {
    id: "gmail",
    name: "Gmail",
    hosts: ["mail.google.com"],

    // ยืนยันแล้วว่าใช้งานได้จริง (เป็นชุดเดิมที่ใช้มาตั้งแต่ต้น)
    selectors: {
      subject: "h2.hP",
      body: "div.a3s",
      sender: "span.gD",
      message: "div.adn",
    },

    /** Gmail ผูกรหัสข้อความไว้กับ ancestor ของกล่องเนื้อหา */
    emailId(bodyEl) {
      const holder = closestAny(bodyEl, ["[data-message-id]", "[data-legacy-message-id]"]);
      if (!holder) return null;
      return holder.getAttribute("data-message-id") || holder.getAttribute("data-legacy-message-id");
    },

    /** span.gD เก็บที่อยู่อีเมลผู้ส่งไว้ในแอตทริบิวต์ email */
    senderAddress(senderEl) {
      return senderEl.getAttribute("email") || senderEl.innerText.trim();
    },
  },

  {
    id: "outlook",
    name: "Outlook Web",
    hosts: ["outlook.live.com", "outlook.office.com", "outlook.office365.com"],

    // ============================================================
    // selector ชุดนี้ "ยังไม่ได้ยืนยันกับหน้าจริง"
    // เป็นเพียงตัวเลือกตั้งต้นที่อิงแอตทริบิวต์เชิงความหมาย (role / aria)
    // ซึ่งมักทนต่อการเปลี่ยน UI มากกว่าคลาสที่ถูก minify
    //
    // ก่อนใช้งานจริงต้องรันสคริปต์ scripts/selector_probe.js
    // ใน DevTools console ขณะเปิดอ่านอีเมลใน Outlook แล้วนำผลมาแก้ที่นี่
    // ============================================================
    selectors: {
      subject: ['div[role="heading"][aria-level="2"]', 'span[role="heading"]'],
      body: ["#UniqueMessageBody", 'div[role="document"]', "div.allowTextSelection"],
      sender: ['span[title*="@"]', 'button[title*="@"]'],
      message: ['div[role="main"]', 'div[role="listitem"]'],
    },

    /**
     * Outlook ไม่ได้วางรหัสข้อความไว้ใน DOM แบบที่ Gmail ทำ จึงคืน null
     * ไม่เป็นปัญหาเพราะ Email.contentKey() ถอยไปใช้ subject + bodyContent แทนเอง
     * และ backend ก็รับ email_id เป็น Optional อยู่แล้ว (backend/app/schemas.py)
     */
    emailId() {
      return null;
    },

    /** Outlook มักเก็บที่อยู่ผู้ส่งไว้ใน title ของ element ชื่อผู้ส่ง */
    senderAddress(senderEl) {
      return senderEl.getAttribute("title") || senderEl.innerText.trim();
    },
  },
];

const Providers = {
  /** เลือกผู้ให้บริการจากโฮสต์ของหน้าปัจจุบัน ไม่รู้จัก = null (ส่วนขยายจะอยู่เฉย ๆ) */
  forHost(hostname) {
    const host = hostname || location.hostname;
    return PROVIDERS.find((provider) => provider.hosts.includes(host)) || null;
  },
};

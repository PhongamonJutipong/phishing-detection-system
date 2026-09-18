/**
 * Class Config (แผนภาพคลาส รูปที่ 3.2) — ฝั่งส่วนขยาย
 * ใช้ร่วมกันทั้ง service worker (importScripts), content scripts และ popup
 *
 * ก่อน publish ขึ้น Chrome Web Store จริง ต้องเปลี่ยน API_ENDPOINT เป็น HTTPS endpoint ของ
 * production backend และเพิ่ม origin นั้นใน manifest.json -> host_permissions ด้วย
 */
class Config {
  static DEFAULTS = Object.freeze({
    // ใช้ 127.0.0.1 แทน localhost: บน Windows การต่อผ่านชื่อ localhost อาจเสียเวลาลอง IPv6 (::1)
    // ก่อนถอยมาใช้ IPv4 ประมาณ 2 วินาทีต่อ request ซึ่งเกินเกณฑ์เรียลไทม์ของโครงงาน (ข้อ 1.4.2)
    API_ENDPOINT: "http://127.0.0.1:8000/api/v1/analyze",
    MIN_RISK_THRESHOLD: 0.5,     // >= ค่านี้ = อันตราย (สีแดง)
    SUSPICIOUS_THRESHOLD: 0.3,   // >= ค่านี้ = มีโอกาสเสี่ยง (สีเหลือง) และเริ่มไฮไลต์คำเสี่ยง
    REQUEST_TIMEOUT_MS: 10000,
    SCAN_ENABLED: true,
    UI_LANGUAGE: null,           // "th" | "en" | null (ตามภาษาของเบราว์เซอร์)
    PRIVACY_CONSENT: null,       // "accepted" | "rejected" | null (ยังไม่ได้เลือก)
  });

  /** getConfig(key): ดึงค่าการตั้งค่าตามคีย์ (ค่าที่ผู้ใช้บันทึกไว้ก่อน ไม่มีจึงใช้ค่าเริ่มต้น) */
  static async getConfig(key) {
    const stored = await chrome.storage.local.get(key);
    return stored[key] ?? Config.DEFAULTS[key];
  }

  static async getAll() {
    const stored = await chrome.storage.local.get(Object.keys(Config.DEFAULTS));
    const merged = {};
    for (const [key, value] of Object.entries(Config.DEFAULTS)) {
      merged[key] = stored[key] ?? value;
    }
    return merged;
  }

  static async setConfig(key, value) {
    await chrome.storage.local.set({ [key]: value });
  }

  static async resolveLanguage() {
    const lang = await Config.getConfig("UI_LANGUAGE");
    if (lang === "th" || lang === "en") return lang;
    return (navigator.language || "").toLowerCase().startsWith("th") ? "th" : "en";
  }
}

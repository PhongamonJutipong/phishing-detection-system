const POPUP_TEXT = {
  th: {
    title: "Phishing Email Detector",
    subtitle: "ตรวจจับอีเมลฟิชชิงอัตโนมัติขณะเปิดอ่านใน Gmail",
    lastResult: "ผลการวิเคราะห์ล่าสุด",
    scanEnabled: "เปิดการตรวจจับอัตโนมัติ",
    language: "ภาษาที่แสดงผล",
    apiUrl: "Backend API URL",
    save: "บันทึกการตั้งค่า",
    saved: "บันทึกแล้ว",
    invalidUrl: "URL ไม่ถูกต้อง",
    checking: "กำลังตรวจสอบการเชื่อมต่อ...",
    online: "เชื่อมต่อเซิร์ฟเวอร์สำเร็จ",
    degraded: "เชื่อมต่อได้ แต่ระบบยังไม่พร้อมใช้งานครบ",
    offline: "ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้",
    privacyAccepted: "ความเป็นส่วนตัว: อนุญาตแล้ว",
    privacyRejected: "ความเป็นส่วนตัว: ปฏิเสธ",
    privacyPending: "ความเป็นส่วนตัว: ยังไม่ได้เลือก",
    privacyReset: "ถามใหม่อีกครั้ง",
  },
  en: {
    title: "Phishing Email Detector",
    subtitle: "Automatically detects phishing emails while reading Gmail",
    lastResult: "Latest analysis",
    scanEnabled: "Enable automatic detection",
    language: "Display language",
    apiUrl: "Backend API URL",
    save: "Save settings",
    saved: "Saved",
    invalidUrl: "Invalid URL",
    checking: "Checking connection...",
    online: "Connected to server",
    degraded: "Connected, but the server is not fully ready",
    offline: "Cannot connect to server",
    privacyAccepted: "Privacy: accepted",
    privacyRejected: "Privacy: rejected",
    privacyPending: "Privacy: not decided",
    privacyReset: "Ask again",
  },
};

const $ = (id) => document.getElementById(id);
let lang = "en";
const t = (key) => (POPUP_TEXT[lang] || POPUP_TEXT.en)[key];

function applyTexts() {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
}

async function checkHealth(analyzeUrl) {
  $("status-dot").className = "dot";
  $("status-text").textContent = t("checking");
  try {
    const healthUrl = new URL("health", new URL(".", analyzeUrl)).toString();
    const res = await fetch(healthUrl, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = await res.json();
    const ready = body.status === "ok";
    $("status-dot").className = `dot ${ready ? "online" : "degraded"}`;
    $("status-text").textContent = t(ready ? "online" : "degraded");
  } catch (e) {
    $("status-dot").className = "dot offline";
    $("status-text").textContent = t("offline");
  }
}

function renderPrivacy(consent) {
  const key = consent === "accepted" ? "privacyAccepted" : consent === "rejected" ? "privacyRejected" : "privacyPending";
  $("privacy-status").textContent = t(key);
}

function renderLastResult(last) {
  if (!last) return;
  $("last-result").hidden = false;
  $("last-score").textContent = `${Number(last.risk_percentage).toFixed(2)}%`;
  $("last-score").className = `pd-chip pd-level-${last.risk_level}`;
  $("last-subject").textContent = last.subject || "-";
}

async function load() {
  const settings = await Config.getAll();
  lang = await Config.resolveLanguage();
  applyTexts();

  $("api-url").value = settings.API_ENDPOINT;
  $("scan-enabled").checked = settings.SCAN_ENABLED;
  $("ui-language").value = settings.UI_LANGUAGE || "";
  renderPrivacy(settings.PRIVACY_CONSENT);
  const { LAST_RESULT } = await chrome.storage.local.get("LAST_RESULT");
  renderLastResult(LAST_RESULT);
  checkHealth(settings.API_ENDPOINT);
}

$("save-btn").addEventListener("click", async () => {
  const url = $("api-url").value.trim();
  try {
    const parsed = new URL(url);
    if (!/^https?:$/.test(parsed.protocol)) throw new Error("protocol");
  } catch (e) {
    $("save-status").textContent = t("invalidUrl");
    $("save-status").className = "error";
    return;
  }
  await chrome.storage.local.set({
    API_ENDPOINT: url,
    SCAN_ENABLED: $("scan-enabled").checked,
    UI_LANGUAGE: $("ui-language").value || null,
  });
  lang = await Config.resolveLanguage();
  applyTexts();
  renderPrivacy(await Config.getConfig("PRIVACY_CONSENT"));
  $("save-status").textContent = t("saved");
  $("save-status").className = "";
  setTimeout(() => ($("save-status").textContent = ""), 1500);
  checkHealth(url);
});

$("privacy-reset").addEventListener("click", async () => {
  await chrome.storage.local.remove("PRIVACY_CONSENT");
  renderPrivacy(null);
});

load();

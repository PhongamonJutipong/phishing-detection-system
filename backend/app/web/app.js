/**
 * หน้าเว็บตรวจสอบอีเมลฟิชชิง — วางเนื้อหาอีเมล -> กดตรวจสอบ -> เห็นผลทันที
 * เรียก API เดียวกับส่วนขยาย (POST /api/v1/analyze) จาก origin เดียวกัน จึงไม่ต้องตั้งค่าอะไรเพิ่ม
 */
const TEXT = {
  th: {
    appTitle: "🛡️ ตรวจสอบอีเมลฟิชชิง",
    lead: "วางเนื้อหาอีเมลที่ต้องการตรวจสอบลงในช่องด้านล่าง แล้วกดปุ่มตรวจสอบ ระบบจะวิเคราะห์ด้วยโมเดลการเรียนรู้ของเครื่องและแสดงระดับความเสี่ยงพร้อมคำที่น่าสงสัย",
    inputLabel: "เนื้อหาอีเมล",
    placeholder: "วางหัวข้อและเนื้อหาอีเมลที่นี่...",
    analyze: "ตรวจสอบอีเมล",
    analyzing: "กำลังวิเคราะห์...",
    sample: "ใส่ตัวอย่างอีเมล",
    clear: "ล้างข้อความ",
    charCount: "{count} ตัวอักษร",
    shortcut: "กด Ctrl + Enter เพื่อตรวจสอบ",
    emptyInput: "กรุณาวางเนื้อหาอีเมลก่อนกดตรวจสอบ",
    tooLong: "เนื้อหายาวเกิน 100,000 ตัวอักษร กรุณาตัดให้สั้นลง",
    levelDangerous: "อันตราย — เข้าข่ายอีเมลฟิชชิง",
    levelSuspicious: "มีโอกาสเสี่ยง — ควรตรวจสอบเพิ่มเติม",
    levelSafe: "ไม่พบอันตรายที่ชัดเจน",
    recommendDangerous: "ไม่ควรคลิกลิงก์ เปิดไฟล์แนบ หรือตอบกลับอีเมลนี้ และควรแจ้งฝ่ายไอทีขององค์กร",
    recommendSuspicious: "ตรวจสอบที่อยู่อีเมลผู้ส่งและปลายทางของลิงก์ให้แน่ใจก่อนดำเนินการใดๆ",
    recommendSafe: "ไม่พบความเสี่ยงที่ชัดเจน แต่ควรระมัดระวังเมื่อมีการขอข้อมูลสำคัญ",
    factClassification: "ผลการจำแนกประเภท",
    factLanguage: "ภาษาของเนื้อหา",
    factTime: "เวลาที่ใช้วิเคราะห์",
    classPhishing: "อีเมลฟิชชิง",
    classLegitimate: "อีเมลปกติ",
    langTh: "ภาษาไทย",
    langEn: "ภาษาอังกฤษ",
    detailsTitle: "รายละเอียดการวิเคราะห์",
    highlightTitle: "เนื้อหาอีเมลพร้อมคำที่น่าสงสัย",
    caution: "*ข้อควรระวัง: โปรดอย่าคลิกลิงก์หรือให้ข้อมูลส่วนตัวใดๆ หากคุณไม่มั่นใจในตัวผู้ส่งอีเมลนี้",
    footer: "ระบบตรวจจับอีเมลฟิชชิงโดยใช้การประมวลผลภาษาธรรมชาติ ·",
    indicator_urgency: "พบข้อความที่สร้างความเร่งด่วนหรือกดดันให้รีบดำเนินการ",
    indicator_credential_request: "พบการขอข้อมูลส่วนบุคคล รหัสผ่าน หรือข้อมูลทางการเงิน",
    indicator_authority: "พบการอ้างถึงหน่วยงานหรือบุคคลที่มีอำนาจ",
    indicator_reward: "พบการเสนอผลประโยชน์หรือของรางวัล",
    indicator_suspicious_link: "พบลิงก์หรือข้อความชักชวนให้คลิก",
    detailKeywords: "ตรวจพบคำที่มีความเสี่ยง {count} คำ เช่น: {terms}",
    detailNoIndicator: "ไม่พบรูปแบบข้อความหลอกลวงที่ชัดเจน",
    reason_model_keyword: "คำที่โมเดลประเมินว่ามีความเสี่ยง",
    reason_urgency: "ความเร่งด่วน",
    reason_credential_request: "การขอข้อมูลส่วนบุคคล/รหัสผ่าน",
    reason_authority: "การแอบอ้างผู้มีอำนาจ",
    reason_reward: "การเสนอผลประโยชน์",
    reason_suspicious_link: "ลิงก์/การชักชวนให้คลิก",
    statusChecking: "กำลังตรวจสอบระบบ...",
    statusOnline: "ระบบพร้อมใช้งาน",
    statusDegraded: "ระบบทำงานได้บางส่วน",
    statusOffline: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้",
    errorModel: "โมเดลยังไม่พร้อมใช้งาน กรุณาเทรนโมเดลก่อน (ml/train.py)",
    errorNetwork: "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจสอบว่า backend ทำงานอยู่",
    errorServer: "เซิร์ฟเวอร์เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง",
    sampleEmail:
      "[แจ้งเตือนด่วน] บัญชีของคุณถูกระงับชั่วคราว กรุณายืนยันตัวตนทันที\n\n" +
      "เรียน ผู้ใช้งาน\n\nเราตรวจพบความพยายามในการเข้าสู่ระบบที่ผิดปกติจากอุปกรณ์ที่คุณไม่เคยใช้งาน " +
      "เพื่อความปลอดภัยของบัญชี ระบบได้ระงับการเข้าถึงบัญชีของคุณไว้ชั่วคราว\n\n" +
      "กรุณาดำเนินการภายใน 24 ชั่วโมง มิฉะนั้นบัญชีของคุณจะถูกปิดใช้งานอย่างถาวร\n" +
      "1. คลิกที่ลิงก์ด้านล่างเพื่อเข้าสู่ระบบยืนยันตัวตน\n" +
      "2. ตรวจสอบข้อมูลส่วนบุคคลและรหัสผ่านของคุณ\n" +
      "http://verify-scurity-check-login.com/th/auth\n\n" +
      "ขออภัยในความไม่สะดวก ฝ่ายรักษาความปลอดภัยข้อมูลลูกค้า",
  },
  en: {
    appTitle: "🛡️ Phishing Email Checker",
    lead: "Paste the email you want to check in the box below and press the button. The machine learning model analyzes it and shows the risk level with the suspicious words.",
    inputLabel: "Email content",
    placeholder: "Paste the email subject and body here...",
    analyze: "Check email",
    analyzing: "Analyzing...",
    sample: "Insert sample email",
    clear: "Clear",
    charCount: "{count} characters",
    shortcut: "Press Ctrl + Enter to check",
    emptyInput: "Please paste the email content first",
    tooLong: "The content is longer than 100,000 characters, please shorten it",
    levelDangerous: "Dangerous — looks like a phishing email",
    levelSuspicious: "Suspicious — check it further",
    levelSafe: "No clear threat found",
    recommendDangerous: "Do not click links, open attachments or reply. Report this email to your IT department.",
    recommendSuspicious: "Verify the sender address and link destinations before taking any action.",
    recommendSafe: "No clear risk found, but stay careful when asked for sensitive information.",
    factClassification: "Classification",
    factLanguage: "Content language",
    factTime: "Analysis time",
    classPhishing: "Phishing email",
    classLegitimate: "Legitimate email",
    langTh: "Thai",
    langEn: "English",
    detailsTitle: "Analysis details",
    highlightTitle: "Email content with suspicious words",
    caution: "*Caution: Please do not click any links or provide personal information if you do not trust the sender.",
    footer: "Phishing Email Detection using Natural Language Processing ·",
    indicator_urgency: "Suspicious urgency or pressure to act quickly detected in the content.",
    indicator_credential_request: "Request for personal information, passwords or financial data detected.",
    indicator_authority: "Reference to an authority (bank, IT department, government) detected.",
    indicator_reward: "Offer of rewards or benefits detected.",
    indicator_suspicious_link: "Links or call-to-action to click detected.",
    detailKeywords: "Detected {count} suspicious keywords, including: {terms}",
    detailNoIndicator: "No clear deceptive patterns were found.",
    reason_model_keyword: "Keyword the model rated as risky",
    reason_urgency: "Urgency",
    reason_credential_request: "Personal information / password request",
    reason_authority: "Authority impersonation",
    reason_reward: "Reward offer",
    reason_suspicious_link: "Link / call-to-action",
    statusChecking: "Checking system...",
    statusOnline: "System ready",
    statusDegraded: "System partially ready",
    statusOffline: "Cannot reach the server",
    errorModel: "The detection model is not ready — train it first (ml/train.py)",
    errorNetwork: "Cannot reach the server, please check that the backend is running",
    errorServer: "The server encountered an error, please try again",
    sampleEmail:
      "Security Alert: Your account has been temporarily suspended\n\n" +
      "Dear Customer,\n\nWe detected some unusual activity on your account. For your protection, your access " +
      "has been Suspended until you Verify your identity.\n\n" +
      "Please click the link below to update your information and secure your account. If you do not complete " +
      "this process within 24 hours, your account will be Permanently Deleted.\n\n" +
      "Click here to Verify Now: http://secure-update-login.com\n\nThank you for your cooperation.",
  },
};

const MAX_LENGTH = 100000;
const $ = (id) => document.getElementById(id);

let lang = (navigator.language || "").toLowerCase().startsWith("th") ? "th" : "en";
let lastResult = null;
let lastText = "";

const t = (key, params = {}) =>
  String(TEXT[lang][key] ?? TEXT.en[key] ?? key).replace(/\{(\w+)\}/g, (_, name) =>
    name in params ? params[name] : `{${name}}`
  );

function applyTexts() {
  document.documentElement.lang = lang;
  document.title = t("appTitle").replace(/^\S+\s/, "");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  $("email-text").placeholder = t("placeholder");
  $("lang-toggle").textContent = lang === "th" ? "EN" : "ไทย";
  updateCharCount();
  if (lastResult) renderResult(lastResult, lastText);
}

function updateCharCount() {
  const count = $("email-text").value.length;
  $("char-count").textContent = count
    ? t("charCount", { count: count.toLocaleString() })
    : t("shortcut");
}

// ---------- สถานะเซิร์ฟเวอร์ ----------
async function checkHealth() {
  const box = $("server-status");
  box.className = "status";
  $("server-status-text").textContent = t("statusChecking");
  try {
    const res = await fetch("api/v1/health", { signal: AbortSignal.timeout(5000) });
    const body = await res.json();
    const ready = body.status === "ok";
    box.className = `status ${ready ? "online" : "degraded"}`;
    $("server-status-text").textContent = t(ready ? "statusOnline" : "statusDegraded");
  } catch (err) {
    box.className = "status offline";
    $("server-status-text").textContent = t("statusOffline");
  }
}

// ---------- วิเคราะห์ ----------
async function analyze(event) {
  event.preventDefault();
  const text = $("email-text").value.trim();
  $("form-error").textContent = "";

  if (!text) {
    $("form-error").textContent = t("emptyInput");
    $("email-text").focus();
    return;
  }
  if (text.length > MAX_LENGTH) {
    $("form-error").textContent = t("tooLong");
    return;
  }

  setLoading(true);
  try {
    const res = await fetch("api/v1/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject: "", body_content: text }),
    });
    if (!res.ok) {
      $("form-error").textContent = t(res.status === 503 ? "errorModel" : "errorServer");
      return;
    }
    const data = await res.json();
    lastResult = data;
    lastText = text;
    renderResult(data, text);
    $("result").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    $("form-error").textContent = t("errorNetwork");
  } finally {
    setLoading(false);
    checkHealth();
  }
}

function setLoading(loading) {
  $("analyze-btn").disabled = loading;
  $("analyze-label").textContent = t(loading ? "analyzing" : "analyze");
}

function renderResult(data, text) {
  const result = $("result");
  result.hidden = false;
  result.className = `result level-${data.risk_level}`;

  const percentage = Number(data.risk_percentage);
  $("score-ring").style.setProperty("--score", percentage);
  $("score-value").textContent = `${percentage.toFixed(1)}%`;
  $("level-text").textContent = t(
    { dangerous: "levelDangerous", suspicious: "levelSuspicious", safe: "levelSafe" }[data.risk_level]
  );
  $("recommend-text").textContent = t(
    { dangerous: "recommendDangerous", suspicious: "recommendSuspicious", safe: "recommendSafe" }[data.risk_level]
  );

  $("fact-classification").textContent = t(data.classification === "phishing" ? "classPhishing" : "classLegitimate");
  $("fact-language").textContent = t(data.language === "th" ? "langTh" : "langEn");
  $("fact-time").textContent = `${Number(data.processing_time_ms).toFixed(0)} ms`;

  renderDetails(data);
  renderHighlightedText(data, text);
}

function renderDetails(data) {
  const list = $("details-list");
  list.replaceChildren();

  (data.indicators || []).forEach((indicator) => {
    const item = document.createElement("li");
    item.textContent = t(`indicator_${indicator.category}`);
    if (indicator.phrases && indicator.phrases.length) {
      const phrases = document.createElement("span");
      phrases.className = "phrases";
      phrases.textContent = ` (${indicator.phrases.slice(0, 5).join(", ")})`;
      item.append(phrases);
    }
    list.append(item);
  });

  const keywords = data.suspicious_keywords || [];
  if (keywords.length) {
    const item = document.createElement("li");
    item.textContent = t("detailKeywords", { count: keywords.length, terms: keywords.slice(0, 8).join(", ") });
    list.append(item);
  }
  if (!list.children.length) {
    const item = document.createElement("li");
    item.textContent = t("detailNoIndicator");
    list.append(item);
  }
}

/** แสดงเนื้อหาอีเมลพร้อมไฮไลต์คำเสี่ยง (สร้างเป็น text node เท่านั้น ไม่ใช้ innerHTML) */
function renderHighlightedText(data, text) {
  const container = $("highlighted-text");
  container.replaceChildren();

  const reasonByTerm = new Map();
  (data.highlights || []).forEach(({ phrase, reason }) => {
    const key = (phrase || "").trim().toLowerCase();
    if (key.length >= 2 && !reasonByTerm.has(key)) reasonByTerm.set(key, reason);
  });

  if (data.risk_level === "safe" || !reasonByTerm.size) {
    container.textContent = text;
    return;
  }

  const escape = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = [...reasonByTerm.keys()]
    .sort((a, b) => b.length - a.length)
    // ภาษาอังกฤษจับทั้งคำ ภาษาไทยจับแบบ substring เพราะไม่มีช่องว่างระหว่างคำ
    .map((term) => (/^[\x00-\x7F]+$/.test(term) ? `(?<![A-Za-z0-9])${escape(term)}(?![A-Za-z0-9])` : escape(term)))
    .join("|");
  const regex = new RegExp(pattern, "gi");

  let last = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match[0].length === 0) {
      regex.lastIndex++;
      continue;
    }
    container.append(text.slice(last, match.index));
    const mark = document.createElement("mark");
    mark.className = "hl";
    mark.textContent = match[0];
    mark.title = t(`reason_${reasonByTerm.get(match[0].toLowerCase()) || "model_keyword"}`);
    container.append(mark);
    last = match.index + match[0].length;
  }
  container.append(text.slice(last));
}

// ---------- events ----------
$("analyze-form").addEventListener("submit", analyze);
$("email-text").addEventListener("input", updateCharCount);
$("email-text").addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") $("analyze-form").requestSubmit();
});
$("sample-btn").addEventListener("click", () => {
  $("email-text").value = t("sampleEmail");
  updateCharCount();
  $("analyze-form").requestSubmit();
});
$("clear-btn").addEventListener("click", () => {
  $("email-text").value = "";
  lastResult = null;
  $("result").hidden = true;
  $("form-error").textContent = "";
  updateCharCount();
  $("email-text").focus();
});
$("lang-toggle").addEventListener("click", () => {
  lang = lang === "th" ? "en" : "th";
  localStorage.setItem("ui_language", lang);
  applyTexts();
  checkHealth();
});

const savedLang = localStorage.getItem("ui_language");
if (savedLang === "th" || savedLang === "en") lang = savedLang;
applyTexts();
checkHealth();

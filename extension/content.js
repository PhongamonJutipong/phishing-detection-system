/**
 * Content script ที่ทำงานบน mail.google.com
 * หมายเหตุสำคัญ: Gmail เป็น SPA ที่เปลี่ยน DOM บ่อยและ class name อาจเปลี่ยนไปตามเวอร์ชัน
 * selector ด้านล่างเป็นจุดเริ่มต้น (ใช้งานได้กับ Gmail เวอร์ชันปัจจุบันส่วนใหญ่)
 * แต่ควรตรวจสอบ/ปรับปรุงเป็นระยะเมื่อ Gmail อัปเดต UI
 */

const SELECTORS = {
  subject: "h2.hP",
  body: "div.a3s.aiL",
  sender: "span.gD",
};

let lastAnalyzedHash = null;
let bannerEl = null;

function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

function extractEmailContent() {
  const subjectEl = document.querySelector(SELECTORS.subject);
  const bodyEl = document.querySelector(SELECTORS.body);
  const senderEl = document.querySelector(SELECTORS.sender);

  if (!bodyEl) return null;

  return {
    subject: subjectEl ? subjectEl.innerText.trim() : "",
    body: bodyEl.innerText.trim(),
    sender: senderEl ? senderEl.getAttribute("email") || senderEl.innerText : null,
    bodyEl,
  };
}

function removeBanner() {
  if (bannerEl) {
    bannerEl.remove();
    bannerEl = null;
  }
}

function renderBanner(result) {
  removeBanner();

  bannerEl = document.createElement("div");
  bannerEl.className = "phishing-detector-banner " + (result.is_phishing ? "risk-high" : "risk-low");
  bannerEl.innerHTML = `
    <span class="pd-icon">${result.is_phishing ? "⚠️" : "✅"}</span>
    <span class="pd-text">
      ${result.is_phishing ? "อีเมลนี้มีความเสี่ยงเป็นฟิชชิง" : "ไม่พบความเสี่ยงที่ชัดเจนในอีเมลนี้"}
      — ระดับความเสี่ยง <strong>${result.risk_percentage.toFixed(1)}%</strong>
    </span>
  `;

  const bodyEl = document.querySelector(SELECTORS.body);
  if (bodyEl && bodyEl.parentElement) {
    bodyEl.parentElement.insertBefore(bannerEl, bodyEl);
  }

  highlightSuspiciousPhrases(bodyEl, result.highlights);
}

function highlightSuspiciousPhrases(bodyEl, highlights) {
  if (!bodyEl || !highlights || highlights.length === 0) return;

  let html = bodyEl.innerHTML;
  highlights.forEach(({ phrase, reason }) => {
    if (!phrase) return;
    const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(${escaped})`, "gi");
    html = html.replace(
      regex,
      `<mark class="phishing-detector-highlight" title="${reason}">$1</mark>`
    );
  });
  bodyEl.innerHTML = html;
}

async function analyzeCurrentEmail() {
  const content = extractEmailContent();
  if (!content) return;

  const hash = simpleHash(content.subject + content.body);
  if (hash === lastAnalyzedHash) return; // อีเมลเดิม ไม่ต้องวิเคราะห์ซ้ำ
  lastAnalyzedHash = hash;

  chrome.runtime.sendMessage(
    {
      type: "ANALYZE_EMAIL",
      payload: {
        subject: content.subject,
        body: content.body,
        sender: content.sender,
      },
    },
    (response) => {
      if (chrome.runtime.lastError) {
        console.warn("Phishing Detector: ", chrome.runtime.lastError.message);
        return;
      }
      if (response && response.ok) {
        renderBanner(response.data);
      } else {
        console.warn("Phishing Detector: วิเคราะห์อีเมลไม่สำเร็จ", response?.error);
      }
    }
  );
}

// Gmail โหลดแบบ SPA จึงต้องเฝ้าดู DOM แทนการรอ page load อย่างเดียว
const observer = new MutationObserver(() => {
  analyzeCurrentEmail();
});
observer.observe(document.body, { childList: true, subtree: true });

// ลองครั้งแรกตอนโหลดสคริปต์ (เผื่อผู้ใช้เปิดอีเมลค้างไว้อยู่แล้ว)
analyzeCurrentEmail();

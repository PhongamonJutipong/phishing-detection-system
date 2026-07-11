const apiUrlInput = document.getElementById("api-url");
const saveBtn = document.getElementById("save-btn");
const saveStatus = document.getElementById("save-status");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

async function loadSettings() {
  const { apiUrl } = await chrome.storage.local.get("apiUrl");
  apiUrlInput.value = apiUrl || DEFAULT_API_URL; // DEFAULT_API_URL มาจาก config.js
  checkHealth(apiUrlInput.value);
}

async function checkHealth(analyzeUrl) {
  try {
    const healthUrl = analyzeUrl.replace("/analyze", "/health");
    const res = await fetch(healthUrl);
    if (res.ok) {
      statusDot.className = "dot online";
      statusText.textContent = "เชื่อมต่อ backend สำเร็จ";
    } else {
      throw new Error("bad status");
    }
  } catch (e) {
    statusDot.className = "dot offline";
    statusText.textContent = "ไม่สามารถเชื่อมต่อ backend ได้";
  }
}

saveBtn.addEventListener("click", async () => {
  const value = apiUrlInput.value.trim();
  await chrome.storage.local.set({ apiUrl: value });
  saveStatus.textContent = "บันทึกแล้ว";
  setTimeout(() => (saveStatus.textContent = ""), 1500);
  checkHealth(value);
});

loadSettings();

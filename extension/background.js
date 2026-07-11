// Service worker: จุดเดียวที่คุยกับ backend API เพื่อรวม logic และจัดการ error ไว้ที่เดียว
importScripts("config.js"); // ให้ DEFAULT_API_URL จาก config.js

async function analyzeEmail(payload) {
  const { apiUrl } = await chrome.storage.local.get("apiUrl");
  const url = apiUrl || DEFAULT_API_URL;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ANALYZE_EMAIL") {
    analyzeEmail(message.payload)
      .then((result) => sendResponse({ ok: true, data: result }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true; // บอก Chrome ว่าจะ sendResponse แบบ async
  }
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ apiUrl: DEFAULT_API_URL });
});

// Service worker: จุดเดียวที่คุยกับ backend API (รวม logic การเชื่อมต่อและการจัดการข้อผิดพลาดไว้ที่เดียว)
importScripts("config.js");

class ApiError extends Error {
  constructor(code, message) {
    super(message || code);
    this.code = code;
  }
}

async function analyzeEmail(payload) {
  const { API_ENDPOINT, REQUEST_TIMEOUT_MS } = await Config.getAll();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(API_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch (err) {
    throw new ApiError(err.name === "AbortError" ? "TIMEOUT" : "NETWORK_ERROR", err.message);
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    if (response.status === 503) throw new ApiError("MODEL_UNAVAILABLE");
    if (response.status === 400 || response.status === 422) throw new ApiError("INVALID_REQUEST");
    throw new ApiError("SERVER_ERROR", `HTTP ${response.status}`);
  }
  return response.json();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ANALYZE_EMAIL") {
    analyzeEmail(message.payload)
      .then(async (data) => {
        await chrome.storage.local.set({
          LAST_RESULT: {
            risk_percentage: data.risk_percentage,
            risk_level: data.risk_level,
            subject: message.payload.subject || "",
            at: new Date().toISOString(),
          },
        });
        sendResponse({ ok: true, data });
      })
      .catch((err) => sendResponse({ ok: false, code: err.code || "SERVER_ERROR", error: err.message }));
    return true; // บอก Chrome ว่าจะ sendResponse แบบ async
  }
  return false;
});

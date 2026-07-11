// ค่าตั้งต้นของ backend API URL — single source of truth
// เดิม background.js กับ popup.js ต่างก็ hardcode string นี้แยกกันคนละที่
// (เสี่ยงแก้ที่หนึ่งแล้วลืมอีกที่) จึงรวมมาไว้ไฟล์เดียวแล้วให้ทั้งสองที่ import มาใช้แทน
//
// ก่อน publish ขึ้น Chrome Web Store จริง ต้องเปลี่ยนค่านี้เป็น HTTPS endpoint ของ
// production backend และเพิ่ม origin นั้นใน manifest.json -> host_permissions ด้วย
// (ตอนนี้ manifest อนุญาตแค่ http://localhost:8000/* สำหรับ dev เท่านั้น)
const DEFAULT_API_URL = "http://localhost:8000/api/v1/analyze";

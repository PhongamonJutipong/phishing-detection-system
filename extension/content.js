/**
 * จุดเริ่มต้นของ content script บน mail.google.com (แผนภาพกิจกรรม รูปที่ 3.9)
 * ขอความยินยอมเรื่องความเป็นส่วนตัว -> เริ่มเฝ้าดูอีเมลที่ผู้ใช้เปิด
 */
(async function main() {
  const ui = new UserInterface();
  await ui.init();
  const scanner = new EmailScanner(ui);

  async function applySettings() {
    const enabled = await Config.getConfig("SCAN_ENABLED");
    if (!enabled) {
      scanner.stop();
      ui.clear();
      return;
    }
    if (await PrivacyConsent.ensure()) {
      scanner.scanDOM();
    } else {
      Logger.logInfo("ผู้ใช้ไม่อนุญาตให้วิเคราะห์เนื้อหาอีเมล");
      scanner.stop();
      ui.clear();
    }
  }

  // ผู้ใช้เปลี่ยนการตั้งค่าใน popup (เปิด/ปิด, ภาษา, ความยินยอม) -> ใช้ค่าใหม่ทันที
  chrome.storage.onChanged.addListener(async (changes, area) => {
    if (area !== "local") return;
    if (changes.UI_LANGUAGE) {
      await ui.init();
      if (ui.result) ui.renderRiskSummary();
    }
    if (changes.SCAN_ENABLED || changes.PRIVACY_CONSENT) {
      scanner.lastKey = null;
      await applySettings();
    }
  });

  await applySettings();
})();

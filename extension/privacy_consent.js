/**
 * หน้าจอข้อตกลงความเป็นส่วนตัวของข้อมูล (รูปที่ 3.15-3.16)
 * ส่วนขยายจะเริ่มอ่านเนื้อหาอีเมลก็ต่อเมื่อผู้ใช้กด "อนุญาต" แล้วเท่านั้น
 */
class PrivacyConsent {
  /** คืนค่า true ถ้าผู้ใช้อนุญาต (ถามผู้ใช้ถ้ายังไม่เคยเลือก) */
  static async ensure() {
    const consent = await Config.getConfig("PRIVACY_CONSENT");
    if (consent === "accepted") return true;
    if (consent === "rejected") return false;
    const accepted = await PrivacyConsent.prompt(await Config.resolveLanguage());
    await Config.setConfig("PRIVACY_CONSENT", accepted ? "accepted" : "rejected");
    return accepted;
  }

  static prompt(lang) {
    return new Promise((resolve) => {
      const t = (key) => translate(lang, key);
      const overlay = el("div", "pd-overlay pd-privacy-overlay");
      const dialog = el("div", "pd-privacy");
      dialog.setAttribute("role", "dialog");
      dialog.setAttribute("aria-modal", "true");

      dialog.append(el("h2", "pd-privacy-title", t("privacyTitle")));
      const body = el("div", "pd-privacy-body");
      t("privacyBody").forEach((paragraph) => body.append(el("p", null, `- ${paragraph}`)));
      dialog.append(body);

      const actions = el("div", "pd-privacy-actions");
      const reject = el("button", "pd-btn-reject", t("privacyReject"));
      const accept = el("button", "pd-btn-accept", t("privacyAccept"));
      reject.type = accept.type = "button";
      const finish = (value) => {
        overlay.remove();
        resolve(value);
      };
      reject.addEventListener("click", () => finish(false));
      accept.addEventListener("click", () => finish(true));
      actions.append(reject, accept);
      dialog.append(actions);

      overlay.append(dialog);
      document.body.append(overlay);
      accept.focus();
    });
  }
}

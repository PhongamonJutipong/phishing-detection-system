/**
 * Class UserInterface (แผนภาพคลาส รูปที่ 3.2)
 *  - showResult()           : UC-05 Display Result
 *  - renderRiskSummary()    : UC-06 Show Risk Summary (ป้าย % ความเสี่ยง 3 สี + ไฮไลต์คำเสี่ยง)
 *  - showDetailedAnalysis() : UC-07 Show Detailed Analysis (หน้าต่างรายงาน)
 *
 * สร้าง DOM ด้วย createElement/textContent เท่านั้น (ไม่ใช้ innerHTML กับข้อมูลจาก server/อีเมล)
 */
const LEVEL_ICON = { dangerous: "⚠️", suspicious: "⚠️", safe: "✅" };
const HIGHLIGHT_CLASS = "pd-highlight";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

class UserInterface {
  constructor() {
    this.riskScore = null;
    this.riskLevel = null;
    this.highlightedTerms = [];
    this.result = null;
    this.lang = "en";
    this.badgeEl = null;
    this.modalEl = null;
    this.onRetry = null;
  }

  async init() {
    this.lang = await Config.resolveLanguage();
  }

  t(key, params) {
    return translate(this.lang, key, params);
  }

  /** showResult(result): กระจายข้อมูลไปเก็บในตัวแปรเพื่อรอการแสดงผล แล้วแสดงผล */
  async showResult(result, bodyEl) {
    this.result = result;
    this.riskScore = result.risk_score;
    this.riskLevel = result.risk_level;
    this.highlightedTerms = result.highlights || [];

    const suspiciousThreshold = await Config.getConfig("SUSPICIOUS_THRESHOLD");
    this.clearHighlights();
    if (bodyEl && this.riskScore >= suspiciousThreshold) {
      this.highlight(bodyEl, this.highlightedTerms);
    }
    this.renderRiskSummary();
  }

  /** renderRiskSummary(): เปลี่ยน riskScore/riskLevel เป็นป้ายเปอร์เซ็นต์ความเสี่ยงตามสี */
  renderRiskSummary() {
    const level = this.riskLevel || "safe";
    const badge = this.ensureBadge(`pd-badge pd-level-${level}`);
    badge.append(
      el("span", "pd-badge-icon", LEVEL_ICON[level]),
      el("span", "pd-badge-score", this.t("badgeRisk", { score: Number(this.result.risk_percentage).toFixed(2) })),
      el("span", "pd-badge-link", `${this.t("badgeDetails")} ⓘ`)
    );
    badge.title = this.t(this.levelKey(level));
    badge.onclick = () => this.showDetailedAnalysis();
    Logger.logInfo("Result Displayed Successfully");
  }

  showLoading() {
    const badge = this.ensureBadge("pd-badge pd-level-loading");
    badge.append(el("span", "pd-spinner"), el("span", "pd-badge-score", this.t("badgeLoading")));
    badge.onclick = null;
  }

  /** แสดงข้อผิดพลาดให้ผู้ใช้ทราบ (UC-05 ทางเลือก 2.1, UC-06/07 ทางเลือก) */
  showError(code) {
    this.clearHighlights();
    const badge = this.ensureBadge("pd-badge pd-level-error");
    badge.append(
      el("span", "pd-badge-icon", "⛔"),
      el("span", "pd-badge-score", `${this.t("badgeError")}: ${this.t(`error_${code || "SERVER_ERROR"}`)}`),
      el("span", "pd-badge-link", this.t("badgeRetry"))
    );
    badge.onclick = () => this.onRetry && this.onRetry();
  }

  /** showDetailedAnalysis(): หน้าต่างรายละเอียดอธิบายความเสี่ยง (รูปที่ 3.13-3.14) */
  showDetailedAnalysis() {
    if (!this.result) return;
    this.closeDetailedAnalysis();
    const r = this.result;
    const level = r.risk_level;

    const overlay = el("div", "pd-overlay");
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) this.closeDetailedAnalysis();
    });

    const modal = el("div", `pd-modal pd-level-${level}`);
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");

    const header = el("div", "pd-modal-header");
    header.append(el("div", "pd-modal-icon", LEVEL_ICON[level]), el("h2", "pd-modal-title", this.t("reportTitle")));

    const body = el("div", "pd-modal-body");
    const scoreRow = el("div", "pd-score-row");
    scoreRow.append(
      el("span", "pd-score-label", this.t("reportScore")),
      el("span", "pd-score-value", `${Number(r.risk_percentage).toFixed(2)}%`)
    );
    body.append(scoreRow);

    const facts = el("dl", "pd-facts");
    const addFact = (label, value) => facts.append(el("dt", null, label), el("dd", null, value));
    addFact(this.t("reportLevel"), this.t(this.levelKey(level)));
    addFact(this.t("reportClassification"), this.t(r.classification === "phishing" ? "classPhishing" : "classLegitimate"));
    addFact(this.t("reportLanguage"), this.t(r.language === "th" ? "langTh" : "langEn"));
    body.append(facts);

    body.append(el("h3", "pd-section-title", this.t("reportDetails")));
    const list = el("ul", "pd-details");
    (r.indicators || []).forEach((indicator) => {
      const item = el("li", null, this.t(`indicator_${indicator.category}`));
      if (indicator.phrases && indicator.phrases.length) {
        item.append(el("span", "pd-phrases", ` (${indicator.phrases.slice(0, 5).join(", ")})`));
      }
      list.append(item);
    });
    const keywords = r.suspicious_keywords || [];
    if (keywords.length) {
      list.append(el("li", null, this.t("detailKeywords", { count: keywords.length, terms: keywords.slice(0, 8).join(", ") })));
    }
    if (!list.children.length) list.append(el("li", null, this.t("detailNoIndicator")));
    body.append(list);

    body.append(el("h3", "pd-section-title", this.t("reportRecommendation")));
    const recommendKey = { dangerous: "recommendDangerous", suspicious: "recommendSuspicious", safe: "recommendSafe" }[level];
    body.append(el("p", "pd-recommend", this.t(recommendKey)));
    body.append(el("p", "pd-caution", this.t("reportCaution")));

    const closeBtn = el("button", "pd-close-btn", this.t("reportClose"));
    closeBtn.type = "button";
    closeBtn.addEventListener("click", () => this.closeDetailedAnalysis());
    body.append(closeBtn);

    modal.append(header, body);
    overlay.append(modal);
    document.body.append(overlay);
    this.modalEl = overlay;
    this._escHandler = (e) => e.key === "Escape" && this.closeDetailedAnalysis();
    document.addEventListener("keydown", this._escHandler);
    closeBtn.focus();
  }

  closeDetailedAnalysis() {
    if (this.modalEl) {
      this.modalEl.remove();
      this.modalEl = null;
      document.removeEventListener("keydown", this._escHandler);
    }
  }

  clear() {
    this.closeDetailedAnalysis();
    this.clearHighlights();
    if (this.badgeEl) {
      this.badgeEl.remove();
      this.badgeEl = null;
    }
    this.result = null;
    this.riskScore = null;
    this.riskLevel = null;
    this.highlightedTerms = [];
  }

  // ---------- helpers ----------
  levelKey(level) {
    return { dangerous: "levelDangerous", suspicious: "levelSuspicious", safe: "levelSafe" }[level] || "levelSafe";
  }

  ensureBadge(className) {
    if (!this.badgeEl || !document.body.contains(this.badgeEl)) {
      this.badgeEl = el("div");
      this.badgeEl.setAttribute("role", "status");
      document.body.append(this.badgeEl);
    }
    this.badgeEl.className = className;
    this.badgeEl.replaceChildren();
    return this.badgeEl;
  }

  /**
   * ไฮไลต์คำเสี่ยงเฉพาะใน text node (ไม่แก้ innerHTML จึงไม่ทำลายลิงก์/attribute ของ Gmail)
   * ภาษาอังกฤษจับทั้งคำ (word boundary) ภาษาไทยจับแบบ substring เพราะไม่มีช่องว่างระหว่างคำ
   */
  highlight(root, terms) {
    const reasonByTerm = new Map();
    terms.forEach(({ phrase, reason }) => {
      const key = (phrase || "").trim().toLowerCase();
      if (key.length >= 2 && !reasonByTerm.has(key)) reasonByTerm.set(key, reason);
    });
    if (!reasonByTerm.size) return;

    const parts = [...reasonByTerm.keys()]
      .sort((a, b) => b.length - a.length)
      .map((term) => (/^[\x00-\x7F]+$/.test(term) ? `(?<![A-Za-z0-9])${escapeRegExp(term)}(?![A-Za-z0-9])` : escapeRegExp(term)));
    const regex = new RegExp(parts.join("|"), "gi");

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => {
        const parent = node.parentElement;
        if (!parent || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (parent.closest(`mark.${HIGHLIGHT_CLASS}, script, style, textarea`)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);

    textNodes.forEach((node) => {
      const text = node.nodeValue;
      regex.lastIndex = 0;
      let match;
      let last = 0;
      const fragment = document.createDocumentFragment();
      while ((match = regex.exec(text)) !== null) {
        if (match[0].length === 0) {
          regex.lastIndex++;
          continue;
        }
        fragment.append(text.slice(last, match.index));
        const reason = reasonByTerm.get(match[0].toLowerCase()) || "model_keyword";
        const mark = el("mark", `${HIGHLIGHT_CLASS} pd-reason-${reason}`, match[0]);
        mark.title = this.t(`reason_${reason}`);
        fragment.append(mark);
        last = match.index + match[0].length;
      }
      if (last > 0) {
        fragment.append(text.slice(last));
        node.replaceWith(fragment);
      }
    });
  }

  clearHighlights() {
    document.querySelectorAll(`mark.${HIGHLIGHT_CLASS}`).forEach((mark) => {
      const parent = mark.parentNode;
      mark.replaceWith(document.createTextNode(mark.textContent));
      parent && parent.normalize();
    });
  }
}

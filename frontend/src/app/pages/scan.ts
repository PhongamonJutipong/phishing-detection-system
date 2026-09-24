import { DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { TimeoutError, timeout } from 'rxjs';

import { ApiService } from '../core/api.service';
import { I18nService } from '../core/i18n.service';
import { AnalyzeResponse } from '../core/models';
import { SiteFooter } from '../shared/site-footer';
import { SiteNav } from '../shared/site-nav';

const MAX_LENGTH = 100_000;
// เผื่อเน็ตช้ามาก (Slow 3G ใช้ราว 2.5 วินาที) แต่ไม่ปล่อยให้ปุ่มหมุนค้างไม่มีที่สิ้นสุดเมื่อเน็ตหลุด
const ANALYZE_TIMEOUT_MS = 45_000;

/** ตัวอย่างอีเมลสำหรับกดสาธิต แยกตามภาษาที่เลือกอยู่ */
const SAMPLE = {
  th:
    'เรียน ผู้ใช้บริการ\n\n' +
    'ระบบตรวจพบความผิดปกติในบัญชีของท่าน บัญชีจะถูกระงับการใช้งานภายใน 24 ชั่วโมง\n' +
    'กรุณายืนยันตัวตนและกรอกรหัสผ่านเพื่อเปิดใช้งานบัญชีอีกครั้ง มิฉะนั้นบัญชีจะถูกปิดถาวร\n\n' +
    'คลิกที่นี่เพื่อยืนยันทันที: http://secure-update-login.com\n\nขอบคุณครับ',
  en:
    'Dear Customer,\n\n' +
    'We have detected unusual activity on your account. Your account will be suspended ' +
    'within 24 hours.\n' +
    'Please click the link below to update your information and secure your account. ' +
    'If you do not complete this process, your account will be permanently deleted.\n\n' +
    'Click here to verify now: http://secure-update-login.com\n\nThank you for your cooperation.',
} as const;

type ServerStatus = 'checking' | 'online' | 'degraded' | 'offline';

@Component({
  selector: 'app-scan',
  imports: [SiteNav, SiteFooter, DecimalPipe],
  templateUrl: './scan.html',
})
export class Scan {
  private readonly api = inject(ApiService);
  protected readonly i18n = inject(I18nService);
  protected readonly t = this.i18n.t;

  protected readonly text = signal('');
  protected readonly loading = signal(false);
  protected readonly formError = signal('');
  protected readonly result = signal<AnalyzeResponse | null>(null);
  protected readonly status = signal<ServerStatus>('checking');

  protected readonly charCount = computed(() => this.text().length);

  /**
   * เนื้อหาอีเมลที่ถูกซอยเป็นชิ้น พร้อมธงว่าชิ้นไหนคือคำเสี่ยงที่ต้องไฮไลต์
   *
   * ทำเป็นข้อมูลแล้วให้เทมเพลตวาด แทนการต่อสตริง HTML เอง
   * Angular จะ escape ข้อความให้เองทุกชิ้น จึงไม่มีทางเกิด XSS จากเนื้อหาอีเมล
   */
  protected readonly highlightedParts = computed(() => {
    const data = this.result();
    const source = this.submittedText();
    if (!data || !source) {
      return [];
    }

    const phrases = [...new Set(data.highlights.map((h) => h.phrase).filter((p) => p.length > 1))]
      .sort((a, b) => b.length - a.length);
    if (phrases.length === 0) {
      return [{ text: source, risky: false }];
    }

    const pattern = new RegExp(`(${phrases.map(escapeRegExp).join('|')})`, 'gi');
    const parts: { text: string; risky: boolean }[] = [];
    let last = 0;
    for (const match of source.matchAll(pattern)) {
      const at = match.index ?? 0;
      if (at > last) {
        parts.push({ text: source.slice(last, at), risky: false });
      }
      parts.push({ text: match[0], risky: true });
      last = at + match[0].length;
    }
    if (last < source.length) {
      parts.push({ text: source.slice(last), risky: false });
    }
    return parts;
  });

  private readonly submittedText = signal('');

  constructor() {
    this.checkHealth();
    // ข้อความในผลลัพธ์ต้องเปลี่ยนตามภาษาที่เลือก จึงอ่าน signal ภาษาไว้ตรงนี้
    effect(() => {
      this.i18n.language();
    });
  }

  protected statusLabel(): string {
    const map = {
      checking: this.t().statusChecking,
      online: this.t().statusOnline,
      degraded: this.t().statusDegraded,
      offline: this.t().statusOffline,
    };
    return map[this.status()];
  }

  protected levelLabel(): string {
    const data = this.result();
    if (!data) return '';
    return {
      dangerous: this.t().levelDangerous,
      suspicious: this.t().levelSuspicious,
      safe: this.t().levelSafe,
    }[data.risk_level];
  }

  protected recommendation(): string {
    const data = this.result();
    if (!data) return '';
    return {
      dangerous: this.t().recommendDangerous,
      suspicious: this.t().recommendSuspicious,
      safe: this.t().recommendSafe,
    }[data.risk_level];
  }

  protected indicatorLabel(category: string): string {
    // ข้อความอธิบายตัวชี้วัดมาจาก backend เป็นรหัส จึงแปลงเป็นข้อความที่อ่านได้ตรงนี้
    const labels: Record<string, { th: string; en: string }> = {
      urgency: {
        th: 'พบข้อความที่สร้างความเร่งด่วนหรือกดดันให้รีบดำเนินการ',
        en: 'Language that creates urgency or pressure to act quickly',
      },
      credential_request: {
        th: 'พบการขอข้อมูลส่วนบุคคล รหัสผ่าน หรือข้อมูลทางการเงิน',
        en: 'A request for personal data, passwords or financial details',
      },
      authority: {
        th: 'พบการอ้างถึงหน่วยงานหรือบุคคลที่มีอำนาจ',
        en: 'An appeal to an authority or official body',
      },
      reward: {
        th: 'พบการเสนอผลประโยชน์หรือของรางวัล',
        en: 'An offer of a reward or benefit',
      },
      threat: {
        th: 'พบการข่มขู่หรือแจ้งผลเสียหากไม่ดำเนินการ',
        en: 'A threat or warning of consequences if you do not act',
      },
      suspicious_link: {
        th: 'พบลิงก์หรือข้อความชวนให้คลิกลิงก์ ควรตรวจที่อยู่เว็บให้แน่ใจก่อนเปิด',
        en: 'A link or a prompt to click one. Check the address carefully before opening it',
      },
      no_known_terms: {
        th: 'ไม่พบคำที่อยู่ในคลังคำของโมเดลเลย ผลนี้จึงไม่ได้มาจากการวิเคราะห์เนื้อหา ควรตรวจสอบด้วยตนเอง',
        en: 'No words matched the model vocabulary, so this result is not based on content analysis. Please review manually.',
      },
    };
    const found = labels[category];
    return found ? found[this.i18n.language()] : category;
  }

  protected onKeydown(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      this.submit();
    }
  }

  protected insertSample(): void {
    this.text.set(SAMPLE[this.i18n.language()]);
    this.submit();
  }

  protected clear(): void {
    this.text.set('');
    this.result.set(null);
    this.submittedText.set('');
    this.formError.set('');
  }

  protected submit(): void {
    const body = this.text().trim();
    this.formError.set('');

    if (!body) {
      this.formError.set(this.t().emptyInput);
      return;
    }
    if (body.length > MAX_LENGTH) {
      this.formError.set(this.t().tooLong);
      return;
    }

    this.loading.set(true);
    this.api.analyze({ body_content: body }).pipe(timeout(ANALYZE_TIMEOUT_MS)).subscribe({
      next: (data) => {
        this.result.set(data);
        this.submittedText.set(body);
        this.loading.set(false);
        // ตอบกลับได้แปลว่าเซิร์ฟเวอร์ใช้งานได้ ไม่ต้องยิงเช็คสถานะซ้ำ (ประหยัด 1 รอบบนเน็ตช้า)
        this.status.set('online');
      },
      error: (err: unknown) => {
        const slow = err instanceof TimeoutError;
        const limited = err instanceof HttpErrorResponse && err.status === 429;
        this.formError.set(slow ? this.t().errorTimeout : limited ? this.t().errorTooMany : this.t().errorNetwork);
        this.loading.set(false);
        this.checkHealth();
      },
    });
  }

  private checkHealth(): void {
    this.status.set('checking');
    this.api.health().subscribe({
      next: (body) => this.status.set(body.status === 'ok' ? 'online' : 'degraded'),
      error: () => this.status.set('offline'),
    });
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { I18nService } from '../core/i18n.service';
import { ShieldIcon } from '../shared/shield-icon';

interface SampleRow {
  sender: string;
  subject: { th: string; en: string };
  risk: number;
  level: 'high' | 'medium' | 'safe';
  lang: 'th' | 'en';
  ms: string;
  time: string;
}

/**
 * หน้าภาพรวมผู้ดูแล — เป็นแบบร่าง
 *
 * ตัวเลขและรายการทั้งหมดเป็นข้อมูลตัวอย่าง ยังไม่ได้ดึงจาก GET /api/v1/stats
 * ซึ่งต้องส่ง header X-Admin-Token
 */
@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, ShieldIcon],
  templateUrl: './dashboard.html',
  host: { class: 'app-host' },
})
export class Dashboard {
  protected readonly i18n = inject(I18nService);
  protected readonly t = this.i18n.t;

  protected readonly rows: SampleRow[] = [
    {
      sender: 'support@it-verify-secure.com',
      subject: { th: 'ด่วน! บัญชีของคุณจะถูกระงับภายใน 24 ชั่วโมง', en: 'Urgent: your account will be suspended in 24 hours' },
      risk: 97.4, level: 'high', lang: 'th', ms: '6.7', time: '09:42',
    },
    {
      sender: 'payroll@hr-notice-center.net',
      subject: { th: 'สลิปเงินเดือนเดือนมีนาคมพร้อมให้ดาวน์โหลด', en: 'Your March payslip is ready to download' },
      risk: 91.2, level: 'high', lang: 'en', ms: '6.3', time: '09:10',
    },
    {
      sender: 'no-reply@shared-docs-cloud.co',
      subject: { th: 'มีเอกสาร "งบประมาณ Q2" แชร์ถึงคุณ', en: 'A document "Q2 Budget" was shared with you' },
      risk: 43.8, level: 'medium', lang: 'th', ms: '7.1', time: '08:55',
    },
    {
      sender: 'billing@invoice-settle.biz',
      subject: { th: 'ใบแจ้งหนี้ค้างชำระ #INV-40912 แจ้งเตือนครั้งสุดท้าย', en: 'Overdue invoice #INV-40912 — final notice' },
      risk: 36.5, level: 'medium', lang: 'en', ms: '6.9', time: '08:31',
    },
    {
      sender: 'notifications@github.com',
      subject: { th: '[phishmail/api] ตรวจผ่าน 2 รายการบน main', en: '[phishmail/api] 2 checks passed on main' },
      risk: 0.1, level: 'safe', lang: 'en', ms: '5.9', time: '08:04',
    },
    {
      sender: 'hr@yourcompany.co.th',
      subject: { th: 'แจ้งเตือน: อบรมความปลอดภัยไซเบอร์ วันศุกร์นี้', en: 'Reminder: cyber security training this Friday' },
      risk: 2.3, level: 'safe', lang: 'th', ms: '6.1', time: '07:48',
    },
  ];

  protected subjectOf(row: SampleRow): string {
    return row.subject[this.i18n.language()];
  }

  protected langLabel(row: SampleRow): string {
    return row.lang === 'th' ? this.t().langTh : this.t().langEn;
  }
}

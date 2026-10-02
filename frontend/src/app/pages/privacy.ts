import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { I18nService } from '../core/i18n.service';
import { SiteFooter } from '../shared/site-footer';
import { SiteNav } from '../shared/site-nav';

/**
 * ต้องตรงกับ PRIVACY_POLICY_VERSION ใน backend/app/config.py
 * แก้เนื้อหาหน้านี้เมื่อใด ให้เปลี่ยนทั้งสองที่ เพื่อให้บันทึกความยินยอมบอกได้ว่าผู้ใช้ยอมรับฉบับไหน
 */
const POLICY_VERSION = '2026-10-02';

interface Section {
  title: string;
  items: string[];
}

const CONTENT: Record<'th' | 'en', { title: string; intro: string; sections: Section[] }> = {
  th: {
    title: 'นโยบายความเป็นส่วนตัว',
    intro:
      'PhishMail เก็บข้อมูลเท่าที่จำเป็นต่อการให้บริการเท่านั้น การตรวจสอบอีเมลใช้ได้โดยไม่ต้องสมัครสมาชิก ' +
      'บัญชีผู้ใช้เป็นทางเลือก',
    sections: [
      {
        title: '1. ข้อมูลที่เก็บเมื่อสมัครสมาชิก',
        items: [
          'อีเมล: เข้ารหัสก่อนบันทึก และเก็บค่าแฮชแบบมีกุญแจ (HMAC-SHA256) ไว้ใช้ค้นหาตอนเข้าสู่ระบบ ฐานข้อมูลไม่มีอีเมลของคุณเป็นข้อความธรรมดา',
          'รหัสผ่าน: เก็บเฉพาะค่าแฮช scrypt ที่มี salt สุ่มต่อบัญชี ไม่มีใครดูรหัสผ่านจริงของคุณได้ รวมถึงผู้ดูแลระบบ',
          'บันทึกความยินยอม: ฉบับของนโยบายนี้ที่คุณยอมรับ และเวลาที่ยอมรับ',
          'วันเวลาที่สมัคร',
          'การเข้าสู่ระบบ: เก็บเฉพาะค่าแฮชของรหัสเข้าใช้งาน (token) และวันหมดอายุ ถูกลบเมื่อออกจากระบบหรือหมดอายุ',
          'ถ้าคุณเข้าสู่ระบบด้วยบัญชี Google จะเก็บเพิ่มเพียงวันเวลาที่ยืนยันอีเมลกับ Google',
        ],
      },
      {
        title: '2. การเข้าสู่ระบบด้วยบัญชี Google (ถ้าเปิดใช้)',
        items: [
          'หน้านี้จะโหลดสคริปต์ของ Google จาก accounts.google.com เมื่อผู้ดูแลเปิดใช้ช่องทางนี้ Google จึงทราบว่าคุณเปิดหน้าเข้าสู่ระบบ ถ้าไม่ได้เปิดใช้ ระบบจะไม่ติดต่อ Google เลย',
          'ระบบใช้เฉพาะอีเมลที่ Google ยืนยันแล้ว ไม่เก็บชื่อ รูปโปรไฟล์ หรือรหัสผู้ใช้ของ Google',
          'ระบบไม่ขอสิทธิ์เข้าถึงกล่องจดหมาย ปฏิทิน หรือข้อมูลอื่นใดในบัญชี Google และไม่เก็บ token ของ Google ไว้',
          'ถ้าอีเมลนั้นมีบัญชีที่ใช้รหัสผ่านอยู่แล้ว ระบบจะขอรหัสผ่านเดิมหนึ่งครั้งก่อนผูกบัญชี เพื่อไม่ให้ผู้ที่สมัครอีเมลของคุณไว้ก่อนเข้าถึงบัญชีได้',
        ],
      },
      {
        title: '3. ข้อมูลที่ไม่เก็บ',
        items: [
          'ชื่อ นามสกุล เบอร์โทรศัพท์ หรือข้อมูลติดต่ออื่น',
          'ที่อยู่ IP (ตัวจำกัดจำนวนคำขอใช้ค่าแฮชของ IP ในหน่วยความจำเท่านั้น ไม่บันทึกลงฐานข้อมูล)',
          'ประวัติการตรวจอีเมลของคุณ ผลการตรวจทุกครั้งไม่ผูกกับบัญชี ระบบจึงบอกไม่ได้ว่าใครตรวจอีเมลฉบับใด',
        ],
      },
      {
        title: '4. การตรวจสอบอีเมล',
        items: [
          'ค่าเริ่มต้นไม่เก็บเนื้อหาอีเมล เก็บเพียงค่าแฮชแบบมีกุญแจของเนื้อหาและผลการตรวจ',
          'ข้อมูลการตรวจถูกลบอัตโนมัติเมื่อครบ 90 วัน',
        ],
      },
      {
        title: '5. ข้อมูลที่เก็บในเบราว์เซอร์ของคุณ',
        items: [
          'รหัสเข้าใช้งานเก็บใน sessionStorage และหายไปเมื่อปิดแท็บ ถ้าเลือก "จดจำการเข้าสู่ระบบ" จะเก็บใน localStorage 30 วัน',
          'ภาษาที่เลือกใช้งาน',
        ],
      },
      {
        title: '6. สิทธิ์ของคุณ',
        items: [
          'ดูข้อมูลทั้งหมดที่ระบบเก็บเกี่ยวกับบัญชีของคุณได้ที่หน้า "บัญชีของฉัน"',
          'ลบบัญชีได้เองทุกเมื่อ ข้อมูลทุกแถวของบัญชีถูกลบจากฐานข้อมูลทันที ไม่มีการเก็บสำเนา',
          'บัญชีที่สร้างด้วย Google ลบได้เช่นกัน โดยยืนยันด้วยการเข้าสู่ระบบ Google อีกครั้งแทนรหัสผ่าน',
          'ถอนความยินยอมได้ด้วยการลบบัญชี',
          'ติดต่อสอบถามผ่าน GitHub repository ของโครงงาน',
        ],
      },
      {
        title: '7. ความปลอดภัย',
        items: [
          'จำกัดจำนวนครั้งการเข้าสู่ระบบต่อนาที เพื่อกันการสุ่มเดารหัสผ่าน',
          'เข้าสู่ระบบไม่สำเร็จจะได้ข้อความเดียวกันเสมอ ไม่บอกว่าอีเมลใดมีบัญชี',
          'ข้อมูลไม่ถูกขาย ไม่ถูกให้เช่า และไม่ถูกใช้เพื่อการโฆษณา',
        ],
      },
    ],
  },
  en: {
    title: 'Privacy policy',
    intro:
      'PhishMail stores only what it needs to provide the service. You can check emails without an account; ' +
      'signing up is optional.',
    sections: [
      {
        title: '1. What we store when you sign up',
        items: [
          'Email: encrypted before it is saved, plus a keyed hash (HMAC-SHA256) used to find your account at login. The database never holds your email in plain text.',
          'Password: only a scrypt hash with a random per-account salt. Nobody can read your actual password, including administrators.',
          'Consent record: which version of this policy you accepted, and when.',
          'The date and time you signed up.',
          'Logins: only a hash of your access token and its expiry. Removed when you log out or it expires.',
          'If you sign in with Google, the only extra item stored is the time your email was verified with Google.',
        ],
      },
      {
        title: '2. Signing in with Google (if enabled)',
        items: [
          "When an administrator enables this option, the page loads Google's script from accounts.google.com, so Google learns that you opened the login page. If it is not enabled, the system never contacts Google at all.",
          'The system uses only the email address Google has verified. It does not store your name, profile picture, or Google user id.',
          'The system requests no access to your mail, calendar, or any other data in your Google account, and stores no Google tokens.',
          'If that email already has a password account, the system asks for the existing password once before linking them, so someone who registered your email beforehand cannot gain access.',
        ],
      },
      {
        title: '3. What we do not store',
        items: [
          'Your name, phone number, or any other contact details.',
          'Your IP address (the rate limiter keeps a hash of it in memory only, never in the database).',
          'Your scan history. Scan results are never linked to an account, so the system cannot tell who checked which email.',
        ],
      },
      {
        title: '4. Checking emails',
        items: [
          'By default the email content is not stored, only a keyed hash of it and the result.',
          'Scan data is deleted automatically after 90 days.',
        ],
      },
      {
        title: '5. What is kept in your browser',
        items: [
          'Your access token, in sessionStorage, cleared when you close the tab. With "Keep me logged in" it is kept in localStorage for 30 days.',
          'Your language preference.',
        ],
      },
      {
        title: '6. Your rights',
        items: [
          'See everything stored about your account on the "My account" page.',
          'Delete your account yourself at any time. Every row belonging to it is removed from the database immediately, with no copies kept.',
          'Accounts created with Google can be deleted too, confirming with another Google sign-in instead of a password.',
          'Withdraw consent by deleting your account.',
          "Contact us through the project's GitHub repository.",
        ],
      },
      {
        title: '7. Security',
        items: [
          'Login attempts are rate limited per minute to prevent password guessing.',
          'A failed login always shows the same message, so it never reveals which emails have accounts.',
          'Data is never sold, rented, or used for advertising.',
        ],
      },
    ],
  },
};

@Component({
  selector: 'app-privacy',
  imports: [RouterLink, SiteNav, SiteFooter],
  template: `
    <app-site-nav />

    <main class="account-page">
      <div class="container narrow">
        <h1>{{ content().title }}</h1>
        <p class="mono policy-version">{{ t().privacyVersion }} {{ version }}</p>
        <p class="lead">{{ content().intro }}</p>

        @for (section of content().sections; track section.title) {
          <section class="policy-section">
            <h2>{{ section.title }}</h2>
            <ul>
              @for (item of section.items; track item) {
                <li>{{ item }}</li>
              }
            </ul>
          </section>
        }

        <p><a routerLink="/account">{{ t().navAccount }}</a></p>
      </div>
    </main>

    <app-site-footer />
  `,
})
export class Privacy {
  private readonly i18n = inject(I18nService);
  protected readonly t = this.i18n.t;
  protected readonly version = POLICY_VERSION;
  protected readonly content = computed(() => CONTENT[this.i18n.language()]);
}

import { Injectable, computed, effect, signal } from '@angular/core';

import { Language } from './models';

const STORAGE_KEY = 'ui_language';

/**
 * ข้อความทั้งหมดของหน้าเว็บ ไทยและอังกฤษ
 *
 * โครงงานรองรับสองภาษานี้เท่านั้น ห้ามเพิ่มภาษาอื่น
 * ใช้วิธีสลับตอนรัน (runtime) ไม่ใช่ i18n แบบ build-time ของ Angular
 * เพราะผู้ใช้ต้องกดสลับภาษาได้ทันทีโดยไม่ต้องโหลดหน้าใหม่
 */
const TEXT = {
  th: {
    // ส่วนที่ใช้ร่วมกัน
    brand: 'PhishMail',
    navHowItWorks: 'วิธีทำงาน',
    navFeatures: 'ความสามารถ',
    navChannels: 'ช่องทางใช้งาน',
    navScan: 'ตรวจสอบอีเมล',
    navDashboard: 'ภาพรวม',
    navLogin: 'เข้าสู่ระบบ',
    navHome: 'หน้าแรก',
    footerNote: 'ปริญญานิพนธ์ · ระบบตรวจจับอีเมลฟิชชิงโดยใช้การประมวลผลภาษาธรรมชาติ',
    langToggle: 'EN',

    // หน้าแรก
    heroEyebrow: 'ระบบตรวจจับอีเมลฟิชชิง · ไทย / อังกฤษ',
    heroTitle: 'รู้ว่าอีเมลนี้ฟิชชิง ก่อนจะกดลิงก์',
    heroSub:
      'PhishMail ตัดคำและวิเคราะห์เนื้อหาอีเมลด้วยการประมวลผลภาษาธรรมชาติ ' +
      'แล้วให้คะแนนความเสี่ยงพร้อมไฮไลต์คำที่น่าสงสัย — ใช้ได้ทั้งการวางข้อความบนหน้าเว็บ ' +
      'และตรวจอัตโนมัติใน Gmail ผ่านส่วนขยาย Chrome',
    heroCtaSee: 'ดูตัวอย่างผลวิเคราะห์',
    heroNote: 'ไม่ต้องสมัครสมาชิกหรือเข้าสู่ระบบ — เปิดหน้าตรวจสอบแล้ววางข้อความได้ทันที',
    builtWith: 'พัฒนาด้วย',

    howTitle: 'จากข้อความอีเมล สู่คะแนนความเสี่ยง',
    howSub: 'ทั้งหน้าเว็บและส่วนขยาย Chrome เรียก API ตัวเดียวกัน จึงได้ผลลัพธ์ตรงกัน',
    how1Title: 'ตัดคำและทำความสะอาด',
    how1Body:
      'กำจัดข้อมูลขยะ แล้วตัดคำด้วย PyThaiNLP (newmm) ร่วมกับคลังคำที่สร้างเพิ่ม ' +
      'และลบคำหยุด ก่อนตรวจว่าอีเมลเป็นภาษาไทยหรืออังกฤษ',
    how2Title: 'คำนวณด้วยโมเดลของแต่ละภาษา',
    how2Body:
      'แปลงเป็นเวกเตอร์ TF-IDF แล้วทำนายด้วย Naive Bayes ที่เทรนแยกภาษาไทย/อังกฤษ ' +
      'หากพบหลายภาษาในอีเมลเดียว ระบบจะเลือกค่าความเสี่ยงสูงสุด',
    how3Title: 'สรุปผลและบันทึกล็อก',
    how3Body:
      'แสดงเปอร์เซ็นต์ความเสี่ยง 3 ระดับ พร้อมไฮไลต์คำเสี่ยงและคำแนะนำ ' +
      'จากนั้นบันทึกผลการตรวจลงฐานข้อมูล',

    featTitle: 'สิ่งที่ระบบทำได้',
    featSub: 'ทุกผลลัพธ์แสดงเหตุผลประกอบ ผู้ใช้จึงตรวจสอบย้อนกลับได้ว่าทำไมอีเมลนี้จึงถูกจัดว่าเสี่ยง',
    feat1Title: 'รองรับสองภาษา ไทยและอังกฤษ',
    feat1Body:
      'ตรวจภาษาของอีเมลอัตโนมัติแล้วเลือกโมเดลที่ตรงกัน ภาษาไทยตัดคำด้วย PyThaiNLP ' +
      'พร้อมคลังคำและคำหยุดที่ปรับสำหรับบริบทอีเมลฟิชชิงโดยเฉพาะ',
    feat2Title: 'ไฮไลต์คำเสี่ยงในเนื้อหา',
    feat2Body:
      'แสดงเนื้อหาอีเมลพร้อมทำเครื่องหมายคำและวลีที่ทำให้คะแนนความเสี่ยงสูงขึ้น ' +
      'ระบุประเภทของสิ่งที่ตรวจพบ เช่น การกดดันด้านเวลา หรือการขอข้อมูลส่วนตัว',
    feat3Title: 'ตรวจอัตโนมัติใน Gmail',
    feat3Body:
      'ส่วนขยาย Chrome อ่านอีเมลที่เปิดอยู่แล้วแสดงป้ายระดับความเสี่ยงมุมขวาล่าง ' +
      'แดงตั้งแต่ 50% เหลืองตั้งแต่ 30% เขียวคือปกติ — ขออนุญาตผู้ใช้ก่อนเริ่มทำงานครั้งแรก',
    feat4Title: 'เก็บล็อกแบบเข้ารหัส',
    feat4Body:
      'ค่าเริ่มต้นไม่เก็บเนื้อหาอีเมล และหากเปิดให้เก็บ เนื้อหาจะถูกเข้ารหัสก่อนบันทึกเสมอ ' +
      'พร้อมลบข้อมูลอัตโนมัติเมื่อครบกำหนด',

    ctaTitle: 'ลองวางอีเมลที่สงสัยดูได้เลย',
    ctaSub: 'ไม่ต้องสมัครสมาชิก ไม่ต้องตั้งค่า วางข้อความแล้วดูว่าระบบให้คะแนนความเสี่ยงเท่าไร',

    // หน้าตรวจสอบ
    scanEyebrow: 'ตรวจสอบอีเมล',
    scanTitle: 'ตรวจสอบอีเมลฟิชชิง',
    scanLead:
      'วางเนื้อหาอีเมลที่ต้องการตรวจสอบลงในช่องด้านล่าง แล้วกดปุ่มตรวจสอบ ' +
      'ระบบจะวิเคราะห์ด้วยโมเดลการเรียนรู้ของเครื่องและแสดงระดับความเสี่ยงพร้อมคำที่น่าสงสัย',
    placeholder: 'วางหัวข้อและเนื้อหาอีเมลที่นี่...',
    inputLabel: 'เนื้อหาอีเมล',
    analyze: 'ตรวจสอบอีเมล',
    analyzing: 'กำลังวิเคราะห์...',
    sample: 'ใส่ตัวอย่างอีเมล',
    clear: 'ล้างข้อความ',
    shortcut: 'กด Ctrl + Enter เพื่อตรวจสอบ',
    emptyInput: 'กรุณาวางเนื้อหาอีเมลก่อนกดตรวจสอบ',
    tooLong: 'เนื้อหายาวเกิน 100,000 ตัวอักษร กรุณาตัดให้สั้นลง',
    errorNetwork: 'เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ กรุณาลองใหม่อีกครั้ง',
    statusChecking: 'กำลังตรวจสอบสถานะ',
    statusOnline: 'ระบบพร้อมใช้งาน',
    statusDegraded: 'ระบบทำงานได้บางส่วน',
    statusOffline: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้',
    levelDangerous: 'อันตราย — เข้าข่ายอีเมลฟิชชิง',
    levelSuspicious: 'มีโอกาสเสี่ยง — ควรตรวจสอบเพิ่มเติม',
    levelSafe: 'ไม่พบสัญญาณอันตราย',
    recommendDangerous: 'อย่าคลิกลิงก์ อย่ากรอกข้อมูลส่วนตัว และอย่าตอบกลับอีเมลฉบับนี้',
    recommendSuspicious: 'ตรวจสอบผู้ส่งให้แน่ใจก่อนดำเนินการใด ๆ กับอีเมลฉบับนี้',
    recommendSafe: 'ไม่พบสัญญาณที่บ่งชี้ว่าเป็นฟิชชิง แต่ควรระมัดระวังเสมอ',
    factClassification: 'ประเภท',
    factLanguage: 'ภาษา',
    factTime: 'เวลาประมวลผล',
    classPhishing: 'อีเมลฟิชชิง',
    classLegitimate: 'อีเมลปกติ',
    langTh: 'ภาษาไทย',
    langEn: 'ภาษาอังกฤษ',
    detailsTitle: 'รายละเอียดการวิเคราะห์',
    detailNoIndicator: 'ไม่พบรูปแบบการหลอกลวงที่ระบบรู้จัก',
    highlightTitle: 'เนื้อหาอีเมลพร้อมคำที่น่าสงสัย',
    caution: 'ผลการวิเคราะห์เป็นเพียงการประเมินด้วยแบบจำลอง ควรใช้วิจารณญาณประกอบเสมอ',

    // หน้าภาพรวม
    dashTitle: 'ภาพรวม',
    dashSample: 'ข้อมูลตัวอย่าง',
    dashSearch: 'ค้นหาผู้ส่งหรือหัวข้อ',
    dashScanned: 'ตรวจสอบทั้งหมด',
    dashPhishing: 'พบว่าเป็นฟิชชิง',
    dashSuspicious: 'น่าสงสัย',
    dashAvgTime: 'เวลาประมวลผลเฉลี่ย',
    dashRecent: 'ผลการตรวจสอบล่าสุด',
    dashLast24: '24 ชั่วโมงที่ผ่านมา',
    colSender: 'ผู้ส่ง',
    colSubject: 'หัวข้อ',
    colRisk: 'ความเสี่ยง',
    colLang: 'ภาษา',
    colProcess: 'ประมวลผล',
    colTime: 'เวลา',
    colDetail: 'ดูรายละเอียด',
    dashNote:
      'หน้านี้เป็นแบบร่างของหน้าจอผู้ดูแล ตัวเลขและรายการทั้งหมดเป็นข้อมูลตัวอย่าง ' +
      'ยังไม่ได้ดึงจาก API สถิติซึ่งต้องใช้สิทธิ์ผู้ดูแล',
    navHistory: 'ประวัติการตรวจสอบ',
    navTerms: 'คำเสี่ยงที่พบบ่อย',
    navModel: 'โมเดลที่ใช้งาน',
    navSettings: 'ตั้งค่า',
    backToSite: 'กลับไปหน้าแรก',

    // หน้าเข้าสู่ระบบ
    loginDraft: 'แบบร่าง · ยังไม่เปิดใช้งาน',
    loginTitle: 'เข้าสู่ระบบ',
    loginSub:
      'ส่วนนี้เป็นแบบร่างของหน้าจอเข้าสู่ระบบสำหรับผู้ดูแล ยังไม่ได้เชื่อมต่อกับระบบยืนยันตัวตนจริง ' +
      'การตรวจสอบอีเมลไม่จำเป็นต้องเข้าสู่ระบบ',
    loginEmail: 'อีเมล',
    loginPassword: 'รหัสผ่าน',
    loginRemember: 'จดจำการเข้าสู่ระบบ',
    loginForgot: 'ลืมรหัสผ่าน',
    loginOr: 'หรือ',
    loginSkip: 'ใช้งานโดยไม่เข้าสู่ระบบ',
    loginBack: 'กลับไปหน้าแรก',
    loginNotWired:
      'หน้านี้เป็นแบบร่าง ยังไม่ได้เชื่อมต่อระบบยืนยันตัวตน — ใช้ปุ่มด้านล่างเพื่อเข้าใช้งานได้เลย',
  },

  en: {
    brand: 'PhishMail',
    navHowItWorks: 'How it works',
    navFeatures: 'Features',
    navChannels: 'Ways to use',
    navScan: 'Scan an email',
    navDashboard: 'Overview',
    navLogin: 'Log in',
    navHome: 'Home',
    footerNote: 'Undergraduate thesis · Phishing email detection using natural language processing',
    langToggle: 'ไทย',

    heroEyebrow: 'Phishing email detection · Thai / English',
    heroTitle: 'Know it is phishing before you click.',
    heroSub:
      'PhishMail tokenises and analyses email content with natural language processing, ' +
      'then returns a risk score with the suspicious wording highlighted — either by pasting ' +
      'text on this site, or automatically inside Gmail through the Chrome extension.',
    heroCtaSee: 'See a sample result',
    heroNote: 'No sign-up and no login needed — open the scan page and paste your text.',
    builtWith: 'Built with',

    howTitle: 'From email text to a risk score',
    howSub: 'The website and the Chrome extension call the same API, so results always match.',
    how1Title: 'Clean and tokenise',
    how1Body:
      'Strip noise, then tokenise with PyThaiNLP (newmm) together with a custom dictionary, ' +
      'remove stop words, and detect whether the email is Thai or English.',
    how2Title: 'Score with the per-language model',
    how2Body:
      'Convert to a TF-IDF vector and predict with a Naive Bayes model trained separately for ' +
      'Thai and English. If several languages appear, the highest risk score is used.',
    how3Title: 'Report and log',
    how3Body:
      'Show the risk percentage across three levels, highlight the risky wording with advice, ' +
      'then record the detection result in the database.',

    featTitle: 'What the system does',
    featSub: 'Every verdict shows its reasoning, so you can check why an email was flagged.',
    feat1Title: 'Thai and English',
    feat1Body:
      'Detects the email language automatically and picks the matching model. Thai is tokenised ' +
      'with PyThaiNLP plus a dictionary and stop-word list tuned for phishing wording.',
    feat2Title: 'Risky wording highlighted',
    feat2Body:
      'Shows the email with the words and phrases that raised the risk score marked, and names ' +
      'what was detected, such as time pressure or requests for personal information.',
    feat3Title: 'Automatic checks in Gmail',
    feat3Body:
      'The Chrome extension reads the open email and shows a risk badge in the corner: red from ' +
      '50%, amber from 30%, green otherwise — after asking the user for consent on first use.',
    feat4Title: 'Encrypted logging',
    feat4Body:
      'Email content is not stored by default, and when storage is enabled the content is always ' +
      'encrypted before being written, with automatic deletion once the retention period passes.',

    ctaTitle: 'Try it with an email you are unsure about',
    ctaSub: 'No sign-up, no configuration. Paste the text and see the risk score.',

    scanEyebrow: 'Scan an email',
    scanTitle: 'Phishing email check',
    scanLead:
      'Paste the email you want to check into the box below and press the button. The system ' +
      'analyses it with a machine learning model and shows the risk level and suspicious wording.',
    placeholder: 'Paste the email subject and body here...',
    inputLabel: 'Email content',
    analyze: 'Check this email',
    analyzing: 'Analysing...',
    sample: 'Insert a sample email',
    clear: 'Clear',
    shortcut: 'Press Ctrl + Enter to check',
    emptyInput: 'Please paste the email content before checking.',
    tooLong: 'The content is longer than 100,000 characters. Please shorten it.',
    errorNetwork: 'Could not reach the server. Please try again.',
    statusChecking: 'Checking status',
    statusOnline: 'System ready',
    statusDegraded: 'Partially available',
    statusOffline: 'Cannot reach the server',
    levelDangerous: 'Dangerous — consistent with phishing',
    levelSuspicious: 'Possibly risky — worth a closer look',
    levelSafe: 'No signs of danger found',
    recommendDangerous: 'Do not click any link, do not enter personal data, and do not reply.',
    recommendSuspicious: 'Verify the sender before acting on anything in this email.',
    recommendSafe: 'No phishing signals found, but stay cautious as always.',
    factClassification: 'Classification',
    factLanguage: 'Language',
    factTime: 'Processing time',
    classPhishing: 'Phishing email',
    classLegitimate: 'Legitimate email',
    langTh: 'Thai',
    langEn: 'English',
    detailsTitle: 'Analysis detail',
    detailNoIndicator: 'No known deception pattern was found.',
    highlightTitle: 'Email content with suspicious wording',
    caution: 'This result is a model estimate. Always apply your own judgement as well.',

    dashTitle: 'Overview',
    dashSample: 'Sample data',
    dashSearch: 'Search sender or subject',
    dashScanned: 'Total checked',
    dashPhishing: 'Found phishing',
    dashSuspicious: 'Suspicious',
    dashAvgTime: 'Average processing time',
    dashRecent: 'Recent results',
    dashLast24: 'Last 24 hours',
    colSender: 'Sender',
    colSubject: 'Subject',
    colRisk: 'Risk',
    colLang: 'Language',
    colProcess: 'Processing',
    colTime: 'Time',
    colDetail: 'View detail',
    dashNote:
      'This is a draft of the administrator screen. All figures and rows are sample data and are ' +
      'not yet read from the statistics API, which requires administrator access.',
    navHistory: 'Detection history',
    navTerms: 'Frequent risky terms',
    navModel: 'Active model',
    navSettings: 'Settings',
    backToSite: 'Back to site',

    loginDraft: 'Draft · not enabled',
    loginTitle: 'Log in',
    loginSub:
      'This is a draft of the administrator login screen. It is not connected to a real ' +
      'authentication system. Checking an email does not require logging in.',
    loginEmail: 'Email',
    loginPassword: 'Password',
    loginRemember: 'Remember me',
    loginForgot: 'Forgot password',
    loginOr: 'or',
    loginSkip: 'Continue without logging in',
    loginBack: 'Back to home',
    loginNotWired:
      'This page is a draft and is not connected to an authentication system — use the button below to continue.',
  },
} as const;

export type TextKey = keyof (typeof TEXT)['th'];

@Injectable({ providedIn: 'root' })
export class I18nService {
  /** ภาษาที่ใช้อยู่ เริ่มจากค่าที่เคยเลือกไว้ ถ้าไม่มีจึงดูจากภาษาของเบราว์เซอร์ */
  readonly language = signal<Language>(readInitialLanguage());

  /** ตารางข้อความของภาษาปัจจุบัน ใช้ในเทมเพลตเป็น t().someKey */
  readonly t = computed(() => TEXT[this.language()]);

  constructor() {
    effect(() => {
      const lang = this.language();
      document.documentElement.lang = lang;
      try {
        localStorage.setItem(STORAGE_KEY, lang);
      } catch {
        // โหมดส่วนตัวหรือปิดการเก็บข้อมูลไว้ — ไม่ใช่เรื่องร้ายแรง แค่จำภาษาไม่ได้
      }
    });
  }

  toggle(): void {
    this.language.update((current) => (current === 'th' ? 'en' : 'th'));
  }
}

function readInitialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'th' || saved === 'en') {
      return saved;
    }
  } catch {
    // อ่านไม่ได้ก็ถือว่ายังไม่เคยเลือก
  }
  return (navigator.language || '').toLowerCase().startsWith('th') ? 'th' : 'en';
}

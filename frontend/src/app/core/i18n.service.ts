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
    dashScanned: 'ตรวจสอบทั้งหมด',
    dashPhishing: 'อันตราย',
    dashSuspicious: 'มีโอกาสเสี่ยง',
    dashSafe: 'ปลอดภัย',
    dashRecent: 'ผลการตรวจสอบล่าสุด',
    dashRecentCount: 'ล่าสุด {n} รายการ',
    dashEmpty: 'ยังไม่มีการตรวจสอบ ลองตรวจอีเมลที่หน้า "ตรวจสอบอีเมล" แล้วกดรีเฟรช',
    dashModels: 'โมเดลที่บันทึกในฐานข้อมูล',
    dashRefresh: 'รีเฟรช',
    dashUpdated: 'อัปเดตเมื่อ',
    dashLoading: 'กำลังโหลดข้อมูล...',
    dashTokenTitle: 'ต้องใช้สิทธิ์ผู้ดูแล',
    dashTokenSub:
      'ข้อมูลสถิติเปิดให้เฉพาะผู้ดูแลระบบ กรอกค่า ADMIN_TOKEN จากไฟล์ backend/.env ' +
      'ระบบเก็บค่านี้ไว้ในแท็บนี้เท่านั้น ปิดแท็บแล้วต้องกรอกใหม่',
    dashTokenLabel: 'Admin token',
    dashTokenSubmit: 'ดูข้อมูล',
    dashTokenForget: 'ล้าง token',
    dashErrWrongToken: 'Admin token ไม่ถูกต้อง',
    dashErrDisabled: 'ปิดใช้งานอยู่ ต้องตั้งค่า ADMIN_TOKEN ใน backend/.env ก่อน',
    dashErrOffline: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้',
    dashErrUnknown: 'โหลดข้อมูลไม่สำเร็จ',
    colRisk: 'ความเสี่ยง',
    colLevel: 'ระดับ',
    colLang: 'ภาษา',
    colTime: 'เวลา',
    colModel: 'โมเดล',
    colAlgorithm: 'อัลกอริทึม',
    colAccuracy: 'ความแม่นยำ',
    colTrainDate: 'วันที่เทรน',
    dashNote:
      'ระบบไม่เก็บผู้ส่ง หัวข้อ หรือเนื้อหาอีเมล ตารางจึงแสดงได้เพียงเวลา ความเสี่ยง และภาษา ' +
      'ความแม่นยำของโมเดลคือค่าจากชุดทดสอบตอนเทรน',
    navHistory: 'ประวัติการตรวจสอบ',
    navModel: 'โมเดลที่ใช้งาน',
    backToSite: 'กลับไปหน้าแรก',

    // หน้าเข้าสู่ระบบ
    navAccount: 'บัญชีของฉัน',
    loginTitle: 'เข้าสู่ระบบ',
    loginSub: 'เข้าสู่ระบบเพื่อจัดการบัญชีของคุณ การตรวจสอบอีเมลไม่จำเป็นต้องเข้าสู่ระบบ',
    loginEmail: 'อีเมล',
    loginPassword: 'รหัสผ่าน',
    loginRemember: 'จดจำการเข้าสู่ระบบ 30 วัน',
    loginOr: 'หรือ',
    loginSkip: 'ใช้งานโดยไม่เข้าสู่ระบบ',
    loginBack: 'กลับไปหน้าแรก',
    loginNoAccount: 'ยังไม่มีบัญชี?',
    loginWorking: 'กำลังตรวจสอบ...',

    // หน้าสมัครสมาชิก
    registerTitle: 'สมัครสมาชิก',
    registerSub: 'ระบบเก็บเพียงอีเมลและรหัสผ่านของคุณ ไม่ขอชื่อ เบอร์โทรศัพท์ หรือข้อมูลอื่น',
    registerPasswordHint: 'อย่างน้อย 8 ตัวอักษร',
    registerConfirm: 'ยืนยันรหัสผ่าน',
    registerConsentPre: 'ฉันได้อ่านและยอมรับ',
    registerConsentLink: 'นโยบายความเป็นส่วนตัว',
    registerHaveAccount: 'มีบัญชีอยู่แล้ว?',
    registerWorking: 'กำลังสมัคร...',

    // ข้อผิดพลาดของฟอร์มบัญชี
    authErrRequired: 'กรุณากรอกอีเมลและรหัสผ่าน',
    authErrEmail: 'รูปแบบอีเมลไม่ถูกต้อง',
    authErrPasswordShort: 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร',
    authErrPasswordMismatch: 'รหัสผ่านทั้งสองช่องไม่ตรงกัน',
    authErrConsent: 'กรุณายอมรับนโยบายความเป็นส่วนตัวก่อนสมัครสมาชิก',
    authErrInvalid: 'อีเมลหรือรหัสผ่านไม่ถูกต้อง',
    authErrTaken: 'อีเมลนี้สมัครสมาชิกไว้แล้ว ลองเข้าสู่ระบบแทน',
    authErrRejected: 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีเมลและรหัสผ่านอีกครั้ง',
    authErrTooMany: 'ลองหลายครั้งเกินไป กรุณารอสักครู่แล้วลองใหม่',
    authErrOffline: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจสอบว่าระบบทำงานอยู่',
    authErrUnknown: 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง',

    // หน้าบัญชีของฉัน
    accountSub: 'ข้อมูลทั้งหมดที่ระบบเก็บเกี่ยวกับบัญชีของคุณมีเท่าที่แสดงด้านล่างนี้',
    accountEmail: 'อีเมล',
    accountEmailUnavailable: 'ถอดรหัสไม่ได้',
    accountCreated: 'สมัครเมื่อ',
    accountConsent: 'นโยบายความเป็นส่วนตัวที่ยอมรับ',
    accountConsentAt: 'ยอมรับเมื่อ',
    accountNotStored:
      'ระบบไม่เก็บชื่อ เบอร์โทรศัพท์ ที่อยู่ IP และไม่ผูกผลการตรวจอีเมลเข้ากับบัญชีของคุณ',
    accountLogout: 'ออกจากระบบ',
    accountDeleteTitle: 'ลบบัญชี',
    accountDeleteSub: 'ลบบัญชีและข้อมูลทุกอย่างของบัญชีนี้ออกจากฐานข้อมูลทันที ไม่สามารถกู้คืนได้',
    accountDeletePassword: 'ยืนยันด้วยรหัสผ่าน',
    accountDeleteButton: 'ลบบัญชีถาวร',
    accountDeleteWrong: 'รหัสผ่านไม่ถูกต้อง',
    accountDeleted: 'ลบบัญชีเรียบร้อยแล้ว ไม่มีข้อมูลของบัญชีนี้เหลืออยู่ในระบบ',
    accountNeedLogin: 'กรุณาเข้าสู่ระบบเพื่อดูข้อมูลบัญชี',
    accountLoading: 'กำลังโหลดข้อมูลบัญชี...',

    // หน้านโยบายความเป็นส่วนตัว
    navPrivacy: 'นโยบายความเป็นส่วนตัว',
    privacyVersion: 'ฉบับวันที่',
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
    dashScanned: 'Total checked',
    dashPhishing: 'Dangerous',
    dashSuspicious: 'Possibly risky',
    dashSafe: 'Safe',
    dashRecent: 'Recent results',
    dashRecentCount: 'Latest {n}',
    dashEmpty: 'Nothing has been checked yet. Scan an email on the "Scan an email" page, then refresh.',
    dashModels: 'Models recorded in the database',
    dashRefresh: 'Refresh',
    dashUpdated: 'Updated',
    dashLoading: 'Loading...',
    dashTokenTitle: 'Administrator access required',
    dashTokenSub:
      'Statistics are available to administrators only. Enter ADMIN_TOKEN from backend/.env. ' +
      'It is kept in this tab only and must be entered again after the tab is closed.',
    dashTokenLabel: 'Admin token',
    dashTokenSubmit: 'View data',
    dashTokenForget: 'Clear token',
    dashErrWrongToken: 'Incorrect admin token.',
    dashErrDisabled: 'Disabled. Set ADMIN_TOKEN in backend/.env first.',
    dashErrOffline: 'Cannot reach the server.',
    dashErrUnknown: 'Could not load the data.',
    colRisk: 'Risk',
    colLevel: 'Level',
    colLang: 'Language',
    colTime: 'Time',
    colModel: 'Model',
    colAlgorithm: 'Algorithm',
    colAccuracy: 'Accuracy',
    colTrainDate: 'Trained on',
    dashNote:
      'The system does not store senders, subjects, or email content, so the table can only show time, ' +
      'risk, and language. Model accuracy is the test-set value from training.',
    navHistory: 'Detection history',
    navModel: 'Active model',
    backToSite: 'Back to site',

    navAccount: 'My account',
    loginTitle: 'Log in',
    loginSub: 'Log in to manage your account. Checking an email does not require logging in.',
    loginEmail: 'Email',
    loginPassword: 'Password',
    loginRemember: 'Keep me logged in for 30 days',
    loginOr: 'or',
    loginSkip: 'Continue without logging in',
    loginBack: 'Back to home',
    loginNoAccount: 'No account yet?',
    loginWorking: 'Checking...',

    registerTitle: 'Sign up',
    registerSub: 'We only store your email and password. No name, phone number, or anything else.',
    registerPasswordHint: 'At least 8 characters',
    registerConfirm: 'Confirm password',
    registerConsentPre: 'I have read and accept the',
    registerConsentLink: 'privacy policy',
    registerHaveAccount: 'Already have an account?',
    registerWorking: 'Signing up...',

    authErrRequired: 'Please enter your email and password.',
    authErrEmail: 'That email address is not valid.',
    authErrPasswordShort: 'Password must be at least 8 characters.',
    authErrPasswordMismatch: 'The two passwords do not match.',
    authErrConsent: 'Please accept the privacy policy to sign up.',
    authErrInvalid: 'Incorrect email or password.',
    authErrTaken: 'This email is already registered. Try logging in instead.',
    authErrRejected: 'Invalid details. Please check your email and password.',
    authErrTooMany: 'Too many attempts. Please wait a moment and try again.',
    authErrOffline: 'Cannot reach the server. Check that the system is running.',
    authErrUnknown: 'Something went wrong. Please try again.',

    accountSub: 'This is everything the system stores about your account.',
    accountEmail: 'Email',
    accountEmailUnavailable: 'Cannot be decrypted',
    accountCreated: 'Signed up',
    accountConsent: 'Privacy policy accepted',
    accountConsentAt: 'Accepted on',
    accountNotStored:
      'We do not store your name, phone number, or IP address, and scan results are never linked to your account.',
    accountLogout: 'Log out',
    accountDeleteTitle: 'Delete account',
    accountDeleteSub: 'Permanently removes this account and all of its data from the database right away. This cannot be undone.',
    accountDeletePassword: 'Confirm with your password',
    accountDeleteButton: 'Delete account permanently',
    accountDeleteWrong: 'Incorrect password.',
    accountDeleted: 'Your account has been deleted. No data from it remains in the system.',
    accountNeedLogin: 'Please log in to see your account.',
    accountLoading: 'Loading your account...',

    navPrivacy: 'Privacy policy',
    privacyVersion: 'Version',
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

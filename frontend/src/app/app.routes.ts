import { Routes } from '@angular/router';

import { Home } from './pages/home';
import { Scan } from './pages/scan';

/**
 * เส้นทางของหน้าเว็บ
 *
 * หน้าแรกกับหน้าตรวจอีเมลโหลดมาพร้อมไฟล์หลัก เพราะเป็นหน้าที่คนเข้ามาเป็นหน้าแรก
 * ถ้าแยกเป็น lazy chunk เบราว์เซอร์ต้องรอไฟล์หลักเสร็จก่อนจึงรู้ว่าต้องโหลดอะไรต่อ
 * วัดบน Slow 3G ได้ 2 รอบไป-กลับเพิ่ม (ราว 4 วินาที) เพื่อไฟล์รวมแค่ 12 KB ซึ่งไม่คุ้ม
 * หน้าอื่นยังเป็น lazy loading ผู้ใช้ส่วนใหญ่ไม่ได้เปิด จึงไม่ต้องโหลดไปด้วย
 */
export const routes: Routes = [
  { path: '', component: Home, title: 'PhishMail' },
  { path: 'scan', component: Scan, title: 'Scan an email · PhishMail' },
  {
    path: 'dashboard',
    loadComponent: () => import('./pages/dashboard').then((m) => m.Dashboard),
    title: 'Overview · PhishMail',
  },
  {
    path: 'login',
    loadComponent: () => import('./pages/login').then((m) => m.Login),
    title: 'Log in · PhishMail',
  },
  {
    path: 'register',
    loadComponent: () => import('./pages/register').then((m) => m.Register),
    title: 'Sign up · PhishMail',
  },
  {
    path: 'account',
    loadComponent: () => import('./pages/account').then((m) => m.Account),
    title: 'My account · PhishMail',
  },
  {
    path: 'privacy',
    loadComponent: () => import('./pages/privacy').then((m) => m.Privacy),
    title: 'Privacy policy · PhishMail',
  },
  { path: '**', redirectTo: '' },
];

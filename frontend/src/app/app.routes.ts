import { Routes } from '@angular/router';

/**
 * เส้นทางของหน้าเว็บ ใช้ lazy loading ทุกหน้า
 * ผู้ใช้ที่เข้ามาหน้าแรกจึงไม่ต้องโหลดโค้ดของหน้าภาพรวมหรือหน้าเข้าสู่ระบบไปด้วย
 */
export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/home').then((m) => m.Home),
    title: 'PhishMail',
  },
  {
    path: 'scan',
    loadComponent: () => import('./pages/scan').then((m) => m.Scan),
    title: 'Scan an email · PhishMail',
  },
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
  { path: '**', redirectTo: '' },
];

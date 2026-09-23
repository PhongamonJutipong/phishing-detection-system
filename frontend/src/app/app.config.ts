import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideRouter, withInMemoryScrolling } from '@angular/router';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideHttpClient(withFetch()),
    provideRouter(
      routes,
      // ลิงก์ที่มี fragment (#how-it-works) ต้องเลื่อนไปยังหัวข้อนั้นจริง
      // และเปลี่ยนหน้าแล้วต้องกลับไปบนสุด ไม่ใช่ค้างอยู่ตำแหน่งเดิม
      withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' }),
    ),
  ],
};

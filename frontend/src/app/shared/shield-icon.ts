import { Component } from '@angular/core';

/** โลโก้โล่ติดถูก ใช้ร่วมกันทุกหน้า สีตาม currentColor ของตัวแม่ */
@Component({
  selector: 'app-shield-icon',
  template: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M12 3l7 3v6c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6l7-3z" />
      <path d="M9.2 12l2 2 3.6-4" />
    </svg>
  `,
})
export class ShieldIcon {}

import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { I18nService } from '../core/i18n.service';
import { ShieldIcon } from '../shared/shield-icon';

/**
 * หน้าเข้าสู่ระบบ — เป็นแบบร่างโดยตั้งใจ
 *
 * ฟอร์มไม่ส่งข้อมูลไปที่ใดทั้งสิ้น ไม่มีการเรียก API ไม่เก็บค่าลง storage
 * และการตรวจสอบอีเมลไม่ได้บังคับให้เข้าสู่ระบบ
 */
@Component({
  selector: 'app-login',
  imports: [RouterLink, ShieldIcon],
  template: `
    <main class="auth">
      <a class="wordmark auth-brand" routerLink="/">
        <app-shield-icon />
        {{ t().brand }}
      </a>

      <div class="auth-card">
        <span class="draft-tag">{{ t().loginDraft }}</span>
        <h1>{{ t().loginTitle }}</h1>
        <p class="auth-sub">{{ t().loginSub }}</p>

        <form (submit)="$event.preventDefault(); notice.set(t().loginNotWired)" novalidate>
          <div class="field">
            <label for="login-email">{{ t().loginEmail }}</label>
            <input id="login-email" type="email" autocomplete="off" placeholder="you@example.com" />
          </div>
          <div class="field">
            <label for="login-password">{{ t().loginPassword }}</label>
            <input id="login-password" type="password" autocomplete="off" placeholder="••••••••" />
          </div>
          <div class="field-row">
            <label class="checkbox">
              <input type="checkbox" />
              <span>{{ t().loginRemember }}</span>
            </label>
            <a class="forgot" routerLink="/login">{{ t().loginForgot }}</a>
          </div>
          <button type="submit" class="primary">{{ t().loginTitle }}</button>
          <p class="form-error" role="status">{{ notice() }}</p>
        </form>

        <div class="auth-divider"><span>{{ t().loginOr }}</span></div>

        <a class="btn btn-ghost auth-skip" routerLink="/scan">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"
               stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14" /><path d="M13 6l6 6-6 6" />
          </svg>
          {{ t().loginSkip }}
        </a>
      </div>

      <p class="auth-foot"><a routerLink="/">{{ t().loginBack }}</a></p>
    </main>
  `,
  host: { class: 'centered-host' },
})
export class Login {
  protected readonly t = inject(I18nService).t;
  protected readonly notice = signal('');
}

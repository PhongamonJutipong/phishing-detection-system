import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { AuthService, authErrorText } from '../core/auth.service';
import { I18nService, TextKey } from '../core/i18n.service';
import { ShieldIcon } from '../shared/shield-icon';

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MIN_PASSWORD_LENGTH = 8;

/**
 * หน้าสมัครสมาชิก
 *
 * ขอข้อมูลเท่าที่จำเป็นต่อการเข้าสู่ระบบเท่านั้น และต้องกดยอมรับนโยบายความเป็นส่วนตัวเอง
 * ช่องยอมรับไม่ติ๊กไว้ให้ล่วงหน้า เพราะความยินยอมต้องเกิดจากการกระทำของผู้ใช้
 */
@Component({
  selector: 'app-register',
  imports: [RouterLink, ShieldIcon],
  template: `
    <main class="auth">
      <a class="wordmark auth-brand" routerLink="/">
        <app-shield-icon />
        {{ t().brand }}
      </a>

      <div class="auth-card">
        <h1>{{ t().registerTitle }}</h1>
        <p class="auth-sub">{{ t().registerSub }}</p>

        <form (submit)="$event.preventDefault(); submit()" novalidate>
          <div class="field">
            <label for="register-email">{{ t().loginEmail }}</label>
            <input id="register-email" type="email" autocomplete="email" placeholder="you@example.com"
                   [value]="email()" (input)="email.set($any($event.target).value)" />
          </div>
          <div class="field">
            <label for="register-password">{{ t().loginPassword }}</label>
            <input id="register-password" type="password" autocomplete="new-password"
                   [placeholder]="t().registerPasswordHint"
                   [value]="password()" (input)="password.set($any($event.target).value)" />
          </div>
          <div class="field">
            <label for="register-confirm">{{ t().registerConfirm }}</label>
            <input id="register-confirm" type="password" autocomplete="new-password"
                   [value]="confirm()" (input)="confirm.set($any($event.target).value)" />
          </div>
          <label class="checkbox consent">
            <input type="checkbox" [checked]="consent()" (change)="consent.set($any($event.target).checked)" />
            <span>
              {{ t().registerConsentPre }}
              <a routerLink="/privacy" target="_blank">{{ t().registerConsentLink }}</a>
            </span>
          </label>
          <button type="submit" class="primary" [disabled]="loading()">
            {{ loading() ? t().registerWorking : t().registerTitle }}
          </button>
          <p class="form-error" role="alert">{{ error() ? t()[error()!] : '' }}</p>
        </form>

        <p class="auth-switch">
          {{ t().registerHaveAccount }} <a routerLink="/login">{{ t().loginTitle }}</a>
        </p>
      </div>

      <p class="auth-foot"><a routerLink="/">{{ t().loginBack }}</a></p>
    </main>
  `,
  host: { class: 'centered-host' },
})
export class Register {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  protected readonly t = inject(I18nService).t;

  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly confirm = signal('');
  protected readonly consent = signal(false);
  protected readonly loading = signal(false);
  protected readonly error = signal<TextKey | null>(null);

  protected submit(): void {
    const problem = this.validate();
    this.error.set(problem);
    if (problem) {
      return;
    }
    this.loading.set(true);
    this.auth.register(this.email().trim(), this.password()).subscribe({
      next: () => this.router.navigateByUrl('/account'),
      error: (err) => {
        this.loading.set(false);
        this.error.set(authErrorText(err));
      },
    });
  }

  /** ตรวจแบบเดียวกับเซิร์ฟเวอร์ เพื่อบอกผู้ใช้ได้ทันทีโดยไม่ต้องรอส่งคำขอ */
  private validate(): TextKey | null {
    if (!this.email().trim() || !this.password()) {
      return 'authErrRequired';
    }
    if (!EMAIL_PATTERN.test(this.email().trim())) {
      return 'authErrEmail';
    }
    if (this.password().length < MIN_PASSWORD_LENGTH) {
      return 'authErrPasswordShort';
    }
    if (this.password() !== this.confirm()) {
      return 'authErrPasswordMismatch';
    }
    if (!this.consent()) {
      return 'authErrConsent';
    }
    return null;
  }
}

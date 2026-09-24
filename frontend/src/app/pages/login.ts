import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { AuthService, authErrorText } from '../core/auth.service';
import { I18nService, TextKey } from '../core/i18n.service';
import { ShieldIcon } from '../shared/shield-icon';

/**
 * หน้าเข้าสู่ระบบ
 *
 * การตรวจสอบอีเมลไม่บังคับให้เข้าสู่ระบบ หน้านี้มีไว้สำหรับผู้ที่สมัครบัญชีแล้วเท่านั้น
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
        <h1>{{ t().loginTitle }}</h1>
        <p class="auth-sub">{{ t().loginSub }}</p>

        <form (submit)="$event.preventDefault(); submit()" novalidate>
          <div class="field">
            <label for="login-email">{{ t().loginEmail }}</label>
            <input id="login-email" type="email" autocomplete="email" placeholder="you@example.com"
                   [value]="email()" (input)="email.set($any($event.target).value)" />
          </div>
          <div class="field">
            <label for="login-password">{{ t().loginPassword }}</label>
            <input id="login-password" type="password" autocomplete="current-password" placeholder="••••••••"
                   [value]="password()" (input)="password.set($any($event.target).value)" />
          </div>
          <div class="field-row">
            <label class="checkbox">
              <input type="checkbox" [checked]="remember()" (change)="remember.set($any($event.target).checked)" />
              <span>{{ t().loginRemember }}</span>
            </label>
          </div>
          <button type="submit" class="primary" [disabled]="loading()">
            {{ loading() ? t().loginWorking : t().loginTitle }}
          </button>
          <p class="form-error" role="alert">{{ error() ? t()[error()!] : '' }}</p>
        </form>

        <p class="auth-switch">
          {{ t().loginNoAccount }} <a routerLink="/register">{{ t().registerTitle }}</a>
        </p>

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
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  protected readonly t = inject(I18nService).t;

  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly remember = signal(false);
  protected readonly loading = signal(false);
  protected readonly error = signal<TextKey | null>(null);

  protected submit(): void {
    if (!this.email().trim() || !this.password()) {
      this.error.set('authErrRequired');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.auth.login(this.email().trim(), this.password(), this.remember()).subscribe({
      next: () => this.router.navigateByUrl('/account'),
      error: (err) => {
        this.loading.set(false);
        this.password.set('');
        this.error.set(authErrorText(err));
      },
    });
  }
}


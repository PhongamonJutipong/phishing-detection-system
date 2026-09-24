import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { AuthService, authErrorText } from '../core/auth.service';
import { I18nService, TextKey } from '../core/i18n.service';
import { SiteFooter } from '../shared/site-footer';
import { SiteNav } from '../shared/site-nav';

/**
 * หน้าบัญชีของฉัน
 *
 * แสดงข้อมูลทุกอย่างที่ระบบเก็บเกี่ยวกับบัญชี (สิทธิ์เข้าถึงข้อมูลของเจ้าของ)
 * และให้ลบบัญชีได้เองโดยไม่ต้องติดต่อผู้ดูแล (สิทธิ์ขอลบข้อมูล)
 */
@Component({
  selector: 'app-account',
  imports: [RouterLink, SiteNav, SiteFooter],
  template: `
    <app-site-nav />

    <main class="account-page">
      <div class="container narrow">
        <h1>{{ t().navAccount }}</h1>

        @if (deleted()) {
          <div class="card account-card">
            <p>{{ t().accountDeleted }}</p>
            <a class="btn btn-ghost btn-sm" routerLink="/">{{ t().loginBack }}</a>
          </div>
        } @else if (!auth.loggedIn()) {
          <div class="card account-card">
            <p>{{ t().accountNeedLogin }}</p>
            <a class="btn btn-primary btn-sm" routerLink="/login">{{ t().loginTitle }}</a>
          </div>
        } @else if (auth.user(); as user) {
          <p class="lead">{{ t().accountSub }}</p>

          <div class="card account-card">
            <dl class="account-data">
              <dt>{{ t().accountEmail }}</dt>
              <dd>{{ user.email ?? t().accountEmailUnavailable }}</dd>
              <dt>{{ t().accountCreated }}</dt>
              <dd>{{ formatDate(user.created_at) }}</dd>
              <dt>{{ t().accountConsent }}</dt>
              <dd><a routerLink="/privacy">{{ t().privacyVersion }} {{ user.consent_version }}</a></dd>
              <dt>{{ t().accountConsentAt }}</dt>
              <dd>{{ formatDate(user.consent_at) }}</dd>
            </dl>
            <p class="account-note">{{ t().accountNotStored }}</p>
            <button type="button" class="btn btn-ghost btn-sm" (click)="logout()">{{ t().accountLogout }}</button>
          </div>

          <div class="card account-card danger-zone">
            <h2>{{ t().accountDeleteTitle }}</h2>
            <p>{{ t().accountDeleteSub }}</p>
            <form (submit)="$event.preventDefault(); deleteAccount()" novalidate>
              <div class="field">
                <label for="delete-password">{{ t().accountDeletePassword }}</label>
                <input id="delete-password" type="password" autocomplete="current-password"
                       [value]="password()" (input)="password.set($any($event.target).value)" />
              </div>
              <button type="submit" class="btn btn-danger btn-sm" [disabled]="busy() || !password()">
                {{ t().accountDeleteButton }}
              </button>
              <p class="form-error" role="alert">{{ error() ? t()[error()!] : '' }}</p>
            </form>
          </div>
        } @else {
          <p class="lead">{{ t().accountLoading }}</p>
        }
      </div>
    </main>

    <app-site-footer />
  `,
})
export class Account {
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly i18n = inject(I18nService);
  protected readonly t = this.i18n.t;

  protected readonly password = signal('');
  protected readonly busy = signal(false);
  protected readonly error = signal<TextKey | null>(null);
  protected readonly deleted = signal(false);

  /** แสดงวันเวลาตามภาษาที่เลือก (DatePipe ใช้ en-US เสมอถ้าไม่ได้ลงทะเบียน locale ไทยไว้) */
  protected formatDate(value: string): string {
    const locale = this.i18n.language() === 'th' ? 'th-TH' : 'en-GB';
    return new Intl.DateTimeFormat(locale, { dateStyle: 'long', timeStyle: 'short' }).format(new Date(value));
  }

  protected logout(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigateByUrl('/'),
      error: () => this.router.navigateByUrl('/'),
    });
  }

  protected deleteAccount(): void {
    this.busy.set(true);
    this.error.set(null);
    this.auth.deleteAccount(this.password()).subscribe({
      next: () => {
        this.busy.set(false);
        this.deleted.set(true);
      },
      error: (err) => {
        this.busy.set(false);
        this.password.set('');
        this.error.set(err?.status === 403 ? 'accountDeleteWrong' : authErrorText(err));
      },
    });
  }
}

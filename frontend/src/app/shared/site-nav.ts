import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../core/auth.service';
import { I18nService } from '../core/i18n.service';
import { ShieldIcon } from './shield-icon';

/** แถบนำทางด้านบน ใช้กับหน้าแรก หน้าตรวจสอบ และหน้าอื่นที่ไม่ใช่ผู้ดูแล */
@Component({
  selector: 'app-site-nav',
  imports: [RouterLink, ShieldIcon],
  template: `
    <nav class="site-nav">
      <div class="container">
        <a class="wordmark" routerLink="/" [attr.aria-label]="t().brand">
          <app-shield-icon />
          <span class="wordmark-text">{{ t().brand }}</span>
        </a>

        <div class="nav-links">
          <a routerLink="/" fragment="how-it-works">{{ t().navHowItWorks }}</a>
          <a routerLink="/" fragment="features">{{ t().navFeatures }}</a>
          <a routerLink="/dashboard">{{ t().navDashboard }}</a>
        </div>

        <div class="nav-actions">
          <button type="button" class="link-btn lang-btn" (click)="i18n.toggle()">
            {{ t().langToggle }}
          </button>
          @if (auth.loggedIn()) {
            <a class="login" routerLink="/account">{{ t().navAccount }}</a>
          } @else {
            <a class="login" routerLink="/login">{{ t().navLogin }}</a>
          }
          <a class="btn btn-primary btn-sm" routerLink="/scan">{{ t().navScan }}</a>
        </div>
      </div>
    </nav>
  `,
  styles: `
    .lang-btn {
      font-family: var(--font-mono);
      font-size: 12px;
      letter-spacing: 0.05em;
      color: var(--muted);
    }
    .lang-btn:hover { color: var(--accent); }
  `,
})
export class SiteNav {
  protected readonly i18n = inject(I18nService);
  protected readonly auth = inject(AuthService);
  protected readonly t = this.i18n.t;
}

import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { I18nService } from '../core/i18n.service';
import { ShieldIcon } from './shield-icon';

@Component({
  selector: 'app-site-footer',
  imports: [RouterLink, ShieldIcon],
  template: `
    <footer class="site-footer">
      <div class="container">
        <a class="wordmark" routerLink="/">
          <app-shield-icon />
          {{ t().brand }}
        </a>
        <span class="copyright">{{ t().footerNote }}</span>
        <div class="footer-links">
          <a routerLink="/scan">{{ t().navScan }}</a>
          <a routerLink="/dashboard">{{ t().navDashboard }}</a>
          <a routerLink="/privacy">{{ t().navPrivacy }}</a>
          <a href="docs" target="_blank" rel="noopener">API</a>
        </div>
      </div>
    </footer>
  `,
})
export class SiteFooter {
  protected readonly t = inject(I18nService).t;
}

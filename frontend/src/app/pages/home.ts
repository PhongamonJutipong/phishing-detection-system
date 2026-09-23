import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { I18nService } from '../core/i18n.service';
import { SiteFooter } from '../shared/site-footer';
import { SiteNav } from '../shared/site-nav';

@Component({
  selector: 'app-home',
  imports: [RouterLink, SiteNav, SiteFooter],
  templateUrl: './home.html',
})
export class Home {
  protected readonly t = inject(I18nService).t;

  /** ชื่อเทคโนโลยีเป็นชื่อเฉพาะ ไม่ต้องแปล */
  protected readonly stack = ['FastAPI', 'scikit-learn', 'PyThaiNLP', 'PostgreSQL', 'Angular'];
}

import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ApiService } from '../core/api.service';
import { I18nService, TextKey } from '../core/i18n.service';
import { Language, RecentScan, RiskLevel, StatsResponse } from '../core/models';
import { ShieldIcon } from '../shared/shield-icon';

const TOKEN_KEY = 'admin_token';

type State = 'needToken' | 'loading' | 'ready' | 'error';

/**
 * หน้าภาพรวมผู้ดูแล ดึงข้อมูลจริงจาก GET /api/v1/stats
 *
 * endpoint นี้ต้องใช้ X-Admin-Token จึงให้ผู้ดูแลกรอกเอง แล้วเก็บไว้ใน sessionStorage
 * (หายเมื่อปิดแท็บ) ไม่ฝัง token ไว้ในโค้ดหน้าเว็บ เพราะใครเปิดหน้าเว็บก็อ่านโค้ดได้
 */
@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, ShieldIcon],
  templateUrl: './dashboard.html',
  host: { class: 'app-host' },
})
export class Dashboard {
  private readonly api = inject(ApiService);
  protected readonly i18n = inject(I18nService);
  protected readonly t = this.i18n.t;

  protected readonly token = signal(readToken());
  protected readonly tokenInput = signal('');
  protected readonly state = signal<State>(this.token() ? 'loading' : 'needToken');
  protected readonly error = signal<TextKey | null>(null);
  protected readonly stats = signal<StatsResponse | null>(null);
  protected readonly updatedAt = signal<Date | null>(null);

  protected readonly recentLabel = computed(() =>
    this.t().dashRecentCount.replace('{n}', String(this.stats()?.recent_scans.length ?? 0)),
  );

  constructor() {
    if (this.token()) {
      this.load();
    }
  }

  protected submitToken(): void {
    const value = this.tokenInput().trim();
    if (!value) {
      return;
    }
    this.token.set(value);
    this.tokenInput.set('');
    this.load();
  }

  protected forgetToken(): void {
    this.token.set('');
    storeToken('');
    this.stats.set(null);
    this.error.set(null);
    this.state.set('needToken');
  }

  protected load(): void {
    this.state.set('loading');
    this.error.set(null);
    this.api.stats(this.token()).subscribe({
      next: (data) => {
        storeToken(this.token());
        this.stats.set(data);
        this.updatedAt.set(new Date());
        this.state.set('ready');
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(statsErrorText(err.status));
        if (err.status === 401 || err.status === 404) {
          // token ผิดหรือปิดใช้งาน ไม่เก็บค่าที่ใช้ไม่ได้ไว้
          this.token.set('');
          storeToken('');
          this.state.set('needToken');
        } else {
          this.state.set('error');
        }
      },
    });
  }

  protected levelBadge(level: RiskLevel): string {
    return level === 'dangerous' ? 'badge-high' : level === 'suspicious' ? 'badge-medium' : 'badge-safe';
  }

  protected levelText(level: RiskLevel): string {
    const t = this.t();
    return level === 'dangerous' ? t.dashPhishing : level === 'suspicious' ? t.dashSuspicious : t.dashSafe;
  }

  protected langLabel(lang: Language | null): string {
    return lang === 'th' ? this.t().langTh : lang === 'en' ? this.t().langEn : '-';
  }

  protected percent(row: RecentScan): string {
    return row.probability === null ? '-' : `${(row.probability * 100).toFixed(1)}%`;
  }

  protected formatTime(value: string | Date | null, withDate = true): string {
    if (!value) {
      return '-';
    }
    const locale = this.i18n.language() === 'th' ? 'th-TH' : 'en-GB';
    const options: Intl.DateTimeFormatOptions = withDate
      ? { dateStyle: 'medium', timeStyle: 'short' }
      : { timeStyle: 'medium' };
    return new Intl.DateTimeFormat(locale, options).format(new Date(value));
  }
}

function statsErrorText(status: number): TextKey {
  switch (status) {
    case 0:
      return 'dashErrOffline';
    case 401:
      return 'dashErrWrongToken';
    case 404:
      return 'dashErrDisabled';
    default:
      return 'dashErrUnknown';
  }
}

function readToken(): string {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? '';
  } catch {
    return '';
  }
}

function storeToken(value: string): void {
  try {
    if (value) {
      sessionStorage.setItem(TOKEN_KEY, value);
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // เก็บไม่ได้ก็ใช้ได้จนกว่าจะรีโหลดหน้า
  }
}

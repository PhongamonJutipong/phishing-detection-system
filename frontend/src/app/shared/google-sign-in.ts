import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  ElementRef,
  OnInit,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';

import { AuthService } from '../core/auth.service';
import { GoogleIdentityService } from '../core/google-identity.service';
import { I18nService, TextKey } from '../core/i18n.service';

/**
 * ปุ่มเข้าสู่ระบบด้วยบัญชี Google พร้อมขั้นตอนที่ต้องถามเพิ่ม
 *
 * จัดการสามสถานะไว้ในตัวเอง หน้า login กับ register จึงใช้ซ้ำได้โดยไม่ต้องรู้รายละเอียด
 *   button  — ปุ่มของ Google ตามปกติ
 *   consent — อีเมลนี้ยังไม่มีบัญชี ต้องขอความยินยอมก่อนสร้าง
 *   link    — อีเมลนี้มีบัญชีแบบรหัสผ่านอยู่แล้ว ขอรหัสผ่านเดิมหนึ่งครั้งเพื่อผูก
 *
 * ซ่อนตัวเองทั้งหมดถ้าเซิร์ฟเวอร์ไม่ได้ตั้ง GOOGLE_CLIENT_ID
 */
@Component({
  selector: 'app-google-sign-in',
  template: `
    @if (clientId()) {
      <div class="google-signin">
        <!-- ปุ่มของ Google ต้องอยู่ใน DOM ตลอด เพราะ renderButton เขียนลง element นี้ -->
        <div #buttonHost [hidden]="step() !== 'button' || busy()"></div>

        @if (busy()) {
          <p class="auth-note">{{ t().googleWorking }}</p>
        }

        @if (step() === 'consent') {
          <div class="google-step">
            <p class="auth-note"><strong>{{ t().googleConsentTitle }}</strong></p>
            <label class="checkbox">
              <input type="checkbox" [checked]="consent()"
                     (change)="consent.set($any($event.target).checked)" />
              <span>{{ t().googleConsentCheck }}</span>
            </label>
            <button type="button" class="primary" [disabled]="!consent() || busy()"
                    (click)="submitConsent()">
              {{ t().googleConsentSubmit }}
            </button>
          </div>
        }

        @if (step() === 'link') {
          <div class="google-step">
            <p class="auth-note"><strong>{{ t().googleLinkTitle }}</strong></p>
            <p class="auth-note">{{ t().googleLinkHelp }}</p>
            <div class="field">
              <label for="google-link-password">{{ t().googleLinkPassword }}</label>
              <input id="google-link-password" type="password" autocomplete="current-password"
                     [value]="linkPassword()"
                     (input)="linkPassword.set($any($event.target).value)" />
            </div>
            <button type="button" class="primary" [disabled]="!linkPassword() || busy()"
                    (click)="submitLink()">
              {{ t().googleLinkSubmit }}
            </button>
          </div>
        }

        <p class="form-error" role="alert">{{ error() ? t()[error()!] : '' }}</p>
      </div>
    }
  `,
})
export class GoogleSignIn implements OnInit {
  /** ส่ง true มาจากหน้าสมัครสมาชิก เพื่อถือว่าผู้ใช้ยอมรับนโยบายไปแล้ว */
  readonly consentAlreadyGiven = input(false);
  readonly remember = input(false);
  /** ยืนยันสำเร็จแล้ว หน้าที่ใช้คอมโพเนนต์นี้เป็นคนพาไปหน้าถัดไป */
  readonly signedIn = output<void>();

  private readonly auth = inject(AuthService);
  private readonly google = inject(GoogleIdentityService);
  private readonly i18n = inject(I18nService);
  protected readonly t = this.i18n.t;

  private readonly buttonHost = viewChild<ElementRef<HTMLElement>>('buttonHost');

  protected readonly clientId = signal<string | null>(null);
  protected readonly step = signal<'button' | 'consent' | 'link'>('button');
  protected readonly busy = signal(false);
  protected readonly error = signal<TextKey | null>(null);
  protected readonly consent = signal(false);
  protected readonly linkPassword = signal('');

  private idToken: string | null = null;
  private rendered = false;

  /** ปุ่มของ Google มีภาษาของตัวเอง ต้องวาดใหม่เมื่อผู้ใช้สลับภาษาของเว็บ */
  private readonly locale = computed<'th' | 'en'>(() => this.i18n.language());

  constructor() {
    effect(() => {
      const id = this.clientId();
      const host = this.buttonHost()?.nativeElement;
      const locale = this.locale();
      if (!id || !host) return;
      this.google
        .renderButton(host, id, (token) => this.onCredential(token), locale)
        .then(() => (this.rendered = true))
        .catch(() => this.error.set('googleErrScript'));
    });
  }

  ngOnInit(): void {
    this.auth.authConfig().subscribe({
      // ไม่ได้ตั้ง client_id = ไม่แสดงอะไรเลย ไม่ใช่แสดงปุ่มที่กดแล้วพัง
      next: (cfg) => this.clientId.set(cfg.google_client_id),
      error: () => this.clientId.set(null),
    });
  }

  private onCredential(idToken: string): void {
    this.idToken = idToken;
    this.error.set(null);
    this.send({ acceptPrivacyPolicy: this.consentAlreadyGiven() });
  }

  protected submitConsent(): void {
    this.send({ acceptPrivacyPolicy: true });
  }

  protected submitLink(): void {
    this.send({ acceptPrivacyPolicy: true, linkPassword: this.linkPassword() });
  }

  private send(options: { acceptPrivacyPolicy: boolean; linkPassword?: string }): void {
    if (!this.idToken) return;
    this.busy.set(true);
    this.error.set(null);
    this.auth
      .googleSignIn(this.idToken, { ...options, remember: this.remember() })
      .subscribe({
        next: () => {
          this.busy.set(false);
          this.linkPassword.set('');
          this.signedIn.emit();
        },
        error: (err) => {
          this.busy.set(false);
          this.linkPassword.set('');
          this.handleError(err);
        },
      });
  }

  /**
   * แยกกรณีด้วย header X-Auth-Reason ไม่ใช่ข้อความ เพราะข้อความเปลี่ยนตามภาษา
   * และสถานะ HTTP เดียวกันใช้ได้หลายความหมาย (409 = ต้องผูกบัญชี หรือ อีเมลถูกใช้แล้ว)
   */
  private handleError(err: unknown): void {
    const reason = err instanceof HttpErrorResponse ? err.headers.get('X-Auth-Reason') : null;
    switch (reason) {
      case 'PASSWORD_REQUIRED_TO_LINK':
        this.step.set('link');
        return;
      case 'CONSENT_REQUIRED':
        this.step.set('consent');
        this.error.set(this.consent() ? 'googleConsentRequired' : null);
        return;
      case 'INVALID_LINK_PASSWORD':
        this.step.set('link');
        this.error.set('googleLinkWrong');
        return;
      case 'GOOGLE_DISABLED':
        this.error.set('googleErrDisabled');
        return;
      case 'INVALID_GOOGLE_TOKEN':
        this.error.set('googleErrToken');
        return;
      default:
        this.error.set('authErrUnknown');
    }
  }
}

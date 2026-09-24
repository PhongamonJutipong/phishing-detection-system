import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, map, tap } from 'rxjs';

import type { TextKey } from './i18n.service';
import { AuthResponse, UserProfile } from './models';

const TOKEN_KEY = 'auth_token';

/**
 * สถานะการเข้าสู่ระบบของหน้าเว็บ
 *
 * เก็บ token ไว้ที่ sessionStorage เป็นค่าเริ่มต้น ปิดแท็บแล้วหายไปเอง
 * เก็บใน localStorage เฉพาะเมื่อผู้ใช้เลือก "จดจำการเข้าสู่ระบบ" เท่านั้น
 * ไม่เก็บอีเมลหรือข้อมูลบัญชีลงเครื่อง ดึงจากเซิร์ฟเวอร์ใหม่ทุกครั้งที่เปิดหน้า
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly token = signal<string | null>(readToken());

  readonly user = signal<UserProfile | null>(null);
  readonly loggedIn = computed(() => this.token() !== null);

  constructor() {
    if (this.token()) {
      this.refreshProfile().subscribe({ error: () => undefined });
    }
  }

  register(email: string, password: string): Observable<UserProfile> {
    return this.http
      .post<AuthResponse>('api/v1/auth/register', { email, password, accept_privacy_policy: true })
      .pipe(map((res) => this.accept(res, false)));
  }

  login(email: string, password: string, remember: boolean): Observable<UserProfile> {
    return this.http
      .post<AuthResponse>('api/v1/auth/login', { email, password, remember })
      .pipe(map((res) => this.accept(res, remember)));
  }

  /** ยกเลิก token ที่เซิร์ฟเวอร์ด้วย ไม่ใช่แค่ลบในเบราว์เซอร์ */
  logout(): Observable<void> {
    return this.http
      .post<void>('api/v1/auth/logout', null, { headers: this.headers() })
      .pipe(tap({ next: () => this.clear(), error: () => this.clear() }));
  }

  refreshProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>('api/v1/auth/me', { headers: this.headers() }).pipe(
      tap({
        next: (user) => this.user.set(user),
        error: (err: HttpErrorResponse) => {
          if (err.status === 401) {
            this.clear();
          }
        },
      }),
    );
  }

  deleteAccount(password: string): Observable<void> {
    return this.http
      .delete<void>('api/v1/auth/me', { headers: this.headers(), body: { password } })
      .pipe(tap(() => this.clear()));
  }

  private accept(res: AuthResponse, remember: boolean): UserProfile {
    clearStoredToken();
    try {
      (remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, res.token);
    } catch {
      // เก็บไม่ได้ (โหมดส่วนตัว) ยังใช้งานได้จนกว่าจะปิดหน้า
    }
    this.token.set(res.token);
    this.user.set(res.user);
    return res.user;
  }

  private clear(): void {
    clearStoredToken();
    this.token.set(null);
    this.user.set(null);
  }

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.token() ?? ''}` });
  }
}

function readToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function clearStoredToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ไม่มีอะไรให้ลบ
  }
}

/** แปลงข้อผิดพลาดจาก API เป็นข้อความที่หน้าเว็บแสดง */
export function authErrorText(err: unknown): TextKey {
  const status = err instanceof HttpErrorResponse ? err.status : -1;
  switch (status) {
    case 0:
      return 'authErrOffline';
    case 401:
      return 'authErrInvalid';
    case 409:
      return 'authErrTaken';
    case 422:
      return 'authErrRejected';
    case 429:
      return 'authErrTooMany';
    default:
      return 'authErrUnknown';
  }
}

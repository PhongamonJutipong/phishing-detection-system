import { Injectable } from '@angular/core';

/**
 * โหลดและเรียกใช้บริการ Google Identity Services
 *
 * ใช้วิธี "ID token" ไม่ใช่ OAuth code flow จึงไม่ต้องมี client secret
 * ฝั่งเซิร์ฟเวอร์ และไม่ต้องจัดการ redirect กลับมาที่หน้าเว็บ
 * ได้ JWT มาแล้วส่งให้ backend ตรวจลายเซ็นกับ public key ของ Google
 *
 * สคริปต์ของ Google ถูกโหลดเมื่อจำเป็นเท่านั้น (ตอนผู้ใช้เปิดหน้าเข้าสู่ระบบ)
 * หน้าอื่นจึงไม่ต้องยิงคำขอออกไปที่ Google เลย
 */
const GSI_SRC = 'https://accounts.google.com/gsi/client';

/** รูปร่างเท่าที่เราใช้ ไม่ดึง @types ของ Google เข้ามาทั้งก้อน */
interface GoogleAccountsId {
  initialize(config: {
    client_id: string;
    callback: (response: { credential?: string }) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
  }): void;
  renderButton(parent: HTMLElement, options: Record<string, unknown>): void;
  disableAutoSelect(): void;
}

declare global {
  interface Window {
    google?: { accounts?: { id?: GoogleAccountsId } };
  }
}

@Injectable({ providedIn: 'root' })
export class GoogleIdentityService {
  private loading: Promise<GoogleAccountsId> | null = null;

  /** โหลดสคริปต์ครั้งเดียวแล้วใช้ซ้ำ ถ้าโหลดไม่สำเร็จจะ reject ให้หน้าเว็บแสดงข้อความแทน */
  load(): Promise<GoogleAccountsId> {
    if (this.loading) return this.loading;

    this.loading = new Promise<GoogleAccountsId>((resolve, reject) => {
      const existing = window.google?.accounts?.id;
      if (existing) {
        resolve(existing);
        return;
      }

      const previous = document.querySelector<HTMLScriptElement>(`script[src="${GSI_SRC}"]`);
      const script = previous ?? document.createElement('script');
      const done = () => {
        const api = window.google?.accounts?.id;
        if (api) resolve(api);
        else reject(new Error('GSI script loaded but google.accounts.id is missing'));
      };

      script.addEventListener('load', done, { once: true });
      script.addEventListener('error', () => reject(new Error('GSI script failed to load')), { once: true });

      if (!previous) {
        script.src = GSI_SRC;
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
      }
    });

    // โหลดพลาดแล้วต้องลองใหม่ได้ ไม่ใช่ค้างอยู่กับ promise ที่ reject ไปแล้วตลอด
    this.loading.catch(() => {
      this.loading = null;
    });
    return this.loading;
  }

  /**
   * วางปุ่มของ Google ลงใน element ที่ให้มา แล้วเรียก onCredential เมื่อผู้ใช้ยืนยันสำเร็จ
   *
   * ใช้ปุ่มของ Google ตรง ๆ ไม่ทำปุ่มเลียนแบบ เพราะนโยบายแบรนด์ของ Google กำหนดไว้
   * และผู้ใช้คุ้นกับหน้าตามาตรฐานอยู่แล้ว
   */
  async renderButton(
    host: HTMLElement,
    clientId: string,
    onCredential: (idToken: string) => void,
    locale: 'th' | 'en',
  ): Promise<void> {
    const api = await this.load();
    api.initialize({
      client_id: clientId,
      callback: (response) => {
        if (response.credential) onCredential(response.credential);
      },
      // ไม่เข้าสู่ระบบให้เองโดยที่ผู้ใช้ไม่ได้กด เพราะการสร้างบัญชีต้องขอความยินยอมก่อน
      auto_select: false,
      cancel_on_tap_outside: true,
    });
    host.replaceChildren();
    api.renderButton(host, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      shape: 'rectangular',
      text: 'continue_with',
      logo_alignment: 'left',
      width: 280,
      locale,
    });
  }

  /** เลิกจำบัญชีที่เลือกไว้ เรียกตอนออกจากระบบ ไม่งั้นครั้งถัดไป Google จะเลือกให้เอง */
  disableAutoSelect(): void {
    window.google?.accounts?.id?.disableAutoSelect();
  }
}

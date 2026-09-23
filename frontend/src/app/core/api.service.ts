import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { AnalyzeRequest, AnalyzeResponse, HealthResponse } from './models';

/**
 * เรียก API ของ backend
 *
 * ใช้ path แบบสัมพัทธ์ ('api/v1/...') เพราะหน้าเว็บถูกเสิร์ฟจาก origin เดียวกับ API
 * จึงไม่ต้องตั้งค่าที่อยู่เซิร์ฟเวอร์ และไม่ติดปัญหา CORS
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  analyze(body: AnalyzeRequest): Observable<AnalyzeResponse> {
    return this.http.post<AnalyzeResponse>('api/v1/analyze', body);
  }

  health(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>('api/v1/health');
  }
}

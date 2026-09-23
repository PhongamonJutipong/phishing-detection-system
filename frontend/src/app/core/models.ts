/** รูปร่างข้อมูลที่รับส่งกับ backend — ตรงกับ backend/app/schemas.py */

export type RiskLevel = 'dangerous' | 'suspicious' | 'safe';
export type Classification = 'phishing' | 'legitimate';
export type Language = 'th' | 'en';

export interface AnalyzeRequest {
  subject?: string;
  sender?: string;
  body_content: string;
}

export interface Highlight {
  phrase: string;
  reason: string;
  weight: number;
}

export interface Indicator {
  category: string;
  phrases: string[];
}

export interface AnalyzeResponse {
  /** เป็น null เมื่อบันทึกผลลงฐานข้อมูลไม่สำเร็จ ผลวิเคราะห์ยังใช้ได้ตามปกติ */
  result_id: string | null;
  risk_score: number;
  risk_percentage: number;
  risk_level: RiskLevel;
  is_phishing: boolean;
  classification: Classification;
  language: Language;
  /** ความน่าจะเป็นของแต่ละภาษาที่พบในอีเมล (UC-04 ข้อ 9-10) */
  language_scores: Record<string, number>;
  highlights: Highlight[];
  suspicious_keywords: string[];
  indicators: Indicator[];
  processing_time_ms: number;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  models_loaded: string[];
  database: string;
}

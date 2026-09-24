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

/** ข้อมูลทั้งหมดที่ระบบเก็บเกี่ยวกับบัญชีผู้ใช้ */
export interface UserProfile {
  /** null เมื่อเซิร์ฟเวอร์ถอดรหัสอีเมลไม่ได้ (เช่นเปลี่ยนกุญแจเข้ารหัส) */
  email: string | null;
  created_at: string;
  consent_version: string;
  consent_at: string;
}

export interface AuthResponse {
  token: string;
  expires_at: string;
  user: UserProfile;
}

export interface RecentScan {
  scan_time: string | null;
  probability: number | null;
  classification: Classification | null;
  risk_level: RiskLevel;
  language: Language | null;
}

export interface StoredModel {
  model_id: string;
  model_name: string | null;
  algorithm: string | null;
  /** ร้อยละ เช่น 96.79 */
  accuracy: number | null;
  train_date: string | null;
}

/** GET /api/v1/stats — ต้องส่ง header X-Admin-Token */
export interface StatsResponse {
  total_emails: number;
  total_scans: number;
  scans_by_classification: Record<string, number>;
  risk_levels: Record<RiskLevel, number>;
  recent_scans: RecentScan[];
  models: StoredModel[];
}

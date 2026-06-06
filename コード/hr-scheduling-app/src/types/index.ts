// ============================================================
// 型定義
// ============================================================

export interface Company {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  theme_color: string;
  greeting_text: string | null;
  calendar_id: string;
  sender_name: string;
  sender_email: string;
  slot_duration_minutes: number;
  buffer_minutes: number;
  available_days_ahead: number;
  is_active: boolean;
}

export interface TimeSlot {
  start: Date;
  end: Date;
  available: boolean;
}

export interface DaySlots {
  date: Date;
  slots: TimeSlot[];
}

export interface BookingFormData {
  candidateName: string;
  candidateEmail: string;
  candidatePhone: string;
  sourceMedium: string;
}

export interface Booking {
  id: string;
  company_id: string;
  candidate_name: string;
  candidate_email: string;
  candidate_phone: string | null;
  source_medium: string | null;
  interview_start_at: string;
  interview_end_at: string;
  google_calendar_event_id: string | null;
  google_meet_url: string | null;
  status: 'pending' | 'confirmed' | 'cancelled' | 'rescheduled';
  created_at: string;
}

export type BookingStep = 'select-slot' | 'enter-info' | 'confirm' | 'complete';

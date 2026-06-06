export type UserRole = 'patient' | 'donor' | 'blood_bank' | 'coordinator' | 'admin';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface PatientProfile {
  id: number;
  user_id: number;
  blood_group_required: string;
  units_required: number;
  urgency: string;
  hospital_name?: string;
  city?: string;
  state?: string;
  latitude?: number;
  longitude?: number;
  medical_notes?: string;
  is_fulfilled: boolean;
}

export interface DonorProfile {
  id: number;
  user_id: number;
  blood_group: string;
  age?: number;
  weight?: number;
  city?: string;
  state?: string;
  latitude?: number;
  longitude?: number;
  is_available: boolean;
  reliability_score: number;
  response_rate: number;
  no_show_count: number;
  total_donations: number;
  last_donated_at?: string;
  points?: number;
}

export interface BloodBankProfile {
  id: number;
  user_id: number;
  hospital_name: string;
  contact_phone: string;
  address: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
}

export interface BloodInventory {
  id: number;
  blood_bank_id: number;
  blood_group: string;
  quantity_ml: number;
  updated_at: string;
}

export interface BloodUnit {
  id: number;
  inventory_id: number;
  donor_id: number;
  blood_group: string;
  volume_ml: number;
  status: 'available' | 'reserved' | 'used' | 'discarded';
  is_safe: boolean;
  notes?: string;
  created_at: string;
  validation_report?: ValidationReport;
}

export interface ValidationReport {
  id: number;
  unit_id: number;
  donor_id: number;
  hemoglobin_g_dl: number;
  systolic_bp?: number;
  diastolic_bp?: number;
  pulse_bpm?: number;
  status: 'approved' | 'rejected';
  issue_category?: string;
  feedback_notes?: string;
  improvement_recommendations?: string;
  report_pdf_path?: string;
  created_at: string;
}

export interface BloodRequest {
  id: number;
  patient_id: number;
  blood_group: string;
  units_required: number;
  urgency: string;
  status: 'pending' | 'matched' | 'accepted' | 'fulfilled' | 'cancelled' | 'escalated';
  assigned_donor_id?: number;
  assigned_blood_bank_id?: number;
  assigned_by?: string;
  coordinator_note?: string;
  ai_confidence_score?: number;
  created_at: string;
  patient?: {
    id: number;
    user: { full_name: string };
    hospital_name: string;
    city: string;
    latitude?: number;
    longitude?: number;
  };
  assigned_donor?: {
    id: number;
    user: { full_name: string };
  };
  top_donors?: any[];
}

export interface Notification {
  id: number;
  user_id: number;
  title: string;
  body: string;
  type: 'system' | 'request' | 'alert' | 'chat' | 'badge';
  is_read: boolean;
  created_at: string;
}

export interface ChatRoom {
  id: number;
  request_id: number;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  room_id: number;
  sender_id: number;
  message: string;
  created_at: string;
  sender?: {
    full_name: string;
  };
}

export interface TransfusionPrediction {
  id: number;
  user_id: number;
  age: number;
  gender: 'Male' | 'Female';
  weight_kg: number;
  thalassemia_type: 'Major' | 'Intermedia';
  current_hb_level: number;
  target_hb_level: number;
  ferritin_level: number;
  days_since_last_transfusion: number;
  previous_units_received: number;
  average_units_per_transfusion: number;
  transfusions_last_12_months: number;
  spleen_status: 'Normal' | 'Enlarged' | 'Removed';
  symptom_severity: 'Mild' | 'Moderate' | 'Severe';
  blood_group: string;
  predicted_units_required: number;
  recommended_next_transfusion_in_days: number;
  created_at: string;
}

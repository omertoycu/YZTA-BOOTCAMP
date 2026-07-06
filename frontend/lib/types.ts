export interface Office {
  id: string;
  name: string;
  subscription_plan: string;
  notification_phone: string | null;
  whatsapp_phone_number_id: string | null;
  created_at: string;
}

export interface Listing {
  id: string;
  title: string;
  district: string;
  price: number;
  room_count: string;
  square_meters: number | null;
  status: string;
  photos: string[];
  created_at: string;
}

export interface ListingExtract {
  title: string | null;
  district: string | null;
  price: number | null;
  room_count: string | null;
  square_meters: number | null;
}

export interface VoiceListingDraft {
  transcript: string;
  title: string | null;
  district: string | null;
  price: number | null;
  room_count: string | null;
  square_meters: number | null;
}

export type LeadStatus = "new" | "contacted" | "viewing" | "negotiation" | "won" | "lost";

export interface Lead {
  id: string;
  source: string;
  status: LeadStatus;
  contact_phone: string;
  district: string | null;
  budget_min: number | null;
  budget_max: number | null;
  room_count: string | null;
  radius_km: number | null;
  message_count: number;
  last_contacted_at: string | null;
  auto_follow_up_enabled: boolean;
  follow_up_stage: number;
  next_follow_up_at: string | null;
  reminder_at: string | null;
  reminder_note: string | null;
  appointment_at: string | null;
  appointment_location: string | null;
  deal_amount: number | null;
  commission_amount: number | null;
  deal_closed_at: string | null;
  fields_extracted_by_ai: boolean;
  created_at: string;
}

export interface LeadUpdatePayload {
  district?: string | null;
  budget_min?: number | null;
  budget_max?: number | null;
  room_count?: string | null;
  radius_km?: number | null;
}

export interface WhatsAppMessage {
  id: string;
  lead_id: string;
  direction: "in" | "out";
  message_type: string;
  body: string | null;
  created_at: string;
}

export interface LeadFieldExtractionDraft {
  district: string | null;
  budget_min: number | null;
  budget_max: number | null;
  room_count: string | null;
  radius_km: number | null;
}

export interface SuggestReplyResult {
  draft: string;
  match_count: number;
}

export interface AppointmentResult {
  lead: Lead;
  whatsapp_confirmation_sent: boolean;
  whatsapp_confirmation_error: string | null;
}

export interface LeadVoiceNoteDraft {
  transcript: string;
  note_summary: string | null;
  suggested_status: LeadStatus | null;
  reminder_at: string | null;
  reminder_note: string | null;
}

export interface FollowUpResult {
  sent: boolean;
  message: string;
}

export interface LeadNote {
  id: string;
  lead_id: string;
  author_id: string;
  author_email: string | null;
  body: string;
  created_at: string;
}

export interface SendMatchesResult {
  sent: boolean;
  match_count: number;
  message: string;
}

export interface MatchResult {
  listing_id: string;
  title: string;
  price: number;
  match_reason: string;
}

export interface LeadScore {
  id: string;
  lead_id: string;
  score: number;
  score_breakdown: Record<string, unknown>;
  computed_at: string;
}

export interface DistrictCount {
  district: string;
  count: number;
}

export interface ScoreBucket {
  label: string;
  count: number;
}

export interface DistrictRevenue {
  district: string;
  revenue: number;
}

export interface ReportsOverview {
  listing_count: number;
  active_listing_count: number;
  listings_by_district: DistrictCount[];
  lead_count: number;
  leads_by_source: Record<string, number>;
  leads_by_district: DistrictCount[];
  leads_by_status: Record<string, number>;
  won_lead_count: number;
  active_follow_up_count: number;
  scored_lead_count: number;
  average_score: number | null;
  score_distribution: ScoreBucket[];
  conversion_rate: number | null;
  closed_deal_count: number;
  total_deal_volume: number;
  total_revenue: number;
  average_commission: number | null;
  revenue_by_district: DistrictRevenue[];
}

export interface PlanInfo {
  id: string;
  name: string;
  monthly_price: number;
  features: string[];
  is_current: boolean;
}

export interface CheckoutResult {
  payment_page_url: string;
}

export interface PricingSuggestion {
  has_enough_data: boolean;
  comparable_count: number;
  message: string | null;
  suggested_min: number | null;
  suggested_max: number | null;
  comparables: Array<{ title: string; price: number; district: string; room_count: string }>;
}

export interface PublicListing {
  id: string;
  title: string;
  district: string;
  price: number;
  room_count: string;
  square_meters: number | null;
  photos: string[];
  office_name: string;
}

export interface ListingViewStats {
  view_count: number;
  last_viewed_at: string | null;
}

export interface StaleListingAlert {
  listing_id: string;
  title: string;
  district: string;
  price: number;
  age_days: number;
  suggested_max: number;
  overprice_pct: number;
  message: string;
}

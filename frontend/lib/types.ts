export interface Office {
  id: string;
  name: string;
  subscription_plan: string;
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

export interface Lead {
  id: string;
  source: string;
  contact_phone: string;
  district: string | null;
  budget_min: number | null;
  budget_max: number | null;
  room_count: string | null;
  radius_km: number | null;
  message_count: number;
  last_contacted_at: string | null;
  created_at: string;
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

export interface PricingSuggestion {
  has_enough_data: boolean;
  comparable_count: number;
  message: string | null;
  suggested_min: number | null;
  suggested_max: number | null;
  comparables: Array<{ title: string; price: number; district: string; room_count: string }>;
}

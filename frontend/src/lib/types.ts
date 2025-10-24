export interface User {
  id: string;
  email: string;
  role: string;
  status?: string;
  is_premium?: boolean;
  created_at: string;
  last_login?: string | null;
  persist_search_results: boolean;
  first_name?: string;
  last_name?: string;
  linkedin_url?: string;
}

export interface Connection {
  id: string;
  // Personal Information
  first_name: string;
  last_name: string;
  linkedin_url?: string | null;
  profile_picture?: string | null;
  email_address?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  followers?: string | null;
  description?: string | null;
  headline?: string | null;
  rating?: number | null;

  // Connection Information
  connected_on?: string | null;
  
  // Boolean Flags
  is_creator?: boolean | null;
  is_hiring?: boolean | null;
  is_influencer?: boolean | null;
  is_open_to_work?: boolean | null;
  is_premium?: boolean | null;
  is_top_voice?: boolean | null;

  // Current Company Information
  company?: string | null;
  title?: string | null;
  
  // Company Details
  company_size?: string | null;
  company_name?: string | null;
  company_website?: string | null;
  company_phone?: string | null;
  company_industry?: string | null;
  company_industry_topics?: string | null;
  company_description?: string | null;
  company_address?: string | null;
  company_city?: string | null;
  company_state?: string | null;
  company_country?: string | null;
  company_revenue?: string | null;
  company_latest_funding?: string | null;
  company_linkedin?: string | null;
}

export interface SearchFilters {
  industries?: string[];
  company_sizes?: string[];
  locations?: string[];
  date_range_start?: string;
  date_range_end?: string;
  min_followers?: number;
  max_followers?: number;
}

export interface SearchRequest {
  query: string;
  filters?: SearchFilters;
}

export interface SearchResult {
  connection: Connection;
  score: number;
  summary: string;
  pros: string[];
  cons: string[];
}

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  filters?: SearchFilters;
  created_at: string;
}
 
 export interface SearchHistory {
  id: string;
  query: string;
  filters?: SearchFilters;
  results_count: number;
  searched_at: string;
}

export interface FavoriteConnection {
  favorite_id: string;
  favorited_at: string;
  connection: Connection;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isLoggedIn: boolean;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}
export interface GeneratedEmail {
  id: string;
  connection_id: string;
  reason_for_connecting: string;
  generated_content: string;
  created_at: string;
}

export interface Tip {
  id: string;
  connection_id: string;
  amount: number;
  message?: string;
  created_at: string;
  transaction_id?: string;
}

export enum WarmIntroStatus {
    pending = "pending",
    connected = "connected",
    declined = "declined",
}

export interface WarmIntroRequest {
  id: string;
  requester_name: string;
  connection_name: string;
  requester_first_name?: string | null;
  requester_last_name?: string | null;
  connection_first_name?: string | null;
  connection_last_name?: string | null;
  connection_linkedin_url?: string | null;
  connection_email?: string | null;
  reason?: string | null;
  about?: string | null;
  requester_linkedin_url?: string | null;
  status: WarmIntroStatus;
  outcome?: string | null;
  outcome_date?: string | null;
  created_at: string;
  updated_at: string;
  connected_date?: string | null;
  declined_date?: string | null;
}

export interface WarmIntroStatusCounts {
  total: number;
  pending: number;
  connected: number;
  declined: number;
}

export interface PaginatedWarmIntroRequests {
  items: WarmIntroRequest[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  status_counts: WarmIntroStatusCounts;
}

// Access Request types
export interface AccessRequest {
  id: string;
  email: string;
  full_name: string;
  reason?: string;
  organization?: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  processed_at?: string;
}

export interface AccessRequestCreate {
  email: string;
  full_name: string;
  reason?: string;
  organization?: string;
}

// Password Reset types
export interface PasswordResetToken {
  reset_token: string;
  token_type: string;
}

export interface PasswordResetRequest {
  new_password: string;
  reset_token: string;
}
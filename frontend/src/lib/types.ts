export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Connection {
  id: string;
  // Personal Information
  first_name: string;
  last_name: string;
  linkedin_url?: string | null;
  email_address?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  followers?: string | null;
  description?: string | null;
  
  // Connection Information
  connected_on?: string | null;
  
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
  updated_at: string;
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
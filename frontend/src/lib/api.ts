import {
  WarmIntroStatus,
  WarmIntroRequest,
  PaginatedWarmIntroRequests,
  GeneratedEmail,
  SearchResult,
  SavedSearch,
  FavoriteConnection,
  Connection,
  SearchHistory
} from "./types";

// Simple and reliable API base URL configuration
const getApiBaseUrl = (): string => {
  // Always prefer explicit environment variable
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    // Remove /api/v1 suffix if it exists to avoid duplication
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    return baseUrl.replace(/\/api\/v1$/, '');
  }
  
  // Simple production check
  if (typeof window !== 'undefined' && window.location.hostname.includes('superconnectai.com')) {
    return 'https://api.superconnectai.com';
  }
  
  // Default to localhost for development
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

// Enhanced error handling wrapper
const handleApiError = (error: unknown, context: string): never => {
  console.error(`API Error in ${context}:`, error);
  console.error('Current API_BASE_URL:', API_BASE_URL);
  
  if (error instanceof Error) {
    // Add more context to network errors
    if (error.message.includes('fetch')) {
      throw new Error(`Network error in ${context}: ${error.message}. Check if API server is running at ${API_BASE_URL}`);
    }
    throw error;
  }
  
  throw new Error(`Unknown error in ${context}: ${String(error)}`);
};

export async function getPopulatedEmailTemplate(
  warmIntroRequestId: string,
  token: string
): Promise<{ success: boolean; template: string; subject: string; message?: string }> {
  try {
    console.log('🚀 API: Calling populate-template endpoint for request ID:', warmIntroRequestId);
    const response = await fetch(`${API_BASE_URL}/api/v1/populate-template`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        warm_intro_request_id: warmIntroRequestId
      }),
    });

    console.log('📧 API: Response status:', response.status);
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ API: Response error:', errorText);
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ API: Response data:', result);
    return result;
  } catch (error) {
    console.error('❌ API: Error in getPopulatedEmailTemplate:', error);
    return handleApiError(error, "getPopulatedEmailTemplate");
  }
}

export async function createWarmIntroRequest(
  requesterName: string,
  connectionName: string,
  status: WarmIntroStatus = WarmIntroStatus.pending,
  token: string,
  connectionLinkedinUrl?: string,
  connectionEmail?: string,
  reason?: string,
  about?: string,
  requesterLinkedinUrl?: string
): Promise<WarmIntroRequest> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/warm-intro-requests/`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        requester_name: requesterName,
        connection_name: connectionName,
        status: status,
        connection_linkedin_url: connectionLinkedinUrl,
        connection_email: connectionEmail,
        reason: reason,
        about: about,
        requester_linkedin_url: requesterLinkedinUrl
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "createWarmIntroRequest");
  }
}

export async function updateWarmIntroRequestStatus(
    requestId: string,
    status: WarmIntroStatus,
    token: string,
    connectedDate?: string,
    declinedDate?: string,
    outcome?: string | null,
    outcomeDate?: string | null
): Promise<WarmIntroRequest> {
    try {
        const body: { status: WarmIntroStatus; connected_date?: string; declined_date?: string; outcome?: string | null; outcome_date?: string | null } = { status };
        
        if (connectedDate) {
            body.connected_date = connectedDate;
        }
        
        if (declinedDate) {
            body.declined_date = declinedDate;
        }
        
        if (outcome !== undefined) {
            body.outcome = outcome;
        }
        
        if (outcomeDate !== undefined) {
            body.outcome_date = outcomeDate;
        }

        const response = await fetch(`${API_BASE_URL}/api/v1/warm-intro-requests/${requestId}/status`, {
            method: "PATCH",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
      return handleApiError(error, "updateWarmIntroRequestStatus");
    }
}

export async function getWarmIntroRequests(
  token: string,
  page: number = 1,
  limit: number = 10,
  status?: WarmIntroStatus
): Promise<PaginatedWarmIntroRequests> {
  try {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });
    
    if (status) {
      params.append('status', status);
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/warm-intro-requests/?${params}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "getWarmIntroRequests");
  }
}

export async function getWarmIntroRequestById(
  requestId: string,
  token: string
): Promise<WarmIntroRequest> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/warm-intro-requests/${requestId}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to fetch warm intro request:", error);
    throw error;
  }
}

async function uploadConnectionsCSV(file: File, token: string): Promise<{ message: string; uploaded_count: number }> {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/v1/connections/upload`, {
      method: "POST",
      body: formData,
      headers: {
        "Authorization": `Bearer ${token}`,
        // Don't set Content-Type - browser will automatically set it with boundary
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to upload connections CSV:", error);
    throw error;
  }
}

async function deleteConnections(token: string): Promise<{ message: string; deleted_count: number }> {
  try {
    const response = await fetch(`/api/delete`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ connectionIds: [] }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to delete connections:", error);
    throw error;
  }
}

async function clearPineconeData(token: string): Promise<{ message: string }> {
  try {
    const response = await fetch(`/api/clear-pinecone`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to clear Pinecone data:", error);
    throw error;
  }
}

// Real authentication implementations
export async function loginUser(email: string, password: string): Promise<{ access_token: string; token_type: string } | { reset_token: string; token_type: string }> {
  try {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      // Simple error handling for authentication
      if (response.status === 401) {
        throw new Error('Invalid email or password');
      }
      
      // Try to get server error message
      try {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Login failed with status: ${response.status}`);
      } catch {
        throw new Error(`Login failed with status: ${response.status}`);
      }
    }

    return await response.json();
  } catch (error) {
    // Re-throw the error as-is for proper handling by the UI
    throw error;
  }
}

export async function registerUser(
  email: string,
  password: string,
  name: string
): Promise<{ id: string; email: string; name: string; created_at: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
        name
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to register:", error);
    throw error;
  }
}

export async function getGeneratedEmails(
  token: string
): Promise<GeneratedEmail[]> {
  // Mock implementation - replace with actual API call when backend is ready
  console.log(token); // Prevent unused parameter error
  return Promise.resolve([]);
}

export async function getUserProfile(token: string): Promise<{ id: string; email: string; role: string; status: string; is_premium: boolean; created_at: string; last_login?: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/users/me`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "getUserProfile");
  }
}

export async function searchConnectionsWithProgress(
  searchRequest: { query: string; filters?: Record<string, unknown> },
  token: string,
  onProgress?: (progress: number) => void
): Promise<SearchResult[]> {
  try {
    if (onProgress) {
      onProgress(10);
    }

    // Production fallback: Try regular search endpoint if SSE fails
    const useSSE = true;
    let response: Response;

    if (useSSE) {
      response = await fetch(`${API_BASE_URL}/api/v1/search/progress`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
          "Cache-Control": "no-cache",
        },
        body: JSON.stringify(searchRequest),
      });
    } else {
      response = await fetch(`${API_BASE_URL}/api/v1/search`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(searchRequest),
      });
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // For non-SSE response, parse JSON directly
    if (!useSSE || !response.headers.get('content-type')?.includes('text/event-stream')) {
      const results = await response.json();
      if (onProgress) onProgress(100);
      return results;
    }

    // Handle Server-Sent Events for progress updates
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let results: SearchResult[] = [];
    let buffer = '';

    // Set a timeout for SSE response
    const SSE_TIMEOUT = 600000; // 10 minutes (600 seconds) to accommodate long AI processing
    let timeoutId: NodeJS.Timeout | null = null;
    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error('SSE stream timeout'));
      }, SSE_TIMEOUT);
    });

    try {
      if (reader) {
        await Promise.race([
          (async () => {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              
              // Process complete lines
              let newlineIndex;
              while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
                const line = buffer.slice(0, newlineIndex).trim();
                buffer = buffer.slice(newlineIndex + 1);

                if (line.startsWith('data: ')) {
                  try {
                    const jsonData = line.slice(6).trim();
                    
                    if (jsonData && jsonData !== '') {
                      const data = JSON.parse(jsonData) as {
                        progress?: number;
                        results?: SearchResult[];
                        error?: string;
                        message?: string;
                      };
                      
                      if (typeof data.progress === 'number' && onProgress) {
                        onProgress(Math.min(data.progress, 100));
                      }
                      
                      if (data.results && Array.isArray(data.results) && data.results.length > 0) {
                        results = data.results;
                        // If we have results and progress is 100, we're done
                        if (data.progress === 100) {
                          if (timeoutId) clearTimeout(timeoutId);
                          return;
                        }
                      }
                      
                      if (data.error) {
                        throw new Error(data.error);
                      }
                    }
                  } catch (parseError) {
                    console.warn('Failed to parse SSE data:', parseError, 'Line:', line);
                    // Continue processing other lines instead of breaking
                  }
                }
              }
            }
          })(),
          timeoutPromise
        ]);
      }
    } catch (error) {
      if (timeoutId) clearTimeout(timeoutId);
      if (error instanceof Error && error.message === 'SSE stream timeout') {
        console.warn('SSE timeout, falling back to regular search');
        // Fallback to regular search endpoint
        try {
          const fallbackResponse = await fetch(`${API_BASE_URL}/api/v1/search`, {
            method: "POST",
            headers: {
              "Authorization": `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(searchRequest),
          });
          
          if (fallbackResponse.ok) {
            const fallbackResults = await fallbackResponse.json();
            if (onProgress) onProgress(100);
            return fallbackResults;
          }
        } catch (fallbackError) {
          console.error('Fallback search also failed:', fallbackError);
        }
      }
      throw error;
    }

    if (timeoutId) clearTimeout(timeoutId);
    return results;
  } catch (error) {
    console.error("Failed to search connections:", error);
    throw error;
  }
}

export async function getConnectionsCount(token: string): Promise<{ count: number }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/connections/count`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to get connections count:", error);
    throw error;
  }
}

export async function getPineconeVectorCount(token: string): Promise<{ 
  count: number; 
  admin_vectors: number; 
  source: string; 
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/connections/pinecone-count`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to get Pinecone vector count:", error);
    throw error;
  }
}

export async function createSavedSearch(
  name: string,
  query: string,
  filters: Record<string, unknown> | undefined,
  token: string
): Promise<SavedSearch> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/saved-searches/`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        query,
        filters
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to create saved search:", error);
    throw error;
  }
}

export async function addFavoriteConnection(
  connectionId: string,
  token: string
): Promise<FavoriteConnection> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/favorites/`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        connection_id: connectionId
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to add favorite connection:", error);
    throw error;
  }
}

export async function generateEmail(
  connectionId: string,
  prompt: string,
  token: string
): Promise<{ subject: string; body: string; generated_at: string }> {
  // Mock implementation - replace with actual API call when backend is ready
  console.log(connectionId, prompt, token); // Prevent unused parameter error
  return Promise.resolve({
    subject: "Introduction Request",
    body: "This is a generated email body based on your prompt.",
    generated_at: new Date().toISOString()
  });
}

// Additional missing API functions
export async function getConnections(
  token: string,
  page: number = 1,
  limit: number = 10
): Promise<{ items: Connection[]; total: number; page: number; limit: number; total_pages: number }> {
  // Mock implementation - replace with actual API call when backend is ready
  return Promise.resolve({
    items: [],
    total: 0,
    page,
    limit,
    total_pages: 0
  });
}

export async function getSavedSearches(
  token: string
): Promise<SavedSearch[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/saved-searches`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "getSavedSearches");
  }
}

export async function deleteSavedSearch(
  searchId: string,
  token: string
): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/saved-searches/${searchId}`, {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return { success: true };
  } catch (error) {
    console.error("Failed to delete saved search:", error);
    throw error;
  }
}

export async function getSearchHistory(
  token: string
): Promise<SearchHistory[]> {
  // Mock implementation - replace with actual API call when backend is ready
  console.log(token); // Prevent unused parameter error
  return Promise.resolve([]);
}

export async function clearSearchHistory(token: string): Promise<{ success: boolean }> {
  // Mock implementation - replace with actual API call when backend is ready
  console.log(token); // Prevent unused parameter error
  return Promise.resolve({ success: true });
}

export async function deleteSearchHistoryEntry(
  entryId: string,
  token: string
): Promise<{ success: boolean }> {
  // Mock implementation - replace with actual API call when backend is ready
  console.log(entryId, token); // Prevent unused parameter error
  return Promise.resolve({ success: true });
}

export async function getFavoriteConnections(
  token: string
): Promise<FavoriteConnection[]> {
  // Mock implementation - replace with actual API call when backend is ready
  console.log(token); // Prevent unused parameter error
  return Promise.resolve([]);
}

export async function removeFavoriteConnection(
  connectionId: string,
): Promise<{ id: string; favorited: boolean }> {
  // Mock implementation - replace with actual API call when backend is ready
  return Promise.resolve({
    id: connectionId,
    favorited: false
  });
}

export async function getTippingHistory(
  token: string,
  page: number = 1,
  limit: number = 10
): Promise<{ items: unknown[]; total: number; page: number; limit: number; total_pages: number }> {
  // Mock implementation - replace with actual API call when backend is ready
  return Promise.resolve({
    items: [],
    total: 0,
    page,
    limit,
    total_pages: 0
  });
}

export async function exportConnectedRequestsCSV(token: string): Promise<Blob> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/warm-intro-requests/export/csv`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.blob();
  } catch (error) {
    console.error("Failed to export connected requests CSV:", error);
    throw error;
  }
}

export async function getFilterOptions(token: string): Promise<{
  countries: string[];
  open_to_work_count: number;
  total_connections: number;
  generated_from: string;
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/filter-options`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "getFilterOptions");
  }
}

// Access Request API functions
export async function submitAccessRequest(
  requestData: {
    email: string;
    full_name: string;
    reason?: string;
    organization?: string;
  }
): Promise<{
  id: string;
  email: string;
  full_name: string;
  reason?: string;
  organization?: string;
  status: string;
  created_at: string;
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/access-requests`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "submitAccessRequest");
  }
}

export async function getAccessRequests(
  token: string,
  statusFilter?: string
): Promise<{
  id: string;
  email: string;
  full_name: string;
  reason?: string;
  organization?: string;
  status: string;
  created_at: string;
  processed_at?: string;
}[]> {
  try {
    const params = new URLSearchParams();
    if (statusFilter) {
      params.append('status_filter', statusFilter);
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/admin/access-requests?${params}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "getAccessRequests");
  }
}

export async function approveAccessRequest(
  requestId: string,
  token: string
): Promise<{
  user: {
    id: string;
    email: string;
    role: string;
    status: string;
    is_premium: boolean;
    must_change_password: boolean;
    created_at: string;
    last_login?: string;
    otp: string;
  };
  message: string;
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/admin/access-requests/${requestId}/approve`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "approveAccessRequest");
  }
}

export async function denyAccessRequest(
  requestId: string,
  token: string,
  adminNotes?: string
): Promise<{
  request: {
    id: string;
    email: string;
    full_name: string;
    reason?: string;
    organization?: string;
    status: string;
    created_at: string;
    processed_at?: string;
  };
  message: string;
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/admin/access-requests/${requestId}`, {
      method: "PATCH",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        status: "rejected",
        admin_notes: adminNotes
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "denyAccessRequest");
  }
}

// Password Reset API functions
export async function resetPassword(
  resetToken: string,
  newPassword: string
): Promise<{ access_token: string; token_type: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/reset-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        reset_token: resetToken,
        new_password: newPassword
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "resetPassword");
  }
}

// Dashboard Stats API functions
export async function getPendingCounts(token: string): Promise<{
  warm_intro_requests: number;
  follow_up_emails: number;
  access_requests: number;
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/dashboard/pending-counts`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "getPendingCounts");
  }
}

// Last Search Results API functions
export async function getLastSearchResults(token: string): Promise<{
  has_results: boolean;
  data?: {
    query: string;
    filters?: Record<string, unknown>;
    results: SearchResult[];
    results_count: number;
    page: number;
    page_size: number;
    created_at: string;
    updated_at: string;
  };
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/last-search-results`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "getLastSearchResults");
  }
}

export async function clearLastSearchResults(token: string): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/last-search-results`, {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return { success: true };
  } catch (error) {
    console.error("Failed to clear last search results:", error);
    throw error;
  }
}

export async function checkLastSearchResultsExist(token: string): Promise<{ has_results: boolean }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/last-search-results/exists`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "checkLastSearchResultsExist");
  }
}

export async function updateUserPreferences(
  token: string,
  preferences: { persist_search_results: boolean }
): Promise<{ persist_search_results: boolean }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/user_preferences/preferences`, {
      method: "PUT",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(preferences),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    return handleApiError(error, "updateUserPreferences");
  }
}

export { uploadConnectionsCSV, deleteConnections, clearPineconeData };
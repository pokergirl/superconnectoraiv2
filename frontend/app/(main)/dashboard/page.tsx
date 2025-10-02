'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { searchConnectionsWithProgress, getConnectionsCount, createSavedSearch, getLastSearchResults, clearLastSearchResults } from '@/lib/api';
import { SearchResult, Connection } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { AutoExpandingTextarea } from '@/components/ui/auto-expanding-textarea';
import { Progress } from '@/components/ui/progress';
import { Badge } from '../../../src/components/ui/badge';
import { User, Linkedin, Loader2, X, Mail, Clock } from 'lucide-react';
import Image from 'next/image';
import { EmailGenerationModal } from '@/components/shared/EmailGenerationModal';
import { TippingModal } from '@/components/shared/TippingModal';
import { TippingBanner } from '@/components/shared/TippingBanner';
import EnhancedWarmIntroModal from '@/components/shared/EnhancedWarmIntroModal';
import SearchFiltersComponent, { SearchFilters } from '@/components/shared/SearchFilters';
import ConnectionStrengthIndicator from '@/components/shared/ConnectionStrengthIndicator';
import SavedSearches from '@/components/shared/SavedSearches';

export default function DashboardPage() {
  const { token, user } = useAuth();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTippingModalOpen, setIsTippingModalOpen] = useState(false);
  const [isWarmIntroModalOpen, setIsWarmIntroModalOpen] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<Connection | null>(null);
  const [connectionsCount, setConnectionsCount] = useState<number | null>(null);
  const [showTippingBanner, setShowTippingBanner] = useState(false);
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [animatedProgress, setAnimatedProgress] = useState(0);
  const [searchFilters, setSearchFilters] = useState<SearchFilters>({});
  const [persistedResults, setPersistedResults] = useState<SearchResult[]>([]);
  const [persistedQuery, setPersistedQuery] = useState('');
  const [filtersChanged, setFiltersChanged] = useState(false);
  
  // Mock facilitator profile - in a real app, this would come from the user's profile
  const facilitatorProfile = {
    companies: ['Google', 'Microsoft', 'Apple', 'Meta', 'Amazon'],
    schools: ['Stanford University', 'MIT', 'Harvard', 'UC Berkeley'],
    location: 'San Francisco Bay Area'
  };

  useEffect(() => {
    if (token) {
      getConnectionsCount(token)
        .then(data => setConnectionsCount(data.count))
        .catch(err => console.error("Failed to fetch connections count:", err));
      
    }
  }, [token, user?.role]);


  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (loading) {
      setAnimatedProgress(0);
      interval = setInterval(() => {
        setAnimatedProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            return 100;
          }
          return prev + 100 / 60;
        });
      }, 1000);
    }
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [loading]);

 // Load persisted search results on component mount
 useEffect(() => {
   if (!token || !user?.id) return; // Don't load persisted data without user context and token
   
   const loadLastSearchResults = async () => {
     try {
       const lastSearchData = await getLastSearchResults(token);
       
       if (lastSearchData.has_results && lastSearchData.data) {
         const { query: savedQuery, filters: savedFilters, results: savedResults } = lastSearchData.data;
         
         setPersistedResults(savedResults);
         setPersistedQuery(savedQuery);
         setQuery(savedQuery);
         setHasSearched(true);
         setResults(savedResults);
         
         if (savedFilters) {
           setSearchFilters(savedFilters);
         }
       }
     } catch (error) {
       console.error('Failed to load last search results:', error);
       // Fallback to localStorage for backward compatibility
       const userPrefix = `user_${user.id}_`;
       const savedResults = localStorage.getItem(`${userPrefix}superconnect_search_results`);
       const savedQuery = localStorage.getItem(`${userPrefix}superconnect_search_query`);
       const savedFilters = localStorage.getItem(`${userPrefix}superconnect_search_filters`);
       
       if (savedResults && savedQuery) {
         try {
           setPersistedResults(JSON.parse(savedResults));
           setPersistedQuery(savedQuery);
           setQuery(savedQuery);
           setHasSearched(true);
           setResults(JSON.parse(savedResults));
           
           if (savedFilters) {
             setSearchFilters(JSON.parse(savedFilters));
           }
         } catch (parseError) {
           console.error('Failed to load persisted search results from localStorage:', parseError);
         }
       }
     }
   };
   
   loadLastSearchResults();
 }, [token, user?.id]);
 
   const handleSearch = async (e: React.FormEvent) => {
     e.preventDefault();
    if (!query.trim()) {
      setError('Please enter a search query.');
      return;
    }
    
    if (!token) {
      setError('Authentication token is not available. Please log in again.');
      return;
    }

    setLoading(true);
    setError(null);
    setHasSearched(true);
    setResults([]);
    setFiltersChanged(false); // Reset filters changed flag when new search is performed

    try {
      const searchResults = await searchConnectionsWithProgress(
        {
          query: query.trim(),
          filters: Object.keys(searchFilters).length > 0 ? searchFilters as Record<string, unknown> : undefined
        },
        token,
        () => {
          // Progress callback - no longer tracking progress
        }
      );
      setResults(searchResults);
      if (searchResults.some(result => result.score >= 9)) {
        setShowTippingBanner(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const openWarmIntroModal = (connection: Connection) => {
    setSelectedConnection(connection);
    setIsWarmIntroModalOpen(true);
  };

  const handleWarmIntroSuccess = () => {
    // Show success message and tipping banner
    setSuccessMessage('Your request has been submitted for review');
    setShowSuccessMessage(true);
    setShowTippingBanner(true);
    setIsWarmIntroModalOpen(false);
    
    // Auto-hide success message after 5 seconds
    setTimeout(() => {
      setShowSuccessMessage(false);
    }, 5000);
  };


  const openTippingModal = (connection: Connection) => {
    setSelectedConnection(connection);
    setIsTippingModalOpen(true);
  };

  const handleSupportClick = () => {
    const topMatch = results.find(result => result.score >= 9)?.connection;
    if (topMatch) {
      openTippingModal(topMatch);
    }
  };
 
   const handleSaveSearch = async () => {
    if (!query.trim()) {
      setError('Cannot save an empty search.');
      return;
    }
    
    if (!token) {
      setError('Authentication token is not available. Please log in again.');
      return;
    }
    const searchName = prompt('Enter a name for this search:');
    if (searchName && token) {
      try {
        await createSavedSearch(searchName, query.trim(), {}, token);
        alert('Search saved successfully!');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to save search');
      }
    }
  };

 const handleRunSavedSearch = (savedQuery: string, savedFilters?: any) => {
   setQuery(savedQuery);
   if (savedFilters) {
     setSearchFilters(savedFilters);
   }
   // Trigger search automatically
   if (savedQuery.trim() && token) {
     setLoading(true);
     setError(null);
     setHasSearched(true);
     setResults([]);

     searchConnectionsWithProgress(
       {
         query: savedQuery.trim(),
         filters: savedFilters && Object.keys(savedFilters).length > 0 ? savedFilters : undefined
       },
       token,
       () => {
         // Progress callback
       }
     ).then(searchResults => {
       setResults(searchResults);
       if (searchResults.some(result => result.score >= 9)) {
         setShowTippingBanner(true);
       }
     }).catch(err => {
       setError(err instanceof Error ? err.message : 'Search failed');
       setResults([]);
     }).finally(() => {
       setLoading(false);
     });
   }
 };

 const handleFiltersChange = (newFilters: SearchFilters) => {
   setSearchFilters(newFilters);
   // Mark that filters have changed since last search
   if (hasSearched && results.length > 0) {
     setFiltersChanged(true);
     setError('Filters updated. Click "Search" to apply filters to your results.');
   }
 };

 const handleClearFilters = () => {
   setSearchFilters({});
   // Don't automatically trigger search when clearing filters
   // User needs to manually search after clearing
 };

 const clearPersistedResults = async () => {
   try {
     if (token) {
       await clearLastSearchResults(token);
     }
   } catch (error) {
     console.error('Failed to clear last search results from server:', error);
   }
   
   // Also clear localStorage for backward compatibility
   if (user?.id) {
     const userPrefix = `user_${user.id}_`;
     localStorage.removeItem(`${userPrefix}superconnect_search_results`);
     localStorage.removeItem(`${userPrefix}superconnect_search_query`);
     localStorage.removeItem(`${userPrefix}superconnect_search_filters`);
   }
   
   setResults([]);
   setQuery('');
   setSearchFilters({});
   setHasSearched(false);
   setPersistedResults([]);
   setPersistedQuery('');
 };

 
   return (
     <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-6 py-12">

        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-6">Superconnect AI</h1>
          
          {/* Search Section */}
          <div className="bg-white rounded-lg shadow-sm border p-4 sm:p-8 mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-6 text-left">Search Connections</h2>
            
            {/* Getting Started Tips - Show when no search has been performed */}
            {!hasSearched && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="text-sm font-semibold text-blue-800 mb-3 text-left">💡 Getting Started Tips</h3>
                <div className="space-y-2 text-sm text-blue-700 text-left">
                  <p className="text-left">• Use natural language to describe who you're looking for</p>
                  <p className="text-left">• Try queries like "VCs who invest in seed stage consumer startups"</p>
                  <p className="text-left">• The AI will analyze your connections and provide detailed match analysis</p>
                  <p className="text-left">• Connections with scores 9-10 are marked as "Top Matches"</p>
                </div>
              </div>
            )}
            
            {/* Search Form */}
            <form onSubmit={handleSearch} className="space-y-4">
              <div className="flex flex-col sm:flex-row gap-3">
                <AutoExpandingTextarea
                  placeholder="Find me a VC who invests in seed stage consumer startups..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="flex-1 px-4 text-gray-700 text-sm sm:text-base border-gray-300 hover:border-blue-400 hover:shadow-md transition-all duration-200 focus:border-blue-500 focus:shadow-lg"
                  disabled={loading}
                />
                <Button
                  type="submit"
                  disabled={loading || !query.trim()}
                  className={`h-12 px-6 sm:px-8 w-full sm:w-auto ${
                    filtersChanged
                      ? 'bg-orange-600 hover:bg-orange-700 animate-pulse'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Searching...
                    </>
                  ) : filtersChanged ? (
                    'Search with New Filters'
                  ) : (
                    'Search'
                  )}
                </Button>
              </div>
              
              {/* Filters and Actions */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="flex flex-wrap gap-2">
                  <SearchFiltersComponent
                    filters={searchFilters}
                    onFiltersChange={handleFiltersChange}
                    onClearFilters={handleClearFilters}
                  />
                  {persistedResults.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={clearPersistedResults}
                      className="text-xs"
                    >
                      <X className="w-3 h-3 mr-1" />
                      Clear History
                    </Button>
                  )}
                </div>
                
                {/* Active Filters Display */}
                {Object.keys(searchFilters).length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="flex flex-wrap gap-1">
                      {searchFilters.open_to_work && (
                        <Badge variant="secondary" className="text-xs">Open to Work</Badge>
                      )}
                      {searchFilters.country && (
                        <Badge variant="secondary" className="text-xs">
                          📍 {searchFilters.country}
                        </Badge>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleClearFilters}
                      className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 h-auto"
                    >
                      <X className="w-3 h-3 mr-1" />
                      Clear Filters
                    </Button>
                  </div>
                )}
              </div>
            </form>
          </div>

          {/* Saved Searches Section */}
          <SavedSearches
            onRunSearch={handleRunSavedSearch}
            currentQuery={query}
            currentFilters={searchFilters}
          />
          {loading && (
            <div className="mt-6 mb-8 text-center bg-blue-50 border border-blue-200 rounded-lg p-6">
              <div className="max-w-md mx-auto">
                <p className="text-lg text-gray-800 mb-2 font-medium">
                  Got it! I&apos;m searching Ha&apos;s {connectionsCount?.toLocaleString() ?? ''} 1st degree connections (from LinkedIn).
                </p>
                <p className="text-sm text-gray-600 mb-4">
                  This search may take a few minutes so hang tight
                </p>
                <Progress value={animatedProgress} className="w-full mb-2" />
                <p className="text-sm text-center text-gray-600 font-medium">{Math.round(animatedProgress)}% complete</p>
              </div>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Success Message */}
        {showSuccessMessage && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center space-x-2">
              <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
              <p className="text-green-800 font-medium">{successMessage}</p>
              <button
                onClick={() => setShowSuccessMessage(false)}
                className="ml-auto text-green-600 hover:text-green-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Search Results */}
        {hasSearched && !loading && (
          <div className="space-y-6">
            {results.length > 0 && (
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <h2 className="text-xl font-semibold text-blue-600">
                  Found {results.length} relevant profiles
                </h2>
                <div className="flex gap-2">
                  <Button onClick={handleSaveSearch} variant="outline" size="sm">
                    Save Search
                  </Button>
                  {persistedResults.length > 0 && results !== persistedResults && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setResults(persistedResults);
                        setQuery(persistedQuery);
                      }}
                    >
                      Restore Previous
                    </Button>
                  )}
                </div>
              </div>
            )}

            {results.length === 0 && !error ? (
              <div className="text-center py-12 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="max-w-md mx-auto">
                  <div className="text-4xl mb-4">🔍</div>
                  <p className="text-gray-700 text-lg font-medium mb-2">No connections match your search criteria.</p>
                  <p className="text-gray-600 text-sm">Try adjusting your search terms, removing filters, or using different keywords.</p>
                </div>
              </div>
            ) : (
              results.map((result) => (
                <div key={result.connection.id} className="bg-white rounded-lg shadow-sm border p-4 sm:p-6">
                  {/* Header with avatar, name, and score */}
                  <div className="flex flex-col sm:flex-row items-start justify-between mb-4 gap-4">
                    <div className="flex items-start space-x-3 sm:space-x-4 flex-1">
                      {/* Avatar */}
                      <div className="w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center overflow-hidden flex-shrink-0">
                        {result.connection.profile_picture ? (
                          <Image
                            src={result.connection.profile_picture}
                            alt={`${result.connection.first_name} ${result.connection.last_name}`}
                            className="w-full h-full object-cover"
                            width={48}
                            height={48}
                            onError={(e) => {
                              // Fallback to initials if image fails to load
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                              const parent = target.parentElement;
                              if (parent) {
                                parent.innerHTML = `<span class="text-white font-semibold text-sm sm:text-lg">${result.connection.first_name?.[0] || ''}${result.connection.last_name?.[0] || ''}</span>`;
                              }
                            }}
                          />
                        ) : (
                          <span className="text-white font-semibold text-sm sm:text-lg">
                            {result.connection.first_name?.[0] || ''}{result.connection.last_name?.[0] || ''}
                          </span>
                        )}
                      </div>
                      
                      {/* Name and title */}
                      <div className="min-w-0 flex-1">
                        <h3 className="text-base sm:text-lg font-semibold text-gray-900 truncate">
                          {result.connection.first_name} {result.connection.last_name}
                        </h3>
                        {result.connection.company_name && (
                          <p className="text-sm sm:text-md font-semibold text-gray-800 mt-1 truncate">
                            {result.connection.company_name}
                          </p>
                        )}
                        <p className="text-sm sm:text-base text-gray-600 line-clamp-2">
                          {result.connection.headline || result.connection.title ? (
                            <>
                              {result.connection.headline}
                              {result.connection.headline && result.connection.title ? ' | ' : ''}
                              {result.connection.title}
                            </>
                          ) : (
                            'No headline or title available'
                          )}
                        </p>
                        {result.connection.email_address && (
                          <p className="text-xs text-gray-500 mt-1">
                            📧 {result.connection.email_address}
                          </p>
                        )}
                        {result.connection.connected_on && (
                          <p className="text-sm text-gray-500 mt-1">
                            Connected on {new Date(result.connection.connected_on).toLocaleDateString('en-US', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric'
                            })}
                          </p>
                        )}
                      </div>
                    </div>
                    
                    {/* Score and badges */}
                    <div className="flex items-center space-x-2 flex-shrink-0">
                      {result.score >= 9 && (
                        <Badge className="bg-yellow-500 hover:bg-yellow-600 text-white">
                          Top Match
                        </Badge>
                      )}
                      <div className="text-right">
                        <div className="text-xl sm:text-2xl font-bold text-blue-600">{result.score}</div>
                        <div className="text-xs text-gray-500">Relevance</div>
                      </div>
                    </div>
                  </div>

                  {/* Badges */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {result.connection.is_hiring && <Badge className="bg-green-500 hover:bg-green-600 text-white">Hiring</Badge>}
                    {result.connection.is_open_to_work && <Badge className="bg-teal-500 hover:bg-teal-600 text-white">Open to Work</Badge>}
                  </div>

                  {/* Connection Strength Indicator - TEMPORARILY HIDDEN FOR PRODUCTION */}
                  {/* TODO: Resurface this when ready to improve the connection strength feature */}
                  {/*
                  <div className="mb-4">
                    <ConnectionStrengthIndicator
                      connection={{
                        connected_on: result.connection.connected_on || undefined,
                        company_name: result.connection.company_name || undefined,
                        city: result.connection.city || undefined,
                        state: result.connection.state || undefined,
                        country: result.connection.country || undefined,
                        // Mock data for demonstration - in real app, this would come from the API
                        mutual_connections: Math.floor(Math.random() * 20) + 1,
                        shared_companies: result.connection.company_name ? [result.connection.company_name] : undefined,
                        interaction_frequency: ['high', 'medium', 'low'][Math.floor(Math.random() * 3)] as 'high' | 'medium' | 'low'
                      }}
                      facilitatorProfile={facilitatorProfile}
                    />
                  </div>
                  */}

                  {/* Summary */}
                  <p className="text-gray-700 mb-4">{result.summary}</p>

                  {/* Pros */}
                  {result.pros && result.pros.length > 0 && (
                    <div className="mb-4">
                      <h4 className="font-medium text-green-700 mb-2">Why this may be a good match:</h4>
                      <ul className="space-y-1">
                        {result.pros.map((pro, idx) => (
                          <li key={idx} className="text-sm text-gray-700 flex items-start">
                            <span className="text-green-600 mr-2">•</span>
                            {pro}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Cons */}
                  {result.cons && result.cons.length > 0 && (
                    <div className="mb-4">
                      <h4 className="font-medium text-red-700 mb-2">Why this may not be a good match:</h4>
                      <ul className="space-y-1">
                        {result.cons.map((con, idx) => (
                          <li key={idx} className="text-sm text-gray-700 flex items-start">
                            <span className="text-red-600 mr-2">•</span>
                            {con}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4 mt-6">
                    <Button
                      onClick={() => openWarmIntroModal(result.connection)}
                      className="bg-blue-600 hover:bg-blue-700 text-white w-full sm:w-auto cursor-pointer"
                      size="sm"
                    >
                      Request a Warm Intro
                    </Button>
                    {result.connection.linkedin_url && (
                      <a
                        href={result.connection.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-9 px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 w-full sm:w-auto"
                      >
                        <span className="inline-flex items-center justify-center w-6 h-6 mr-2 bg-blue-600 text-white text-xs font-bold rounded">
                          in
                        </span>
                        LinkedIn Profile
                      </a>
                    )}
                  </div>
                </div>
              ))
            )}
            {showTippingBanner && (
              <TippingBanner onSupportClick={handleSupportClick} />
            )}
          </div>
        )}

      </div>
      <EmailGenerationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        connection={selectedConnection}
      />
      <TippingModal
        isOpen={isTippingModalOpen}
        onClose={() => setIsTippingModalOpen(false)}
        connection={selectedConnection}
      />
      {selectedConnection && (
        <EnhancedWarmIntroModal
          isOpen={isWarmIntroModalOpen}
          onClose={() => setIsWarmIntroModalOpen(false)}
          onSuccess={handleWarmIntroSuccess}
          targetFirstName={selectedConnection.first_name}
          targetLastName={selectedConnection.last_name}
          theirCompany={selectedConnection.company_name || ''}
          linkedinUrl={selectedConnection.linkedin_url || undefined}
          profilePicture={selectedConnection.profile_picture || undefined}
        />
      )}
    </div>
  );
}
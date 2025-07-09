'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../src/context/AuthContext';
import { SearchHistory, SearchFilters } from '../../../src/lib/types';
import { getSearchHistory, deleteSearchHistoryEntry, clearSearchHistory } from '../../../src/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '../../../src/components/ui/badge';
import { Search, Trash2, Calendar, Filter, RotateCcw } from 'lucide-react';

export default function SearchHistoryPage() {
  const { token } = useAuth();
  const [searchHistory, setSearchHistory] = useState<SearchHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadSearchHistory = useCallback(async () => {
    try {
      const history = await getSearchHistory(token!, 50);
      setSearchHistory(history);
    } catch (error) {
      console.error('Failed to load search history:', error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      loadSearchHistory();
    }
  }, [token, loadSearchHistory]);

  const handleDeleteEntry = async (searchId: string) => {
    if (!confirm('Are you sure you want to delete this search history entry?')) return;
    
    try {
      await deleteSearchHistoryEntry(searchId, token!);
      setSearchHistory(prev => prev.filter(s => s.id !== searchId));
    } catch (error) {
      console.error('Failed to delete search history entry:', error);
    }
  };

  const handleClearHistory = async () => {
    if (!confirm('Are you sure you want to clear all search history? This action cannot be undone.')) return;
    
    try {
      await clearSearchHistory(token!);
      setSearchHistory([]);
    } catch (error) {
      console.error('Failed to clear search history:', error);
    }
  };

  const handleRepeatSearch = (historyEntry: SearchHistory) => {
    const searchRequest = {
      query: historyEntry.query,
      filters: historyEntry.filters
    };
    
    // Store the search request in sessionStorage and redirect to dashboard
    sessionStorage.setItem('pendingSearch', JSON.stringify(searchRequest));
    window.location.href = '/dashboard';
  };

  const filteredHistory = searchHistory.filter(entry =>
    entry.query.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatFilters = (filters?: SearchFilters) => {
    if (!filters) return [];
    
    const filterTexts = [];
    if (filters.industries?.length) filterTexts.push(`Industries: ${filters.industries.join(', ')}`);
    if (filters.company_sizes?.length) filterTexts.push(`Company Sizes: ${filters.company_sizes.join(', ')}`);
    if (filters.locations?.length) filterTexts.push(`Locations: ${filters.locations.join(', ')}`);
    if (filters.date_range_start || filters.date_range_end) {
      filterTexts.push(`Date Range: ${filters.date_range_start || 'Any'} - ${filters.date_range_end || 'Any'}`);
    }
    if (filters.min_followers || filters.max_followers) {
      filterTexts.push(`Followers: ${filters.min_followers || 0} - ${filters.max_followers || 'Max'}`);
    }
    
    return filterTexts;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading search history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Search History</h1>
              <p className="text-gray-600">Review and repeat your previous searches</p>
            </div>
            {searchHistory.length > 0 && (
              <Button
                variant="outline"
                onClick={handleClearHistory}
                className="text-red-600 hover:text-red-700 flex items-center space-x-2"
              >
                <Trash2 className="h-4 w-4" />
                <span>Clear All</span>
              </Button>
            )}
          </div>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              type="text"
              placeholder="Search history..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Search History List */}
        {filteredHistory.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchHistory.length === 0 ? 'No search history yet' : 'No searches match your filter'}
              </h3>
              <p className="text-gray-600 mb-6">
                {searchHistory.length === 0 
                  ? 'Start searching on the dashboard to build your search history.'
                  : 'Try adjusting your search terms.'
                }
              </p>
              <Button onClick={() => window.location.href = '/dashboard'}>
                Go to Dashboard
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {filteredHistory.map((entry) => (
              <Card key={entry.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg">&quot;{entry.query}&quot;</CardTitle>
                      <CardDescription className="mt-1">
                        {entry.results_count} result{entry.results_count !== 1 ? 's' : ''} found
                      </CardDescription>
                    </div>
                    <div className="flex items-center space-x-2 ml-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRepeatSearch(entry)}
                        className="flex items-center space-x-1"
                      >
                        <RotateCcw className="h-4 w-4" />
                        <span>Repeat</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteEntry(entry.id)}
                        className="text-red-600 hover:text-red-700 flex items-center space-x-1"
                      >
                        <Trash2 className="h-4 w-4" />
                        <span>Delete</span>
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Filters */}
                    {entry.filters && formatFilters(entry.filters).length > 0 && (
                      <div>
                        <div className="flex items-center space-x-2 mb-2">
                          <Filter className="h-4 w-4 text-gray-500" />
                          <span className="text-sm font-medium text-gray-700">Filters used:</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {formatFilters(entry.filters).map((filter, index) => (
                            <Badge key={index} variant="secondary" className="text-xs">
                              {filter}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Search Date */}
                    <div className="flex items-center space-x-1 text-sm text-gray-500">
                      <Calendar className="h-4 w-4" />
                      <span>Searched: {new Date(entry.searched_at).toLocaleString()}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
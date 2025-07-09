'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../src/context/AuthContext';
import { SavedSearch, SearchFilters } from '../../../src/lib/types';
import { getSavedSearches, deleteSavedSearch } from '../../../src/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '../../../src/components/ui/badge';
import { Search, Trash2, Play, Calendar, Filter } from 'lucide-react';

export default function SavedSearchesPage() {
  const { token } = useAuth();
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadSavedSearches = useCallback(async () => {
    try {
      const searches = await getSavedSearches(token!);
      setSavedSearches(searches);
    } catch (error) {
      console.error('Failed to load saved searches:', error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      loadSavedSearches();
    }
  }, [token, loadSavedSearches]);

  const handleDeleteSearch = async (searchId: string) => {
    if (!confirm('Are you sure you want to delete this saved search?')) return;
    
    try {
      await deleteSavedSearch(searchId, token!);
      setSavedSearches(prev => prev.filter(s => s.id !== searchId));
    } catch (error) {
      console.error('Failed to delete saved search:', error);
    }
  };

  const handleRunSearch = async (savedSearch: SavedSearch) => {
    try {
      const searchRequest = {
        query: savedSearch.query,
        filters: savedSearch.filters
      };
      
      // Store the search request in sessionStorage and redirect to dashboard
      sessionStorage.setItem('pendingSearch', JSON.stringify(searchRequest));
      window.location.href = '/dashboard';
    } catch (error) {
      console.error('Failed to run search:', error);
    }
  };

  const filteredSearches = savedSearches.filter(search =>
    search.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    search.query.toLowerCase().includes(searchTerm.toLowerCase())
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
          <p className="text-gray-600">Loading saved searches...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Saved Searches</h1>
          <p className="text-gray-600">Manage and run your saved search queries</p>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              type="text"
              placeholder="Search saved searches..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Saved Searches List */}
        {filteredSearches.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {savedSearches.length === 0 ? 'No saved searches yet' : 'No searches match your filter'}
              </h3>
              <p className="text-gray-600 mb-6">
                {savedSearches.length === 0 
                  ? 'Create your first saved search by performing a search on the dashboard and saving it.'
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
            {filteredSearches.map((savedSearch) => (
              <Card key={savedSearch.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg">{savedSearch.name}</CardTitle>
                      <CardDescription className="mt-1">
                        Query: &quot;{savedSearch.query}&quot;
                      </CardDescription>
                    </div>
                    <div className="flex items-center space-x-2 ml-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRunSearch(savedSearch)}
                        className="flex items-center space-x-1"
                      >
                        <Play className="h-4 w-4" />
                        <span>Run</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteSearch(savedSearch.id)}
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
                    {savedSearch.filters && formatFilters(savedSearch.filters).length > 0 && (
                      <div>
                        <div className="flex items-center space-x-2 mb-2">
                          <Filter className="h-4 w-4 text-gray-500" />
                          <span className="text-sm font-medium text-gray-700">Filters:</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {formatFilters(savedSearch.filters).map((filter, index) => (
                            <Badge key={index} variant="secondary" className="text-xs">
                              {filter}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Dates */}
                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>Created: {new Date(savedSearch.created_at).toLocaleDateString()}</span>
                      </div>
                      {savedSearch.updated_at !== savedSearch.created_at && (
                        <div className="flex items-center space-x-1">
                          <span>Updated: {new Date(savedSearch.updated_at).toLocaleDateString()}</span>
                        </div>
                      )}
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
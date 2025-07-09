'use client';

import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { searchConnections } from '@/lib/api';
import { SearchResult } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '../../../src/components/ui/badge';
import { User, Linkedin, Loader2 } from 'lucide-react';

export default function DashboardPage() {
  const { token } = useAuth();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !token) return;

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const searchResults = await searchConnections({ query: query.trim() }, token);
      setResults(searchResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleEmailConnection = (email: string | null | undefined, name: string) => {
    const subject = encodeURIComponent(`Connection from LinkedIn`);
    const body = encodeURIComponent(`Hi ${name},\n\nI hope this message finds you well. I wanted to reach out to connect and explore potential opportunities for collaboration.\n\nBest regards`);
    
    // Use email if available, otherwise leave To: field blank
    const toField = email ? email : '';
    window.open(`mailto:${toField}?subject=${subject}&body=${body}`, '_blank');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-6">SuperConnector AI</h1>
          
          {/* Search Section */}
          <div className="bg-white rounded-lg shadow-sm border p-8 mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-6 text-left">Search Connections</h2>
            
            <form onSubmit={handleSearch} className="flex gap-3">
              <Input
                type="text"
                placeholder="please find me a VC who invests in seed stage consumer startups."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 h-12 px-4 text-gray-700"
                disabled={loading}
              />
              <Button 
                type="submit" 
                disabled={loading || !query.trim()}
                className="h-12 px-8 bg-blue-600 hover:bg-blue-700"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  'Search'
                )}
              </Button>
            </form>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Search Results */}
        {hasSearched && !loading && (
          <div className="space-y-6">
            {results.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500 text-lg">No connections match your search criteria.</p>
                <p className="text-gray-400 mt-2">Try adjusting your search terms or uploading more connection data.</p>
              </div>
            ) : (
              results.map((result) => (
                <div key={result.connection.id} className="bg-white rounded-lg shadow-sm border p-6">
                  {/* Header with avatar, name, and score */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start space-x-4">
                      {/* Avatar */}
                      <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                        <User className="w-6 h-6 text-gray-500" />
                      </div>
                      
                      {/* Name and title */}
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {result.connection.first_name} {result.connection.last_name}
                        </h3>
                        <p className="text-gray-600">
                          {result.connection.title && result.connection.company ? (
                            `${result.connection.title} at ${result.connection.company}`
                          ) : result.connection.title || result.connection.company || (
                            'No company information available'
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
                    <div className="flex items-center space-x-2">
                      {result.score >= 9 && (
                        <Badge className="bg-yellow-500 hover:bg-yellow-600 text-white">
                          Top Match
                        </Badge>
                      )}
                      <div className="text-right">
                        <div className="text-2xl font-bold text-blue-600">{result.score.toFixed(1)}</div>
                        <div className="text-xs text-gray-500">Relevance</div>
                      </div>
                      {result.connection.linkedin_url && (
                        <Linkedin 
                          className="w-5 h-5 text-blue-600 cursor-pointer hover:text-blue-700"
                          onClick={() => window.open(result.connection.linkedin_url!, '_blank')}
                        />
                      )}
                    </div>
                  </div>

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

                  {/* Send Email Button */}
                  <Button
                    onClick={() => handleEmailConnection(
                      result.connection.email_address,
                      `${result.connection.first_name} ${result.connection.last_name}`
                    )}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    Send Email
                  </Button>
                </div>
              ))
            )}
          </div>
        )}

        {/* Getting Started */}
        {!hasSearched && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold mb-3">Getting Started</h3>
            <div className="space-y-2 text-sm text-gray-600">
              <p>• Use natural language to describe who you&apos;re looking for</p>
              <p>• Try queries like &quot;VCs who invest in seed stage consumer startups&quot;</p>
              <p>• The AI will analyze your connections and provide detailed match analysis</p>
              <p>• Connections with scores 9-10 are marked as &quot;Top Matches&quot;</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
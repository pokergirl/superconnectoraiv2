'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../../src/context/AuthContext';
import { FavoriteConnection } from '../../../src/lib/types';
import { getFavoriteConnections, removeFavoriteConnection } from '../../../src/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '../../../src/components/ui/badge';
import { Heart, Search, Trash2, User, Linkedin, Mail, MapPin, Building, Calendar } from 'lucide-react';

export default function FavoritesPage() {
  const { token } = useAuth();
  const [favorites, setFavorites] = useState<FavoriteConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const loadFavorites = useCallback(async () => {
    try {
      const favoritesData = await getFavoriteConnections(token!);
      setFavorites(favoritesData);
    } catch (error) {
      console.error('Failed to load favorites:', error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      loadFavorites();
    }
  }, [token, loadFavorites]);

  const handleRemoveFavorite = async (connectionId: string) => {
    if (!confirm('Are you sure you want to remove this connection from favorites?')) return;
    
    try {
      await removeFavoriteConnection(connectionId, token!);
      setFavorites(prev => prev.filter(f => f.connection.id !== connectionId));
    } catch (error) {
      console.error('Failed to remove favorite:', error);
    }
  };

  const filteredFavorites = favorites.filter(favorite =>
    `${favorite.connection.first_name} ${favorite.connection.last_name}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (favorite.connection.company && favorite.connection.company.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (favorite.connection.title && favorite.connection.title.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const openLinkedIn = (url?: string | null) => {
    if (url) {
      window.open(url, '_blank');
    }
  };

  const openEmail = (email?: string | null) => {
    if (email) {
      window.open(`mailto:${email}`, '_blank');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading favorite connections...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-2">
            <Heart className="h-8 w-8 text-red-500 fill-current" />
            <h1 className="text-3xl font-bold text-gray-900">Favorite Connections</h1>
          </div>
          <p className="text-gray-600">Your starred connections for quick access</p>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              type="text"
              placeholder="Search favorites..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Favorites Count */}
        {favorites.length > 0 && (
          <div className="mb-6">
            <p className="text-sm text-gray-600">
              {filteredFavorites.length} of {favorites.length} favorite connections
            </p>
          </div>
        )}

        {/* Favorites List */}
        {filteredFavorites.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <Heart className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {favorites.length === 0 ? 'No favorite connections yet' : 'No favorites match your search'}
              </h3>
              <p className="text-gray-600 mb-6">
                {favorites.length === 0 
                  ? 'Start adding connections to your favorites by clicking the heart icon on search results.'
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
            {filteredFavorites.map((favorite) => {
              const connection = favorite.connection;
              return (
                <Card key={favorite.favorite_id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4">
                        <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                          <User className="h-6 w-6 text-blue-600" />
                        </div>
                        <div>
                          <CardTitle className="text-xl">
                            {connection.first_name} {connection.last_name}
                          </CardTitle>
                          {connection.title && (
                            <CardDescription className="text-base">
                              {connection.title}
                              {connection.company && ` at ${connection.company}`}
                            </CardDescription>
                          )}
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRemoveFavorite(connection.id)}
                        className="text-red-600 hover:text-red-700 flex items-center space-x-1"
                      >
                        <Trash2 className="h-4 w-4" />
                        <span>Remove</span>
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Contact Information */}
                      <div className="flex flex-wrap gap-3">
                        {connection.linkedin_url && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openLinkedIn(connection.linkedin_url)}
                            className="flex items-center space-x-1"
                          >
                            <Linkedin className="h-4 w-4" />
                            <span>LinkedIn</span>
                          </Button>
                        )}
                        {connection.email_address && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openEmail(connection.email_address)}
                            className="flex items-center space-x-1"
                          >
                            <Mail className="h-4 w-4" />
                            <span>Email</span>
                          </Button>
                        )}
                      </div>

                      {/* Location and Company Info */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        {(connection.city || connection.state || connection.country) && (
                          <div className="flex items-center space-x-2">
                            <MapPin className="h-4 w-4 text-gray-500" />
                            <span>
                              {[connection.city, connection.state, connection.country]
                                .filter(Boolean)
                                .join(', ')}
                            </span>
                          </div>
                        )}
                        {connection.company_industry && (
                          <div className="flex items-center space-x-2">
                            <Building className="h-4 w-4 text-gray-500" />
                            <span>{connection.company_industry}</span>
                          </div>
                        )}
                      </div>

                      {/* Additional Info */}
                      <div className="flex flex-wrap gap-2">
                        {connection.followers && (
                          <Badge variant="secondary">
                            {connection.followers} followers
                          </Badge>
                        )}
                        {connection.company_size && (
                          <Badge variant="secondary">
                            {connection.company_size} company
                          </Badge>
                        )}
                      </div>

                      {/* Description */}
                      {connection.description && (
                        <div className="pt-2 border-t">
                          <p className="text-sm text-gray-600 line-clamp-3">
                            {connection.description}
                          </p>
                        </div>
                      )}

                      {/* Favorited Date */}
                      <div className="flex items-center space-x-1 text-xs text-gray-500 pt-2 border-t">
                        <Calendar className="h-3 w-3" />
                        <span>Added to favorites: {new Date(favorite.favorited_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
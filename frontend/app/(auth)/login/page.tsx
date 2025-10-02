'use client';

import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { loginUser, getUserProfile } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import Link from 'next/link';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await loginUser(email, password);
      
      // Check if this is a password reset response
      if ('reset_token' in response) {
        // User needs to reset password - redirect to reset page
        router.push(`/reset-password?token=${response.reset_token}`);
        return;
      }
      
      // Normal login flow
      const { access_token } = response;
      const userProfile = await getUserProfile(access_token);
      // Add default persist_search_results if not present
      const userWithDefaults = {
        ...userProfile,
        persist_search_results: (userProfile as any).persist_search_results ?? false
      };
      login(access_token, userWithDefaults);
      // Redirect is now handled by the PublicRoute wrapper
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-4 pb-8">
          <CardTitle className="text-4xl font-bold text-center">Login</CardTitle>
          <CardDescription className="text-lg text-center text-gray-600">
            Enter your email below to login to your account.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="grid gap-6">
            <div className="grid gap-3">
              <Label htmlFor="email" className="text-base font-medium">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="m@example.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 text-base"
              />
            </div>
            <div className="grid gap-3">
              <Label htmlFor="password" className="text-base font-medium">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-12 text-base"
              />
            </div>
            {error && <p className="text-red-500 text-base font-medium">{error}</p>}
          </CardContent>
          <CardFooter className="flex flex-col pt-6">
            <Button type="submit" className="w-full h-12 text-base font-medium" disabled={isSubmitting}>
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </Button>
            <p className="mt-6 text-base text-center text-gray-700">
              Don&apos;t have an account?{' '}
              <Link href="/request-access" className="underline font-medium text-blue-600 hover:text-blue-800">
                Request Access
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
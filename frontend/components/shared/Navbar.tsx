'use client';

import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { getPendingCounts } from '@/lib/api';

interface PendingCounts {
  warm_intro_requests: number;
  follow_up_emails: number;
  access_requests: number;
}

interface NavLink {
  href: string;
  label: string;
  countKey?: keyof PendingCounts;
}

const adminNavLinks: NavLink[] = [
  { href: '/dashboard', label: 'Search Connections' },
  { href: '/data-management', label: 'Upload Connections' },
  { href: '/warm-intro-requests', label: 'Warm Intro Requests', countKey: 'warm_intro_requests' },
  { href: '/admin/follow-ups', label: 'Follow-Up Emails', countKey: 'follow_up_emails' },
  { href: '/access-requests', label: 'Access Requests', countKey: 'access_requests' },
  { href: '/settings', label: 'Settings' },
];

const userNavLinks: NavLink[] = [
  // End users see no navigation links - they only get the dashboard search functionality
];

export function Navbar() {
  const { logout, user, token } = useAuth();
  const pathname = usePathname();
  const [pendingCounts, setPendingCounts] = useState<PendingCounts>({
    warm_intro_requests: 0,
    follow_up_emails: 0,
    access_requests: 0,
  });

  // Determine which navigation links to show based on user role
  const navLinks = user?.role === 'admin' ? adminNavLinks : userNavLinks;

  // Fetch pending counts for admin users
  useEffect(() => {
    const fetchPendingCounts = async () => {
      if (user?.role === 'admin' && token) {
        try {
          const counts = await getPendingCounts(token);
          setPendingCounts(counts);
        } catch (error) {
          console.error('Failed to fetch pending counts:', error);
          // Keep default counts of 0 on error
        }
      }
    };

    fetchPendingCounts();
    
    // Refresh counts every 30 seconds for admin users
    const interval = user?.role === 'admin' && token ? setInterval(fetchPendingCounts, 30000) : null;
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [user?.role, token]);

  return (
    <nav className="bg-white border-b shadow-sm">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <Link href="/dashboard" className="font-bold text-xl">
              Superconnect AI
            </Link>
            {navLinks.length > 0 && (
              <div className="hidden md:flex items-center space-x-4">
                {navLinks.map((link) => {
                  const count = link.countKey ? pendingCounts[link.countKey] : 0;
                  const hasCountKey = !!link.countKey;
                  
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={`px-3 py-2 rounded-md text-sm font-medium ${
                        pathname === link.href
                          ? 'bg-gray-100 text-gray-900'
                          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                      }`}
                    >
                      {link.label}
                      {hasCountKey && (
                        <span className={`ml-1 text-white text-xs px-2 py-1 rounded-full ${
                          count > 0 ? 'bg-red-500' : 'bg-gray-400'
                        }`}>
                          {count}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
          <div className="flex items-center space-x-3">
            {user?.role && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                {user.role === 'admin' ? 'Admin' : 'User'}
              </span>
            )}
            <Button onClick={logout} variant="ghost" size="sm">
              Logout
            </Button>
          </div>
        </div>
      </div>
    </nav>
  );
}
'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/login');
  }, [router]);
  return <div className="flex items-center justify-center h-screen"><p>Redirecting...</p></div>;
}
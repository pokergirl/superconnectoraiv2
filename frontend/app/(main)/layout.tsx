'use client';
import { Navbar } from '../../components/shared/Navbar';
import ProtectedRoute from '../../components/shared/ProtectedRoute';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main>{children}</main>
      </div>
    </ProtectedRoute>
  );
}
'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getCurrentUser, logout } from '../utils/auth';
import { getBackendUrl } from '../utils/api';

export default function Navbar() {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    setMounted(true);
    setUser(getCurrentUser());
  }, [pathname]); // Refresh user whenever route changes

  // Avoid hydration mismatch by not rendering reactive portions until mounted
  if (!mounted) {
    return (
      <nav className="navbar">
        <div className="nav-container">
          <div className="nav-brand">
            <Link href="/" className="brand-link">Nyugma Legal Tool</Link>
          </div>
        </div>
      </nav>
    );
  }

  const handleLogout = () => {
    logout();
    setUser(null);
  };

  const isHelper = user?.user_type === 'helper';
  
  // Create Docs URL dynamically
  let docsUrl = 'http://localhost:8000/docs';
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
      docsUrl = `${process.env.NEXT_PUBLIC_API_URL}/docs`;
  }

  return (
    <nav className="navbar">
      <div className="nav-container" style={{ flexWrap: 'wrap', gap: '16px' }}>
        <div className="nav-brand">
          <Link href="/" className="brand-link">Nyugma Legal Tool</Link>
        </div>
        <div className="nav-links" style={{ flexWrap: 'wrap' }}>
          <Link href="/" className={`nav-link ${pathname === '/' ? 'active' : ''}`}>Home</Link>
          
          {/* Conditional links based on User status */}
          {!isHelper && (
            <>
              <Link href="/search" className={`nav-link ${pathname.includes('/search') ? 'active' : ''}`}>Search</Link>
              <Link href="/inquiry" className={`nav-link ${pathname.includes('/inquiry') ? 'active' : ''}`}>Inquiry</Link>
            </>
          )}

          {user && (
            <>
              {isHelper ? (
                 <Link href="/helper-dashboard" className={`nav-link ${pathname.includes('/helper-dashboard') ? 'active' : ''}`}>Helper Dashboard</Link>
              ) : (
                 <Link href="/dashboard" className={`nav-link ${pathname.includes('/dashboard') ? 'active' : ''}`}>Dashboard</Link>
              )}
              <Link href="/connections" className={`nav-link ${pathname.includes('/connections') ? 'active' : ''}`}>Connections</Link>
              <Link href="/messages" className={`nav-link ${pathname.includes('/messages') ? 'active' : ''}`}>Messages</Link>
            </>
          )}

          <Link href="/admin" className={`nav-link ${pathname.includes('/admin') ? 'active' : ''}`}>Admin</Link>
          <a href={docsUrl} target="_blank" rel="noopener noreferrer" className="nav-link">API Docs</a>
        </div>
        
        {/* User Status/Auth Links */}
        <div className="nav-user-actions" style={{ flexShrink: 0, display: 'flex', gap: '16px', alignItems: 'center', marginLeft: 'auto' }}>
          {user ? (
            <>
              <div className="user-info" style={{ display: 'flex', flexDirection: 'column', fontSize: '13px', textAlign: 'right' }}>
                <span className="user-name" style={{ fontWeight: 'bold', color: '#fff' }}>{user.full_name}</span>
                <span className="user-type" style={{ opacity: 0.9, color: '#e2e8f0' }}>{isHelper ? 'Helper' : 'Litigant'}</span>
              </div>
              <button onClick={handleLogout} className="logout-btn" style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#ef4444', border: 'none', color: '#fff', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', transition: 'all 0.2s', fontWeight: 600, boxShadow: '0 2px 4px rgba(0,0,0,0.1)'}}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
                Logout
              </button>
            </>
          ) : (
            <Link href="/auth" className="nav-link" style={{ background: '#10b981', color: '#fff', fontWeight: 'bold', padding: '8px 20px', borderRadius: '6px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>Login / Register</Link>
          )}
        </div>
      </div>
    </nav>
  );
}

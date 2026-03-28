'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getCurrentUser, isAuthenticated } from '../../utils/auth';

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }
    const currentUser = getCurrentUser();
    if (!currentUser) {
      router.push('/auth');
      return;
    }
    setUser(currentUser);
  }, [router]);

  if (!mounted || !user) {
    return <div className="loading-container"><div className="loading-spinner"></div></div>;
  }

  const isHelper = user.user_type === 'helper';
  
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const calculateDaysSince = (dateString) => {
    if (!dateString) return 0;
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  return (
    <div className="container">
      <header className="header">
        <h1 className="title">Welcome, {user.full_name}!</h1>
        <p className="subtitle">
          {isHelper 
            ? 'Thank you for helping others with your experience' 
            : 'Find similar cases and connect with experienced helpers'}
        </p>
      </header>

      <main className="main-content">
        {/* User Profile Section */}
        <section className="dashboard-section">
          <div className="section-card" style={{padding: '30px', background: '#fff', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)'}}>
            <h2 className="section-title" style={{marginBottom: '20px', fontSize: '1.4rem', borderBottom: '1px solid #eee', paddingBottom: '10px'}}>Your Profile</h2>
            <div className="profile-info" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '20px'}}>
              
              <div className="profile-item">
                <span className="profile-label" style={{display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '4px'}}>Full Name</span>
                <span className="profile-value" style={{fontWeight: '600'}}>{user.full_name}</span>
              </div>
              
              <div className="profile-item">
                <span className="profile-label" style={{display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '4px'}}>Email</span>
                <span className="profile-value" style={{fontWeight: '600'}}>{user.email}</span>
              </div>
              
              <div className="profile-item">
                <span className="profile-label" style={{display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '4px'}}>User Type</span>
                <span className={`profile-badge`} style={{display: 'inline-block', padding: '4px 10px', borderRadius: '20px', fontSize: '0.8rem', fontWeight: 'bold', background: isHelper ? '#dbeafe' : '#dcfce3', color: isHelper ? '#1e40af' : '#166534'}}>{isHelper ? 'Helper' : 'New Litigant'}</span>
              </div>

              {user.phone && (
                <div className="profile-item">
                  <span className="profile-label" style={{display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '4px'}}>Phone</span>
                  <span className="profile-value" style={{fontWeight: '600'}}>{user.phone}</span>
                </div>
              )}

              {user.city && (
                <div className="profile-item">
                  <span className="profile-label" style={{display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '4px'}}>City</span>
                  <span className="profile-value" style={{fontWeight: '600'}}>{user.city}</span>
                </div>
              )}

              {user.state && (
                <div className="profile-item">
                  <span className="profile-label" style={{display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '4px'}}>State</span>
                  <span className="profile-value" style={{fontWeight: '600'}}>{user.state}</span>
                </div>
              )}

              <div className="profile-item">
                <span className="profile-label" style={{display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '4px'}}>Member Since</span>
                <span className="profile-value" style={{fontWeight: '600'}}>{formatDate(user.created_at)}</span>
              </div>

              {isHelper && (
                 <div className="profile-item">
                   <span className="profile-label" style={{display: 'block', fontSize: '0.85rem', color: '#6b7280', marginBottom: '4px'}}>Reputation Score</span>
                   <span className="profile-value" style={{fontWeight: '600', color: '#f59e0b'}}>{(user.reputation_score || 0).toFixed(1)} / 5.0</span>
                 </div>
              )}

            </div>
          </div>
        </section>

        {/* Quick Actions */}
        <section className="dashboard-section" style={{marginTop: '30px'}}>
          <div className="section-card" style={{padding: '30px', background: '#fff', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)'}}>
            <h2 className="section-title" style={{marginBottom: '20px', fontSize: '1.4rem', borderBottom: '1px solid #eee', paddingBottom: '10px'}}>Quick Actions</h2>
            <div className="quick-actions" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '20px'}}>
              
              {isHelper ? (
                <>
                  <Link href="/helper-dashboard" style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px', background: '#f8fafc', borderRadius: '12px', textDecoration: 'none', color: '#1e293b', transition: 'transform 0.2s, boxShadow 0.2s', border: '1px solid #e2e8f0'}}>
                    <h3 style={{fontSize: '1.1rem', marginBottom: '8px'}}>Add New Case</h3>
                    <p style={{fontSize: '0.85rem', color: '#64748b'}}>Share your past case experience</p>
                  </Link>
                  <Link href="/connections" style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px', background: '#f8fafc', borderRadius: '12px', textDecoration: 'none', color: '#1e293b', transition: 'transform 0.2s, boxShadow 0.2s', border: '1px solid #e2e8f0'}}>
                    <h3 style={{fontSize: '1.1rem', marginBottom: '8px'}}>My Connections</h3>
                    <p style={{fontSize: '0.85rem', color: '#64748b'}}>View and manage connections</p>
                  </Link>
                  <div onClick={() => alert('Coming soon!')} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', cursor: 'pointer', color: '#1e293b'}}>
                    <h3 style={{fontSize: '1.1rem', marginBottom: '8px'}}>My Cases</h3>
                    <p style={{fontSize: '0.85rem', color: '#64748b'}}>View your submitted cases</p>
                  </div>
                </>
              ) : (
                <>
                  <Link href="/search" style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px', background: '#f0f9ff', borderRadius: '12px', textDecoration: 'none', color: '#0369a1', transition: 'transform 0.2s', border: '1px solid #bae6fd'}}>
                    <h3 style={{fontSize: '1.1rem', marginBottom: '8px'}}>Search Cases</h3>
                    <p style={{fontSize: '0.85rem', color: '#0284c7'}}>Find similar legal cases</p>
                  </Link>
                  <Link href="/connections" style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px', background: '#f8fafc', borderRadius: '12px', textDecoration: 'none', color: '#1e293b', transition: 'transform 0.2s', border: '1px solid #e2e8f0'}}>
                    <h3 style={{fontSize: '1.1rem', marginBottom: '8px'}}>My Connections</h3>
                    <p style={{fontSize: '0.85rem', color: '#64748b'}}>View connection requests</p>
                  </Link>
                  <Link href="/messages" style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px', background: '#f8fafc', borderRadius: '12px', textDecoration: 'none', color: '#1e293b', transition: 'transform 0.2s', border: '1px solid #e2e8f0'}}>
                    <h3 style={{fontSize: '1.1rem', marginBottom: '8px'}}>Messages</h3>
                    <p style={{fontSize: '0.85rem', color: '#64748b'}}>Chat with helpers</p>
                  </Link>
                  <Link href="/inquiry" style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px', background: '#fffbeb', borderRadius: '12px', textDecoration: 'none', color: '#92400e', transition: 'transform 0.2s', border: '1px solid #fde68a'}}>
                    <h3 style={{fontSize: '1.1rem', marginBottom: '8px'}}>Legal Inquiry</h3>
                    <p style={{fontSize: '0.85rem', color: '#b45309'}}>Schedule a consultation</p>
                  </Link>
                </>
              )}

            </div>
          </div>
        </section>

        {/* Statistics */}
        <section className="dashboard-section" style={{marginTop: '30px', marginBottom: '60px'}}>
          <div className="section-card" style={{padding: '30px', background: '#fff', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)'}}>
            <h2 className="section-title" style={{marginBottom: '20px', fontSize: '1.4rem', borderBottom: '1px solid #eee', paddingBottom: '10px'}}>Your Activity</h2>
            <div className="stats-grid" style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '20px'}}>
              
              {isHelper ? (
                <>
                  <div style={{textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: '12px'}}>
                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#667eea'}}>{user.cases_helped || 0}</div>
                    <div style={{fontSize: '0.85rem', color: '#64748b'}}>People Helped</div>
                  </div>
                  <div style={{textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: '12px'}}>
                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#667eea'}}>{user.total_ratings || 0}</div>
                    <div style={{fontSize: '0.85rem', color: '#64748b'}}>Total Ratings</div>
                  </div>
                  <div style={{textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: '12px'}}>
                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#667eea'}}>{user.reputation_score ? user.reputation_score.toFixed(1) : '0.0'}</div>
                    <div style={{fontSize: '0.85rem', color: '#64748b'}}>Reputation</div>
                  </div>
                  <div style={{textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: '12px'}}>
                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#667eea'}}>{calculateDaysSince(user.created_at)}</div>
                    <div style={{fontSize: '0.85rem', color: '#64748b'}}>Days Active</div>
                  </div>
                </>
              ) : (
                <>
                  <div style={{textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: '12px'}}>
                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#667eea'}}>0</div>
                    <div style={{fontSize: '0.85rem', color: '#64748b'}}>Cases Searched</div>
                  </div>
                  <div style={{textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: '12px'}}>
                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#667eea'}}>0</div>
                    <div style={{fontSize: '0.85rem', color: '#64748b'}}>Connections Made</div>
                  </div>
                  <div style={{textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: '12px'}}>
                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#667eea'}}>0</div>
                    <div style={{fontSize: '0.85rem', color: '#64748b'}}>Messages Sent</div>
                  </div>
                  <div style={{textAlign: 'center', padding: '20px', background: '#f8fafc', borderRadius: '12px'}}>
                    <div style={{fontSize: '2rem', fontWeight: 'bold', color: '#667eea'}}>{calculateDaysSince(user.created_at)}</div>
                    <div style={{fontSize: '0.85rem', color: '#64748b'}}>Days Active</div>
                  </div>
                </>
              )}

            </div>
          </div>
        </section>

      </main>
    </div>
  );
}

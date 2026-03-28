'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, isAuthenticated } from '../../utils/auth';
import { authenticatedFetch } from '../../utils/api';

export default function Connections() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [activeTab, setActiveTab] = useState('pending');
  
  const [pending, setPending] = useState([]);
  const [accepted, setAccepted] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Rating Modal State
  const [ratingModal, setRatingModal] = useState({ isOpen: false, targetUser: null, connectionId: null });
  const [ratingValue, setRatingValue] = useState(0);
  const [reviewText, setReviewText] = useState('');

  useEffect(() => {
    setMounted(true);
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }
    const currentUser = getCurrentUser();
    setUser(currentUser);
    if (currentUser) {
      fetchConnections();
    }
  }, [router]);

  const fetchConnections = async () => {
    setLoading(true);
    try {
      const [pendingRes, acceptedRes] = await Promise.all([
        authenticatedFetch('/api/connections/pending'),
        authenticatedFetch('/api/connections/accepted')
      ]);

      if (pendingRes.ok) setPending(await pendingRes.json());
      if (acceptedRes.ok) setAccepted(await acceptedRes.json());
    } catch (err) {
      console.error("Error fetching connections:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (connectionId, action) => {
    try {
      const res = await authenticatedFetch(`/api/connections/${connectionId}/${action}`, {
        method: 'POST'
      });
      if (res.ok) {
        fetchConnections();
      } else {
        alert(`Failed to ${action} connection`);
      }
    } catch (err) {
      alert(err.message);
    }
  };

  const openRatingModal = (targetUser, connectionId) => {
    setRatingModal({ isOpen: true, targetUser, connectionId });
    setRatingValue(0);
    setReviewText('');
  };

  const closeRatingModal = () => {
    setRatingModal({ isOpen: false, targetUser: null, connectionId: null });
  };

  const submitRating = async () => {
    if (ratingValue === 0) {
      alert("Please select a star rating");
      return;
    }
    try {
      const res = await authenticatedFetch(`/api/ratings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rated_user_id: ratingModal.targetUser.id,
          rating_value: ratingValue,
          review: reviewText || null
        })
      });

      if (res.ok) {
        alert("Rating submitted successfully!");
        closeRatingModal();
      } else {
        const errData = await res.json().catch(()=>({}));
        alert(errData.detail || "Failed to submit rating");
      }
    } catch (err) {
      alert(err.message);
    }
  };

  if (!mounted || !user) {
    return <div className="loading-container"><div className="loading-spinner"></div></div>;
  }

  const isHelper = user.user_type === 'helper';
  
  return (
    <div className="container" style={{position: 'relative'}}>
      <header className="header">
        <h1 className="title">My Connections</h1>
        <p className="subtitle">Manage your connection requests and accepted connections</p>
      </header>

      <main className="main-content">
        {/* Tabs */}
        <div style={{display: 'flex', borderBottom: '1px solid #e2e8f0', marginBottom: '24px'}}>
          <button 
            onClick={() => setActiveTab('pending')}
            style={{padding: '16px 24px', background: 'none', border: 'none', borderBottom: activeTab === 'pending' ? '2px solid #667eea' : '2px solid transparent', color: activeTab === 'pending' ? '#667eea' : '#64748b', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s'}}>
            Pending Requests
            <span style={{background: activeTab === 'pending' ? '#e0e7ff' : '#f1f5f9', color: activeTab === 'pending' ? '#4338ca' : '#64748b', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem'}}>{pending.length}</span>
          </button>
          <button 
            onClick={() => setActiveTab('accepted')}
            style={{padding: '16px 24px', background: 'none', border: 'none', borderBottom: activeTab === 'accepted' ? '2px solid #10b981' : '2px solid transparent', color: activeTab === 'accepted' ? '#10b981' : '#64748b', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', transition: 'all 0.2s'}}>
            Accepted Connections
            <span style={{background: activeTab === 'accepted' ? '#d1fae5' : '#f1f5f9', color: activeTab === 'accepted' ? '#047857' : '#64748b', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem'}}>{accepted.length}</span>
          </button>
        </div>

        {/* Tab Content */}
        <div>
          {loading ? (
            <div style={{textAlign: 'center', padding: '40px'}}>
               <div className="loading-spinner" style={{width: '32px', height: '32px', border: '3px solid #e5e7eb', borderTopColor: '#667eea', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 16px'}}></div>
               <p style={{color: '#64748b'}}>Loading connections...</p>
            </div>
          ) : (
             <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px'}}>
               
               {activeTab === 'pending' && pending.length === 0 && (
                 <div style={{gridColumn: '1 / -1', textAlign: 'center', padding: '60px', background: '#f8fafc', borderRadius: '16px', border: '1px dashed #cbd5e1'}}>
                    <h3 style={{fontSize: '1.25rem', color: '#334155', marginBottom: '8px'}}>No Pending Requests</h3>
                    <p style={{color: '#64748b'}}>You don't have any pending connection requests right now.</p>
                 </div>
               )}

               {activeTab === 'pending' && pending.map(conn => {
                  // Determine profile info to show based on who the logged-in user is
                  const counterpart = isHelper ? conn.requester : conn.target_user;
                  return (
                    <div key={conn.id} style={{background: '#fff', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0'}}>
                       <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px'}}>
                         <div>
                            <h3 style={{fontSize: '1.1rem', fontWeight: 600, color: '#1e293b', marginBottom: '4px'}}>{counterpart?.full_name || 'Unknown User'}</h3>
                            <p style={{fontSize: '0.85rem', color: '#64748b', background: '#f1f5f9', display: 'inline-block', padding: '2px 8px', borderRadius: '12px'}}>{counterpart?.user_type === 'helper' ? 'Helper' : 'Litigant'}</p>
                         </div>
                       </div>
                       
                       {conn.message && (
                         <div style={{background: '#f8fafc', padding: '12px', borderRadius: '8px', fontSize: '0.9rem', color: '#475569', marginBottom: '16px', fontStyle: 'italic'}}>
                           "{conn.message}"
                         </div>
                       )}

                       <div style={{display: 'flex', gap: '12px', marginTop: 'auto'}}>
                          {isHelper ? (
                            <>
                              <button onClick={() => handleAction(conn.id, 'accept')} style={{flex: 1, padding: '10px', background: '#10b981', color: 'white', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', transition: 'background 0.2s'}}>Accept</button>
                              <button onClick={() => handleAction(conn.id, 'decline')} style={{flex: 1, padding: '10px', background: '#f8fafc', color: '#ef4444', border: '1px solid #fca5a5', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', transition: 'background 0.2s'}}>Decline</button>
                            </>
                          ) : (
                             <button style={{flex: 1, padding: '10px', background: '#f1f5f9', color: '#94a3b8', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'not-allowed'}}>Request Sent</button>
                          )}
                       </div>
                    </div>
                  );
               })}

               {activeTab === 'accepted' && accepted.length === 0 && (
                 <div style={{gridColumn: '1 / -1', textAlign: 'center', padding: '60px', background: '#f8fafc', borderRadius: '16px', border: '1px dashed #cbd5e1'}}>
                    <h3 style={{fontSize: '1.25rem', color: '#334155', marginBottom: '8px'}}>No Accepted Connections</h3>
                    <p style={{color: '#64748b'}}>You don't have any accepted connections yet.</p>
                 </div>
               )}

               {activeTab === 'accepted' && accepted.map(conn => {
                  const counterpart = isHelper ? conn.requester : conn.target_user;
                  return (
                    <div key={conn.id} style={{background: '#fff', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column'}}>
                       <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px'}}>
                         <div>
                            <h3 style={{fontSize: '1.1rem', fontWeight: 600, color: '#1e293b', marginBottom: '4px'}}>{counterpart?.full_name || 'Unknown User'}</h3>
                            <p style={{fontSize: '0.85rem', color: '#64748b', background: '#d1fae5', color: '#047857', display: 'inline-block', padding: '2px 8px', borderRadius: '12px'}}>Connected</p>
                         </div>
                       </div>
                       
                       <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.85rem', color: '#475569', marginBottom: '20px'}}>
                          {counterpart?.email && <div><strong>Email:</strong> {counterpart.email}</div>}
                          {counterpart?.phone && <div><strong>Phone:</strong> {counterpart.phone}</div>}
                          {counterpart?.city && <div><strong>City:</strong> {counterpart.city}</div>}
                       </div>

                       <div style={{display: 'flex', gap: '12px', marginTop: 'auto'}}>
                          <button onClick={() => router.push(`/messages?connectionId=${conn.id}`)} style={{flex: 1, padding: '10px', background: '#667eea', color: 'white', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', transition: 'background 0.2s'}}>Message</button>
                          
                          {/* Only Litigants can rate Helpers */}
                          {!isHelper && (
                             <button onClick={() => openRatingModal(counterpart, conn.id)} style={{flex: 1, padding: '10px', background: '#f59e0b', color: 'white', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', transition: 'background 0.2s'}}>Rate</button>
                          )}
                       </div>
                    </div>
                  );
               })}

             </div>
          )}
        </div>
      </main>

      {/* Rating Modal */}
      {ratingModal.isOpen && (
        <div style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000}}>
           <div style={{background: '#fff', padding: '32px', borderRadius: '16px', width: '100%', maxWidth: '400px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
                 <h3 style={{fontSize: '1.25rem', fontWeight: 600, margin: 0}}>Rate {ratingModal.targetUser?.full_name}</h3>
                 <button onClick={closeRatingModal} style={{background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#94a3b8'}}>&times;</button>
              </div>

              <div style={{textAlign: 'center', marginBottom: '24px'}}>
                 <div style={{display: 'flex', justifyContent: 'center', gap: '8px', fontSize: '2rem', cursor: 'pointer', userSelect: 'none', color: '#cbd5e1'}}>
                    {[1, 2, 3, 4, 5].map(star => (
                       <span 
                         key={star} 
                         onClick={() => setRatingValue(star)}
                         style={{color: star <= ratingValue ? '#f59e0b' : '#cbd5e1', transition: 'color 0.2s'}}
                       >★</span>
                    ))}
                 </div>
                 <p style={{fontSize: '0.9rem', color: '#64748b', marginTop: '8px'}}>{ratingValue > 0 ? `${ratingValue} Stars` : 'Click to select rating'}</p>
              </div>

              <div style={{marginBottom: '24px'}}>
                 <textarea 
                   placeholder="Write a brief review (optional)" 
                   value={reviewText}
                   onChange={e => setReviewText(e.target.value)}
                   style={{width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '0.95rem', resize: 'vertical'}}
                   rows="4"
                 ></textarea>
              </div>

              <div style={{display: 'flex', gap: '12px'}}>
                 <button onClick={closeRatingModal} style={{flex: 1, padding: '12px', background: '#f1f5f9', color: '#475569', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer'}}>Cancel</button>
                 <button onClick={submitRating} disabled={ratingValue === 0} style={{flex: 1, padding: '12px', background: '#f59e0b', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: ratingValue === 0 ? 'not-allowed' : 'pointer', opacity: ratingValue === 0 ? 0.7 : 1}}>Submit Rating</button>
              </div>
           </div>
        </div>
      )}

    </div>
  );
}

'use client';

import { useState, useEffect, useCallback } from 'react';

export default function AdminPage() {
  const [inquiries, setInquiries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchInquiries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${url}/api/inquiries`);
      if (!response.ok) {
        throw new Error('Failed to fetch inquiries');
      }
      const data = await response.json();
      setInquiries(data.inquiries || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInquiries();
  }, [fetchInquiries]);

  const handleStatusChange = async (inquiryId, newStatus) => {
    try {
      const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${url}/api/inquiries/${inquiryId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (response.ok) {
        fetchInquiries();
      }
    } catch (err) {
      console.error('Error updating status', err);
    }
  };

  const filteredInquiries = statusFilter 
    ? inquiries.filter(i => i.status === statusFilter)
    : inquiries;

  const stats = {
    total: inquiries.length,
    pending: inquiries.filter(i => i.status === 'pending').length,
    reviewed: inquiries.filter(i => i.status === 'reviewed').length,
    contacted: inquiries.filter(i => i.status === 'contacted').length,
  };

  // Helper function to format the long inquiry body
  const formatDate = (isoStr) => new Date(isoStr).toLocaleString();

  return (
    <div className="container">
      <header className="header">
        <h1 className="title">Inquiry Management</h1>
        <p className="subtitle">View and manage legal inquiries submitted by clients</p>
      </header>

      <main className="main-content">
        <section className="stats-section">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon pending">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </div>
              <div className="stat-content">
                <div className="stat-value">{stats.pending}</div>
                <div className="stat-label">Pending</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon reviewed">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              </div>
              <div className="stat-content">
                <div className="stat-value">{stats.reviewed}</div>
                <div className="stat-label">Reviewed</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon contacted">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
                </svg>
              </div>
              <div className="stat-content">
                <div className="stat-value">{stats.contacted}</div>
                <div className="stat-label">Contacted</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon total">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="8.5" cy="7" r="4"></circle>
                  <polyline points="17 11 19 13 23 9"></polyline>
                </svg>
              </div>
              <div className="stat-content">
                <div className="stat-value">{stats.total}</div>
                <div className="stat-label">Total Inquiries</div>
              </div>
            </div>
          </div>
        </section>

        <section className="filters-section">
          <div className="filters-container">
            <div className="filter-group">
              <label htmlFor="statusFilter">Filter by Status:</label>
              <select 
                id="statusFilter" 
                className="filter-select" 
                value={statusFilter} 
                onChange={e => setStatusFilter(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="reviewed">Reviewed</option>
                <option value="contacted">Contacted</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <button className="refresh-button" onClick={fetchInquiries}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="23 4 23 10 17 10"></polyline>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
              </svg>
              Refresh
            </button>
          </div>
        </section>

        <section className="inquiries-section">
          <div className="inquiries-container">
            {loading && (
              <div className="loading-state">
                <div className="loading-spinner"></div>
                <p>Loading inquiries...</p>
              </div>
            )}
            
            {!loading && error && (
              <div style={{ padding: '20px', color: 'red', textAlign: 'center' }}>
                {error}
              </div>
            )}

            {!loading && !error && filteredInquiries.length === 0 && (
              <div className="empty-state">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"></circle>
                  <path d="m21 21-4.35-4.35"></path>
                </svg>
                <h3>No Inquiries Found</h3>
                <p>There are no inquiries matching your filter criteria.</p>
              </div>
            )}

            {!loading && filteredInquiries.map((inquiry) => (
              <div key={inquiry.id} className="inquiry-card">
                <div className="inquiry-header">
                  <div className="inquiry-client">
                    <h3 className="client-name">{inquiry.client_name}</h3>
                    <div className="inquiry-meta">
                      <span className="inquiry-date">{formatDate(inquiry.created_at)}</span>
                      <span className="inquiry-location">{inquiry.city}, {inquiry.state}</span>
                    </div>
                  </div>
                  <div className="inquiry-badges">
                    <span className={`status-badge status-${inquiry.status}`}>{inquiry.status}</span>
                    <span className={`urgency-badge urgency-${inquiry.urgency}`}>{inquiry.urgency}</span>
                  </div>
                </div>
                
                <div className="inquiry-body">
                  <div className="detail-group">
                    <h4>Case Type</h4>
                    <p>{inquiry.case_type}</p>
                  </div>
                  <div className="detail-group field-full">
                    <h4>Description</h4>
                    <p>{inquiry.description}</p>
                  </div>
                  <div className="detail-group">
                    <h4>Contact Info</h4>
                    <p>{inquiry.client_phone}</p>
                    {inquiry.client_email && <p>{inquiry.client_email}</p>}
                  </div>
                </div>

                <div className="inquiry-actions">
                  <select 
                    className="status-select" 
                    value={inquiry.status}
                    onChange={(e) => handleStatusChange(inquiry.id, e.target.value)}
                  >
                    <option value="pending">Pending</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="contacted">Contacted</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

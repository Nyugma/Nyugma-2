'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, isUserType } from '../../utils/auth';
import { authenticatedFetch } from '../../utils/api';

export default function HelperDashboard() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [user, setUser] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setMounted(true);
    if (!isUserType('helper')) {
      router.push('/dashboard');
      return;
    }
    setUser(getCurrentUser());
  }, [router]);

  if (!mounted || !user) {
    return <div className="loading-container"><div className="loading-spinner"></div></div>;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const form = e.target;
    const formData = new FormData(form);
    
    // Validate File
    const file = formData.get('caseDocument');
    if (!file || file.size === 0) {
      setError("Please select a PDF document");
      setLoading(false);
      return;
    }
    if (file.type !== 'application/pdf') {
      setError("File must be a PDF");
      setLoading(false);
      return;
    }

    const payload = new FormData();
    payload.append('file', file);
    
    const metadata = {
      user_id: user.user_id,
      title: formData.get('caseTitle'),
      case_type: formData.get('caseType'),
      description: formData.get('description'),
      outcome: formData.get('outcome'),
      duration_months: parseInt(formData.get('durationMonths')),
      total_cost: parseFloat(formData.get('totalCost')),
      court_name: formData.get('courtName'),
      state: formData.get('state'),
      city: formData.get('city'),
      lawyer_name: formData.get('lawyerName') || null,
      lawyer_contact: formData.get('lawyerContact') || null,
      key_learnings: formData.get('keyLearnings') || null,
      advice_for_others: formData.get('adviceForOthers') || null,
      is_public: formData.get('isPublic') === 'on',
      willing_to_help: formData.get('willingToHelp') === 'on',
    };

    payload.append('metadata', JSON.stringify(metadata));

    try {
      const response = await authenticatedFetch('/api/helper/cases', {
        method: 'POST',
        body: payload
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to submit case');
      }

      const result = await response.json();
      setSuccess(result);
      form.reset();
      window.scrollTo(0, 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <h1 className="title">Share Your Legal Experience</h1>
        <p className="subtitle">Help others by sharing your case details. Your experience can guide someone facing a similar situation.</p>
      </header>

      <main className="main-content">
        <section className="inquiry-section">
          <div className="inquiry-container" style={{background: '#fff', borderRadius: '16px', padding: '40px', boxShadow: '0 10px 25px rgba(0,0,0,0.05)'}}>
            
            {error && (
              <div style={{ backgroundColor: '#fee2e2', color: '#dc2626', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
                {error}
              </div>
            )}

            {!success && !loading && (
              <form onSubmit={handleSubmit} className="inquiry-form" style={{display: 'flex', flexDirection: 'column', gap: '32px'}}>
                  {/* Case Document Upload */}
                  <div className="form-section">
                      <h2 className="section-title" style={{fontSize: '1.25rem', borderBottom: '1px solid #e5e7eb', paddingBottom: '8px', marginBottom: '16px'}}>Case Document</h2>
                      <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                          <label htmlFor="caseDocument" className="form-label" style={{fontWeight: 600}}>
                              Upload Case Document (PDF) <span className="required" style={{color: '#dc2626'}}>*</span>
                          </label>
                          <input type="file" id="caseDocument" name="caseDocument" accept=".pdf" required 
                            style={{padding: '12px', border: '1px dashed #d1d5db', borderRadius: '8px', background: '#f9fafb'}}/>
                          <span className="form-hint" style={{fontSize: '0.85rem', color: '#6b7280'}}>Upload your case judgment, petition, or related legal document (Max 10MB)</span>
                      </div>
                  </div>

                  {/* Basic Case Information */}
                  <div className="form-section">
                      <h2 className="section-title" style={{fontSize: '1.25rem', borderBottom: '1px solid #e5e7eb', paddingBottom: '8px', marginBottom: '16px'}}>Basic Information</h2>
                      
                      <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px'}}>
                          <label htmlFor="caseTitle" className="form-label" style={{fontWeight: 600}}>Case Title <span className="required" style={{color: '#dc2626'}}>*</span></label>
                          <input type="text" id="caseTitle" name="caseTitle" required placeholder="e.g., Property Dispute - Sharma vs Kumar" 
                             style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}} />
                      </div>

                      <div className="form-row" style={{display: 'flex', gap: '16px', marginBottom: '16px'}}>
                          <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px', flex: 1}}>
                              <label htmlFor="caseType" className="form-label" style={{fontWeight: 600}}>Type of Case <span className="required" style={{color: '#dc2626'}}>*</span></label>
                              <select id="caseType" name="caseType" required defaultValue="" style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}}>
                                  <option value="" disabled>Select case type</option>
                                  <option value="civil">Civil Case</option>
                                  <option value="criminal">Criminal Case</option>
                                  <option value="family">Family Law</option>
                                  <option value="property">Property Dispute</option>
                                  <option value="other">Other</option>
                              </select>
                          </div>

                          <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px', flex: 1}}>
                              <label htmlFor="outcome" className="form-label" style={{fontWeight: 600}}>Case Outcome <span className="required" style={{color: '#dc2626'}}>*</span></label>
                              <select id="outcome" name="outcome" required defaultValue="" style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}}>
                                  <option value="" disabled>Select outcome</option>
                                  <option value="won">Won</option>
                                  <option value="lost">Lost</option>
                                  <option value="settled">Settled</option>
                                  <option value="ongoing">Ongoing</option>
                              </select>
                          </div>
                      </div>

                      <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                          <label htmlFor="description" className="form-label" style={{fontWeight: 600}}>Brief Description <span className="required" style={{color: '#dc2626'}}>*</span></label>
                          <textarea id="description" name="description" rows="4" required placeholder="Provide a brief overview of your case..." 
                            style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}}></textarea>
                      </div>
                  </div>

                  {/* Court & Location Details */}
                  <div className="form-section">
                      <h2 className="section-title" style={{fontSize: '1.25rem', borderBottom: '1px solid #e5e7eb', paddingBottom: '8px', marginBottom: '16px'}}>Court & Location</h2>
                      
                      <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px'}}>
                          <label htmlFor="courtName" className="form-label" style={{fontWeight: 600}}>Court Name <span className="required" style={{color: '#dc2626'}}>*</span></label>
                          <input type="text" id="courtName" name="courtName" required placeholder="e.g., District Court, Delhi" 
                             style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}}/>
                      </div>

                      <div className="form-row" style={{display: 'flex', gap: '16px'}}>
                          <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px', flex: 1}}>
                              <label htmlFor="state" className="form-label" style={{fontWeight: 600}}>State <span className="required" style={{color: '#dc2626'}}>*</span></label>
                              <input type="text" id="state" name="state" required placeholder="Your state" 
                                style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}}/>
                          </div>

                          <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px', flex: 1}}>
                              <label htmlFor="city" className="form-label" style={{fontWeight: 600}}>City <span className="required" style={{color: '#dc2626'}}>*</span></label>
                              <input type="text" id="city" name="city" required placeholder="Your city" 
                                style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}}/>
                          </div>
                      </div>
                  </div>

                  {/* Timeline & Cost */}
                  <div className="form-section">
                      <h2 className="section-title" style={{fontSize: '1.25rem', borderBottom: '1px solid #e5e7eb', paddingBottom: '8px', marginBottom: '16px'}}>Timeline & Cost</h2>
                      
                      <div className="form-row" style={{display: 'flex', gap: '16px'}}>
                          <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px', flex: 1}}>
                              <label htmlFor="durationMonths" className="form-label" style={{fontWeight: 600}}>Duration (Months) <span className="required" style={{color: '#dc2626'}}>*</span></label>
                              <input type="number" id="durationMonths" name="durationMonths" min="1" required placeholder="e.g., 12" 
                                style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}}/>
                          </div>

                          <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px', flex: 1}}>
                              <label htmlFor="totalCost" className="form-label" style={{fontWeight: 600}}>Total Cost (₹) <span className="required" style={{color: '#dc2626'}}>*</span></label>
                              <input type="number" id="totalCost" name="totalCost" min="0" required placeholder="e.g., 50000" 
                                style={{padding: '12px', border: '1px solid #d1d5db', borderRadius: '8px'}}/>
                          </div>
                      </div>
                  </div>

                  <div className="form-actions" style={{display: 'flex', gap: '16px', marginTop: '16px'}}>
                      <button type="button" onClick={() => window.history.back()} style={{padding: '14px 24px', background: '#f3f4f6', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer', color: '#4b5563'}}>Cancel</button>
                      <button type="submit" style={{padding: '14px 32px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer', flex: 1}}>
                          Submit Case
                      </button>
                  </div>
              </form>
            )}

            {loading && !success && (
              <div className="loading-container" style={{textAlign: 'center', padding: '60px'}}>
                <div className="loading-spinner" style={{width: '48px', height: '48px', border: '4px solid #e5e7eb', borderTopColor: '#667eea', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 20px'}}></div>
                <h3>Processing Document...</h3>
                <p style={{color: '#6b7280'}}>Saving case details safely</p>
              </div>
            )}

            {success && (
              <div className="success-container" style={{textAlign: 'center', padding: '40px'}}>
                <h2 style={{fontSize: '1.8rem', color: '#059669', marginBottom: '16px'}}>Case Added Successfully!</h2>
                <p style={{color: '#4b5563', marginBottom: '24px'}}>Thank you for sharing your experience. Your case will help others.</p>
                <div style={{background: '#f8fafc', padding: '24px', borderRadius: '12px', marginBottom: '32px', textAlign: 'left', border: '1px solid #e2e8f0'}}>
                  <p><strong>Case ID:</strong> {success.case_id}</p>
                  <p><strong>Title:</strong> {success.title}</p>
                </div>
                <button onClick={() => setSuccess(null)} style={{background: '#667eea', color: '#fff', padding: '12px 24px', borderRadius: '8px', border: 'none', fontWeight: 600, cursor: 'pointer', marginRight: '16px'}}>Add Another Case</button>
                <button onClick={() => router.push('/dashboard')} style={{background: '#f3f4f6', color: '#1f2937', padding: '12px 24px', borderRadius: '8px', border: 'none', fontWeight: 600, cursor: 'pointer'}}>Back to Dashboard</button>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

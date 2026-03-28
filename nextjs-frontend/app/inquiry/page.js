'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function InquiryPage() {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(e.target);
    const data = {
      case_id: formData.get('caseId') || null,
      case_type: formData.get('caseType'),
      client_name: formData.get('fullName'),
      client_phone: formData.get('phoneNumber'),
      client_email: formData.get('email') || null,
      city: formData.get('city'),
      state: formData.get('state'),
      description: formData.get('caseDescription'),
      requirements: formData.get('requirements'),
      expectations: formData.get('expectations'),
      urgency: formData.get('urgency'),
      preferred_date: formData.get('preferredDate') || null,
      previous_lawyer: formData.get('previousLawyer') === 'yes',
      budget_range: formData.get('budgetRange'),
      additional_notes: formData.get('additionalNotes') || null
    };

    try {
      const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${url}/api/inquiries`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.message || 'Failed to submit inquiry.');
      }

      setSuccess(true);
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
        <h1 className="title">Schedule Legal Inquiry</h1>
        <p className="subtitle">Fill out the form below and our legal team will contact you shortly</p>
      </header>

      <main className="main-content">
        <section className="inquiry-section">
          <div className="inquiry-container">
            {!success && (
              <form id="inquiryForm" className="inquiry-form" onSubmit={handleSubmit}>
                {error && (
                  <div style={{ backgroundColor: '#fee2e2', color: '#dc2626', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
                    {error}
                  </div>
                )}
                
                {/* Case Information */}
                <div className="form-section">
                  <h2 className="section-title">Case Information</h2>
                  
                  <div className="form-group">
                    <label htmlFor="caseId" className="form-label">
                      Case ID / Case Number <span className="optional">(Optional)</span>
                    </label>
                    <input type="text" id="caseId" name="caseId" className="form-input" placeholder="e.g., case_001 or reference number" />
                  </div>

                  <div className="form-group">
                    <label htmlFor="caseType" className="form-label">
                      Type of Case <span className="required">*</span>
                    </label>
                    <select id="caseType" name="caseType" className="form-input" required defaultValue="">
                      <option value="" disabled>Select case type</option>
                      <option value="civil">Civil Case</option>
                      <option value="criminal">Criminal Case</option>
                      <option value="family">Family Law</option>
                      <option value="property">Property Dispute</option>
                      <option value="corporate">Corporate/Business Law</option>
                      <option value="labor">Labor/Employment Law</option>
                      <option value="consumer">Consumer Protection</option>
                      <option value="tax">Tax Law</option>
                      <option value="intellectual">Intellectual Property</option>
                      <option value="constitutional">Constitutional Law</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>

                {/* Personal Information */}
                <div className="form-section">
                  <h2 className="section-title">Personal Information</h2>
                  
                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="fullName" className="form-label">
                        Full Name <span className="required">*</span>
                      </label>
                      <input type="text" id="fullName" name="fullName" className="form-input" placeholder="Enter your full name" required />
                    </div>

                    <div className="form-group">
                      <label htmlFor="phoneNumber" className="form-label">
                        Phone Number <span className="required">*</span>
                      </label>
                      <input type="tel" id="phoneNumber" name="phoneNumber" className="form-input" placeholder="+91 XXXXX XXXXX" maxLength="17" required />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="email" className="form-label">
                        Email Address <span className="optional">(Optional)</span>
                      </label>
                      <input type="email" id="email" name="email" className="form-input" placeholder="your.email@example.com" />
                    </div>

                    <div className="form-group">
                      <label htmlFor="city" className="form-label">
                        City <span className="required">*</span>
                      </label>
                      <input type="text" id="city" name="city" className="form-input" placeholder="Your city" required />
                    </div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="state" className="form-label">
                      State <span className="required">*</span>
                    </label>
                    <select id="state" name="state" className="form-input" required defaultValue="">
                      <option value="" disabled>Select state</option>
                      <option value="Andhra Pradesh">Andhra Pradesh</option>
                      <option value="Delhi">Delhi</option>
                      <option value="Maharashtra">Maharashtra</option>
                      {/* Truncated options for example, in reality full list */}
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>

                {/* Case Details */}
                <div className="form-section">
                  <h2 className="section-title">Case Details</h2>
                  
                  <div className="form-group">
                    <label htmlFor="caseDescription" className="form-label">
                      Brief Description of Your Case <span className="required">*</span>
                    </label>
                    <textarea id="caseDescription" name="caseDescription" className="form-textarea" rows="4" placeholder="Provide a brief overview of your legal matter..." required></textarea>
                    <span className="form-hint">Please provide key details about your case</span>
                  </div>

                  <div className="form-group">
                    <label htmlFor="requirements" className="form-label">
                      Your Requirements <span className="required">*</span>
                    </label>
                    <textarea id="requirements" name="requirements" className="form-textarea" rows="4" placeholder="What legal services do you need?" required></textarea>
                  </div>

                  <div className="form-group">
                    <label htmlFor="expectations" className="form-label">
                      What Do You Expect? <span className="required">*</span>
                    </label>
                    <textarea id="expectations" name="expectations" className="form-textarea" rows="3" placeholder="What outcome or resolution are you seeking?" required></textarea>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="urgency" className="form-label">
                        Urgency Level <span className="required">*</span>
                      </label>
                      <select id="urgency" name="urgency" className="form-input" required defaultValue="">
                        <option value="" disabled>Select urgency</option>
                        <option value="low">Low - Can wait a few weeks</option>
                        <option value="medium">Medium - Within a week</option>
                        <option value="high">High - Within 2-3 days</option>
                        <option value="urgent">Urgent - Immediate attention needed</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="preferredDate" className="form-label">
                        Preferred Consultation Date <span className="optional">(Optional)</span>
                      </label>
                      <input type="date" id="preferredDate" name="preferredDate" className="form-input" />
                    </div>
                  </div>

                  <div className="form-group">
                    <label htmlFor="previousLawyer" className="form-label">
                      Have you consulted a lawyer before for this matter?
                    </label>
                    <div className="radio-group">
                      <label className="radio-label">
                        <input type="radio" name="previousLawyer" value="yes" /> Yes
                      </label>
                      <label className="radio-label">
                        <input type="radio" name="previousLawyer" value="no" defaultChecked /> No
                      </label>
                    </div>
                  </div>
                </div>

                {/* Budget Information */}
                <div className="form-section">
                  <h2 className="section-title">Budget Information</h2>
                  
                  <div className="form-group">
                    <label htmlFor="budgetRange" className="form-label">
                      Budget Range (INR) <span className="required">*</span>
                    </label>
                    <select id="budgetRange" name="budgetRange" className="form-input" required defaultValue="">
                      <option value="" disabled>Select budget range</option>
                      <option value="under-10k">Under ₹10,000</option>
                      <option value="10k-25k">₹10,000 - ₹25,000</option>
                      <option value="25k-50k">₹25,000 - ₹50,000</option>
                      <option value="50k-1l">₹50,000 - ₹1,00,000</option>
                      <option value="above-5l">Above ₹5,00,000</option>
                      <option value="flexible">Flexible</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="additionalNotes" className="form-label">
                      Additional Notes <span className="optional">(Optional)</span>
                    </label>
                    <textarea id="additionalNotes" name="additionalNotes" className="form-textarea" rows="3" placeholder="Any other information you'd like to share..."></textarea>
                  </div>
                </div>

                {/* Submit Actions */}
                <div className="form-actions">
                  <button type="button" className="cancel-button" onClick={() => window.history.back()}>
                    Cancel
                  </button>
                  <button type="submit" className="submit-button" disabled={loading}>
                    <span className="button-text">{loading ? 'Submitting...' : 'Submit Inquiry'}</span>
                  </button>
                </div>
              </form>
            )}

            {success && (
              <div className="success-container">
                <div className="success-icon">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>
                </div>
                <h2 className="success-title">Inquiry Submitted Successfully!</h2>
                <p className="success-message">
                  Thank you for your inquiry. Our legal team will review your case and contact you within 24-48 hours.
                </p>
                <div className="success-actions">
                  <Link href="/search" className="primary-button" style={{ display: 'inline-block', textDecoration: 'none' }}>Back to Search</Link>
                </div>
              </div>
            )}
            
            {loading && !success && (
              <div className="loading-overlay">
                <div className="loading-spinner"></div>
                <p>Submitting your inquiry...</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

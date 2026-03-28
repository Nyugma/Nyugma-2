'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getBackendUrl } from '../../utils/api';
import { setAuthData, isAuthenticated } from '../../utils/auth';

export default function AuthPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated()) {
      router.push('/dashboard');
    }
  }, [router]);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData(e.target);
    const email = formData.get('email');
    const password = formData.get('password');

    try {
      // FastAPI expects x-www-form-urlencoded for OAuth2 password flow
      const urlEncodedData = new URLSearchParams();
      urlEncodedData.append('username', email); // FastAPI OAuth2 uses 'username' field
      urlEncodedData.append('password', password);

      const response = await fetch(`${getBackendUrl()}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: urlEncodedData.toString(),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Login failed. Please check your credentials.');
      }

      const data = await response.json();
      
      // Fetch user profile
      const userResponse = await fetch(`${getBackendUrl()}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${data.access_token}`
        }
      });

      if (!userResponse.ok) {
        throw new Error('Failed to fetch user profile.');
      }

      const userData = await userResponse.json();
      
      // Save credentials using auth utility
      setAuthData(data.access_token, userData);

      // Redirect based on user type
      if (userData.user_type === 'helper') {
        router.push('/helper-dashboard');
      } else {
        router.push('/dashboard');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData(e.target);
    const data = {
      email: formData.get('email'),
      full_name: formData.get('full_name'),
      password: formData.get('password'),
      user_type: formData.get('user_type'),
      phone: formData.get('phone') || null,
      city: formData.get('city') || null,
      state: formData.get('state') || null,
    };

    try {
      const response = await fetch(`${getBackendUrl()}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        if (errData.detail && Array.isArray(errData.detail)) {
          throw new Error(errData.detail[0].msg);
        }
        throw new Error(errData.detail || 'Registration failed. Email might be taken.');
      }

      setSuccess('Registration successful! Please login.');
      setActiveTab('login');
      e.target.reset(); // clear form
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    setLoading(true);
    
    // Simulate OAuth Delay
    setTimeout(() => {
        // Read user type preference from the active tab if they're registering
        let selectedType = 'new_litigant';
        if (activeTab === 'register') {
           const typeInput = document.querySelector('input[name="user_type"]:checked');
           if (typeInput) selectedType = typeInput.value;
        }

        const mockGoogleUser = {
            user_id: Math.floor(Math.random() * 10000),
            email: "test.google.user@gmail.com",
            full_name: "Google Test User",
            user_type: selectedType,
            phone: "+91 9876543210", 
            city: "Mumbai",
            state: "Maharashtra",
            created_at: new Date().toISOString(),
            cases_helped: 0,
            total_ratings: 0,
            reputation_score: 5.0
        };

        // Create a fake JWT token
        const mockToken = "mock_google_jwt_" + Math.random().toString(36).substring(7);
        
        // Save the session using auth utility
        setAuthData(mockToken, mockGoogleUser);
        
        // Redirect to appropriate dashboard
        setLoading(false);
        if (mockGoogleUser.user_type === 'helper') {
            router.push('/helper-dashboard');
        } else {
            router.push('/dashboard');
        }
    }, 1500);
  };

  return (
    <div className="auth-container" style={{maxWidth: '500px', margin: '60px auto', padding: '0 20px'}}>
      <div className="auth-box" style={{background: '#fff', borderRadius: '16px', boxShadow: '0 10px 25px rgba(0,0,0,0.1)', overflow: 'hidden'}}>
        
        {/* Tab Navigation */}
        <div className="auth-tabs" style={{display: 'flex', borderBottom: '1px solid #e5e7eb'}}>
          <button 
            className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`} 
            onClick={() => { setActiveTab('login'); setError(null); setSuccess(null); }}
            style={{flex: 1, padding: '16px', background: 'none', border: 'none', borderBottom: activeTab === 'login' ? '2px solid #667eea' : '2px solid transparent', color: activeTab === 'login' ? '#667eea' : '#6b7280', fontWeight: 'bold', cursor: 'pointer', transition: 'all 0.2s'}}
          >
            Login
          </button>
          <button 
            className={`auth-tab ${activeTab === 'register' ? 'active' : ''}`} 
            onClick={() => { setActiveTab('register'); setError(null); setSuccess(null); }}
            style={{flex: 1, padding: '16px', background: 'none', border: 'none', borderBottom: activeTab === 'register' ? '2px solid #667eea' : '2px solid transparent', color: activeTab === 'register' ? '#667eea' : '#6b7280', fontWeight: 'bold', cursor: 'pointer', transition: 'all 0.2s'}}
          >
            Register
          </button>
        </div>

        <div style={{padding: '32px'}}>
          {error && <div style={{marginBottom: '20px', padding: '12px', background: '#fee2e2', color: '#dc2626', borderRadius: '8px', fontSize: '14px'}}>{error}</div>}
          {success && <div style={{marginBottom: '20px', padding: '12px', background: '#d1fae5', color: '#059669', borderRadius: '8px', fontSize: '14px'}}>{success}</div>}
          
          {/* Login Form */}
          {activeTab === 'login' && (
            <div className="auth-form-container">
              <h2 style={{fontSize: '24px', fontWeight: 'bold', marginBottom: '8px', color: '#1f2937'}}>Welcome Back</h2>
              <p style={{color: '#6b7280', marginBottom: '24px'}}>Login to access your account</p>

              <form onSubmit={handleLoginSubmit} style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
                <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                  <label htmlFor="loginEmail" style={{fontSize: '14px', fontWeight: '500', color: '#374151'}}>Email Address</label>
                  <input type="email" id="loginEmail" name="email" required style={{padding: '12px 16px', borderRadius: '8px', border: '1px solid #d1d5db', fontSize: '15px'}} placeholder="your.email@example.com" />
                </div>

                <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                  <label htmlFor="loginPassword" style={{fontSize: '14px', fontWeight: '500', color: '#374151'}}>Password</label>
                  <input type="password" id="loginPassword" name="password" required style={{padding: '12px 16px', borderRadius: '8px', border: '1px solid #d1d5db', fontSize: '15px'}} placeholder="Enter your password" />
                </div>

                <button type="submit" disabled={loading} style={{background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', padding: '14px', borderRadius: '8px', border: 'none', fontWeight: '600', fontSize: '16px', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1}}>
                  {loading ? 'Logging in...' : 'Login'}
                </button>

                {/* Google Login Placeholder UI */}
                <div style={{ display: 'flex', alignItems: 'center', margin: '8px 0', color: '#9ca3af', fontSize: '14px' }}>
                    <hr style={{ flex: 1, borderColor: '#e5e7eb', borderTop: 'none' }}/>
                    <span style={{ padding: '0 10px' }}>OR</span>
                    <hr style={{ flex: 1, borderColor: '#e5e7eb', borderTop: 'none' }}/>
                </div>

                <button type="button" onClick={handleGoogleLogin} style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', background: '#fff', color: '#374151', padding: '12px', borderRadius: '8px', border: '1px solid #d1d5db', fontWeight: '600', fontSize: '15px', cursor: 'pointer', transition: 'background 0.2s'}}>
                  <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  Login with Google
                </button>
              </form>
            </div>
          )}

          {/* Register Form */}
          {activeTab === 'register' && (
            <div className="auth-form-container">
              <h2 style={{fontSize: '24px', fontWeight: 'bold', marginBottom: '8px', color: '#1f2937'}}>Create Account</h2>
              <p style={{color: '#6b7280', marginBottom: '24px'}}>Join our legal community</p>

              <form onSubmit={handleRegisterSubmit} style={{display: 'flex', flexDirection: 'column', gap: '16px'}}>
                <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '6px'}}>
                  <label htmlFor="registerName" style={{fontSize: '13px', fontWeight: '600', color: '#374151'}}>Full Name *</label>
                  <input type="text" id="registerName" name="full_name" required minLength="2" style={{padding: '10px 14px', borderRadius: '6px', border: '1px solid #d1d5db'}} placeholder="Enter your full name" />
                </div>

                <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '6px'}}>
                  <label htmlFor="registerEmail" style={{fontSize: '13px', fontWeight: '600', color: '#374151'}}>Email Address *</label>
                  <input type="email" id="registerEmail" name="email" required style={{padding: '10px 14px', borderRadius: '6px', border: '1px solid #d1d5db'}} placeholder="your.email@example.com" />
                </div>

                <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '6px'}}>
                  <label htmlFor="registerPhone" style={{fontSize: '13px', fontWeight: '600', color: '#374151'}}>Phone Number</label>
                  <input type="tel" id="registerPhone" name="phone" maxLength="17" style={{padding: '10px 14px', borderRadius: '6px', border: '1px solid #d1d5db'}} placeholder="+91 XXXXX XXXXX" />
                </div>
                
                <div style={{display: 'flex', gap: '12px'}}>
                  <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '6px', flex: 1}}>
                    <label htmlFor="registerCity" style={{fontSize: '13px', fontWeight: '600', color: '#374151'}}>City</label>
                    <input type="text" id="registerCity" name="city" style={{padding: '10px 14px', borderRadius: '6px', border: '1px solid #d1d5db'}} placeholder="Your city" />
                  </div>

                  <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '6px', flex: 1}}>
                    <label htmlFor="registerState" style={{fontSize: '13px', fontWeight: '600', color: '#374151'}}>State</label>
                    <input type="text" id="registerState" name="state" style={{padding: '10px 14px', borderRadius: '6px', border: '1px solid #d1d5db'}} placeholder="Your state" />
                  </div>
                </div>

                <div className="form-group" style={{display: 'flex', flexDirection: 'column', gap: '6px'}}>
                  <label htmlFor="registerPassword" style={{fontSize: '13px', fontWeight: '600', color: '#374151'}}>Password *</label>
                  <input type="password" id="registerPassword" name="password" required minLength="8" style={{padding: '10px 14px', borderRadius: '6px', border: '1px solid #d1d5db'}} placeholder="Create a strong password" />
                </div>

                <div className="form-group" style={{marginTop: '8px'}}>
                    <label style={{fontSize: '13px', fontWeight: '600', color: '#374151', display: 'block', marginBottom: '8px'}}>I am a:</label>
                    <div style={{display: 'flex', gap: '16px'}}>
                        <label style={{display: 'flex', gap: '8px', alignItems: 'center', cursor: 'pointer', background: '#f9fafb', padding: '12px', border: '1px solid #e5e7eb', borderRadius: '8px', flex: 1}}>
                            <input type="radio" name="user_type" value="new_litigant" defaultChecked />
                            <div>
                                <strong style={{display: 'block', fontSize: '14px'}}>New Litigant</strong>
                                <small style={{color: '#6b7280', fontSize: '12px'}}>I need help</small>
                            </div>
                        </label>
                        <label style={{display: 'flex', gap: '8px', alignItems: 'center', cursor: 'pointer', background: '#f9fafb', padding: '12px', border: '1px solid #e5e7eb', borderRadius: '8px', flex: 1}}>
                            <input type="radio" name="user_type" value="helper" />
                            <div>
                                <strong style={{display: 'block', fontSize: '14px'}}>Helper</strong>
                                <small style={{color: '#6b7280', fontSize: '12px'}}>I provide help</small>
                            </div>
                        </label>
                    </div>
                </div>

                <button type="submit" disabled={loading} style={{background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', padding: '14px', borderRadius: '8px', border: 'none', fontWeight: '600', fontSize: '16px', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1, marginTop: '12px'}}>
                  {loading ? 'Creating Account...' : 'Register'}
                </button>

                {/* Google Register Placeholder UI */}
                <div style={{ display: 'flex', alignItems: 'center', margin: '8px 0', color: '#9ca3af', fontSize: '14px' }}>
                    <hr style={{ flex: 1, borderColor: '#e5e7eb', borderTop: 'none' }}/>
                    <span style={{ padding: '0 10px' }}>OR</span>
                    <hr style={{ flex: 1, borderColor: '#e5e7eb', borderTop: 'none' }}/>
                </div>

                <button type="button" onClick={handleGoogleLogin} style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', background: '#fff', color: '#374151', padding: '12px', borderRadius: '8px', border: '1px solid #d1d5db', fontWeight: '600', fontSize: '15px', cursor: 'pointer', transition: 'background 0.2s'}}>
                  <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  Register with Google
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

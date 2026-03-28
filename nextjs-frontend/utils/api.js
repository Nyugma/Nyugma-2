/**
 * API Utility Functions
 * Wrapper around fetch to handle base URL and authentication tokens
 */

import { getAccessToken, logout } from './auth';

/**
 * Get the backend URL from environment variables
 */
export function getBackendUrl() {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

/**
 * Make an authenticated API request
 * @param {string} endpoint - The API endpoint path (e.g. '/api/upload')
 * @param {Object} options - Fetch options
 */
export async function authenticatedFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') 
    ? endpoint 
    : `${getBackendUrl()}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    
  const token = getAccessToken();
  
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`
  };
  
  const response = await fetch(url, {
    ...options,
    headers
  });
  
  // Handle 401 Unauthorized - token expired or invalid
  if (response.status === 401) {
    logout();
    throw new Error('Session expired. Please login again.');
  }
  
  return response;
}

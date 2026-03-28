/**
 * Authentication utility functions
 * Client-side only wrappers around localStorage
 */

/**
 * Check if we are running on the client side
 */
const isClient = typeof window !== 'undefined';

/**
 * Get current user from localStorage
 */
export function getCurrentUser() {
  if (!isClient) return null;
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}

/**
 * Get access token from localStorage
 */
export function getAccessToken() {
  if (!isClient) return null;
  return localStorage.getItem('access_token');
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
  return !!getAccessToken();
}

/**
 * Login user - saves token and user to localStorage
 */
export function setAuthData(token, user) {
  if (!isClient) return;
  localStorage.setItem('access_token', token);
  localStorage.setItem('user', JSON.stringify(user));
  // In Next.js, we should also set a cookie for middleware
  document.cookie = `access_token=${token}; path=/; max-age=86400; SameSite=Strict;`;
}

/**
 * Logout user
 */
export function logout() {
  if (!isClient) return;
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
  window.location.href = '/auth'; // Hard redirect to force clean state
}

/**
 * Check if user is of specific type ('helper' or 'new_litigant')
 */
export function isUserType(requiredType) {
  const user = getCurrentUser();
  return user && user.user_type === requiredType;
}

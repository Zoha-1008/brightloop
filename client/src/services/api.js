const API_BASE = '/api';

export async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem('brightloop_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data.error || data.message || `Request failed with status ${response.status}`;
    const error = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const api = {
  // Auth
  login: (credentials) => apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials)
  }),
  registerCustomer: (customerData) => apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify(customerData)
  }),
  forgotPassword: (email) => apiRequest('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email })
  }),
  resetPassword: (payload) => apiRequest('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  getMe: () => apiRequest('/auth/me'),

  // Admin
  registerStaff: (staffData) => apiRequest('/admin/register-staff', {
    method: 'POST',
    body: JSON.stringify(staffData)
  }),
  getAdminDashboard: () => apiRequest('/admin/dashboard'),
  getStaffList: () => apiRequest('/admin/staff'),
  getCustomerList: () => apiRequest('/admin/customers'),
  getDatabaseTables: () => apiRequest('/admin/tables'),

  // Customer
  getCustomerDashboard: () => apiRequest('/customer/dashboard'),

  // Profile
  getProfile: () => apiRequest('/profile'),
  updateProfile: (profileData) => apiRequest('/profile', {
    method: 'PUT',
    body: JSON.stringify(profileData)
  }),
  changePassword: (passwords) => apiRequest('/profile/change-password', {
    method: 'PUT',
    body: JSON.stringify(passwords)
  })
};

import api from './client';

export interface UserProfile {
  id: string;
  full_name: string;
  email: string;
  email_verified: boolean;
  status: string;
  last_login: string | null;
  created_at: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user: UserProfile;
  accessToken: string;
  refreshToken: string;
  session_id: string;
  expires_at: string;
}

export interface RegisterResponse {
  success: boolean;
  message: string;
  user_id: string;
}

export const authApi = {
  async register(data: { full_name: string; email: string; password: string }) {
    const res = await api.post<RegisterResponse>('/api/auth/register', data);
    return res.data;
  },

  async verifyEmail(token: string) {
    const res = await api.get('/api/auth/verify', { params: { token } });
    return res.data as { success: boolean; message: string };
  },

  async login(email: string, password: string, device_name?: string) {
    const res = await api.post<AuthResponse>('/api/auth/login', {
      email,
      password,
      device_name,
    });
    return res.data;
  },

  async logout(session_id: string) {
    const res = await api.post('/api/auth/logout', { session_id });
    return res.data as { success: boolean; message: string };
  },

  async forgotPassword(email: string) {
    const res = await api.post('/api/auth/forgot-password', { email });
    return res.data as { success: boolean; message: string };
  },

  async resetPassword(token: string, new_password: string) {
    const res = await api.post('/api/auth/reset-password', {
      token,
      new_password,
    });
    return res.data as { success: boolean; message: string };
  },

  async resendVerification(email: string) {
    const res = await api.post('/api/auth/resend-verification', { email });
    return res.data as { success: boolean; message: string };
  },

  async getMe() {
    const res = await api.get('/api/auth/me');
    return res.data as { success: boolean; user: UserProfile };
  },

  async refreshToken(refresh_token: string) {
    const res = await api.post('/api/auth/refresh', { refresh_token });
    return res.data as { success: boolean; accessToken: string; refreshToken: string; expires_at: string };
  },
};

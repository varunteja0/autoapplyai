import axios from 'axios';
import type {
  Application,
  ApplicationLog,
  ApplicationStats,
  Job,
  Resume,
  TokenResponse,
  User,
  UserProfile,
} from '../types';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post<TokenResponse>(
            `${API_BASE}/auth/refresh`,
            null,
            { params: { refresh_token: refreshToken } }
          );
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post<TokenResponse>('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post<TokenResponse>('/auth/login', data),
};

// Users
export const userApi = {
  getMe: () => api.get<User>('/users/me'),
  updateMe: (data: Partial<User>) => api.patch<User>('/users/me', data),
  getProfile: () => api.get<UserProfile | null>('/users/me/profile'),
  upsertProfile: (data: Partial<UserProfile>) =>
    api.put<UserProfile>('/users/me/profile', data),
};

// Jobs
export const jobApi = {
  create: (data: { url: string; title?: string; company?: string }) =>
    api.post<Job>('/jobs/', data),
  createBulk: (urls: string[]) => api.post<Job[]>('/jobs/bulk', { urls }),
  list: (skip = 0, limit = 50) =>
    api.get<Job[]>('/jobs/', { params: { skip, limit } }),
  get: (id: string) => api.get<Job>(`/jobs/${id}`),
  delete: (id: string) => api.delete(`/jobs/${id}`),
};

// Applications
export const applicationApi = {
  create: (data: { job_id: string; resume_id?: string }) =>
    api.post<Application>('/applications/', data),
  createBulk: (data: { job_ids: string[]; resume_id?: string }) =>
    api.post<{ task_id: string; job_count: number; status: string }>(
      '/applications/bulk',
      data
    ),
  applyAll: (resumeId?: string) =>
    api.post<{ task_id: string; job_count: number; status: string }>(
      '/applications/apply-all',
      null,
      { params: resumeId ? { resume_id: resumeId } : {} }
    ),
  list: (skip = 0, limit = 50, status?: string) =>
    api.get<Application[]>('/applications/', {
      params: { skip, limit, status },
    }),
  get: (id: string) => api.get<Application>(`/applications/${id}`),
  getStats: () => api.get<ApplicationStats>('/applications/stats'),
  getLogs: (id: string) =>
    api.get<ApplicationLog[]>(`/applications/${id}/logs`),
  retry: (id: string) => api.post<Application>(`/applications/${id}/retry`),
  cancel: (id: string) => api.post<Application>(`/applications/${id}/cancel`),
};

// Resumes
export const resumeApi = {
  upload: (name: string, file: File, isDefault = false) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<Resume>('/resumes/', formData, {
      params: { name, is_default: isDefault },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  list: () => api.get<Resume[]>('/resumes/'),
  get: (id: string) => api.get<Resume>(`/resumes/${id}`),
  setDefault: (id: string) => api.patch<Resume>(`/resumes/${id}/default`),
  delete: (id: string) => api.delete(`/resumes/${id}`),
};

export default api;

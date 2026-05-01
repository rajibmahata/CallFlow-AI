import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<{ access_token: string; token_type: string }>('/auth/login', { email, password }),
  me: () => apiClient.get<{ id: number; email: string; role: string; full_name: string }>('/auth/me'),
}

// ── Campaigns ─────────────────────────────────────────────────────────────────
export interface Campaign {
  id: number
  name: string
  event_name: string
  event_date: string
  event_location?: string
  llm_provider: 'openai' | 'deepseek'
  is_active: boolean
  capacity?: number
  max_daily_calls: number
}

export const campaignsApi = {
  list: () => apiClient.get<Campaign[]>('/campaigns/'),
  get: (id: number) => apiClient.get<Campaign>(`/campaigns/${id}`),
  create: (data: Partial<Campaign>) => apiClient.post<Campaign>('/campaigns/', data),
  start: (id: number, batchSize = 50) =>
    apiClient.post(`/campaigns/${id}/start`, { batch_size: batchSize }),
}

// ── Leads ─────────────────────────────────────────────────────────────────────
export interface Lead {
  id: number
  name: string
  phone: string
  email?: string
  city?: string
  language: string
  status: string
  ai_summary?: string
  sentiment_score?: number
  confidence_score?: number
  attendees_count: number
  campaign_id: number
}

export type LeadStatus =
  | 'new' | 'queued' | 'calling' | 'answered' | 'interested'
  | 'needs_confirmation' | 'confirmed' | 'attended'
  | 'not_interested' | 'callback' | 'no_answer'

export const leadsApi = {
  list: (params?: { campaign_id?: number; status?: string; page?: number; size?: number }) =>
    apiClient.get<{ items: Lead[]; total: number; page: number; size: number }>('/leads/', { params }),
  upload: (campaignId: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    form.append('campaign_id', String(campaignId))
    return apiClient.post('/leads/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  approve: (id: number) => apiClient.post(`/leads/${id}/approve`),
  reject: (id: number, reason?: string) => apiClient.post(`/leads/${id}/reject`, { reason }),
}

// ── Call Logs ─────────────────────────────────────────────────────────────────
export interface CallLog {
  id: number
  lead_id: number
  campaign_id: number
  retell_call_id?: string
  status: string
  intent?: string
  duration_seconds?: number
  recording_url?: string
  ai_summary?: string
  sentiment_score?: number
  confidence_score?: number
  started_at?: string
  ended_at?: string
}

export const callsApi = {
  list: (params?: { campaign_id?: number; lead_id?: number }) =>
    apiClient.get<CallLog[]>('/calls/', { params }),
  initiate: (leadId: number, campaignId: number) =>
    apiClient.post<{ retell_call_id: string }>('/calls/initiate', { lead_id: leadId, campaign_id: campaignId }),
}

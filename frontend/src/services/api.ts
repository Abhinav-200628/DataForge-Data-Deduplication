import {
  AvailableFile,
  DashboardSummary,
  DataQualitySummary,
  HealthStatus,
  MasterLineageDetail,
  RecordListResponse,
  ReviewItem,
  ReviewQueueResponse,
  RunListResponse,
  PipelineRun,
  RunTriggerRequest,
  SettingsData,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  getHealth: () => fetchJson<HealthStatus>('/health'),

  getDashboardSummary: () => fetchJson<DashboardSummary>('/dashboard/summary'),

  listRuns: (params?: { entity_type?: string; status?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.status) query.append('status', params.status);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());
    return fetchJson<RunListResponse>(`/runs?${query.toString()}`);
  },

  getRun: (runId: string) => fetchJson<PipelineRun>(`/runs/${runId}`),

  triggerRun: (payload: RunTriggerRequest) =>
    fetchJson<{ run_id: string; entity_type: string; status: string; message: string }>('/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listAvailableFiles: () => fetchJson<{ files: AvailableFile[] }>('/files/available'),

  listRecords: (params: { entity_type: 'customer' | 'product'; search?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams({ entity_type: params.entity_type });
    if (params.search) query.append('search', params.search);
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());
    return fetchJson<RecordListResponse>(`/records?${query.toString()}`);
  },

  getRecordLineage: (entityType: string, masterId: string) =>
    fetchJson<MasterLineageDetail>(`/records/${entityType}/${masterId}/lineage`),

  listReviewQueue: (params?: { entity_type?: string; status?: string; search?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.status) query.append('status', params.status);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.page_size) query.append('page_size', params.page_size.toString());
    return fetchJson<ReviewQueueResponse>(`/review-queue?${query.toString()}`);
  },

  updateReviewAction: (reviewId: string, status: 'APPROVED' | 'REJECTED' | 'RESOLVED', notes?: string) =>
    fetchJson<{ review_id: string; status: string; updated_at: string; message: string }>(
      `/review-queue/${reviewId}/action`,
      {
        method: 'POST',
        body: JSON.stringify({ status, notes }),
      }
    ),

  getDataQualitySummary: (page = 1, pageSize = 20) =>
    fetchJson<DataQualitySummary>(`/data-quality/summary?page=${page}&page_size=${pageSize}`),

  getRunReport: (runId: string) => fetchJson<any>(`/reports/${runId}`),

  getSettings: () => fetchJson<SettingsData>('/settings'),
};


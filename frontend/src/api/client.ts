import axios, { AxiosError } from 'axios';
import type {
  ParseResponse,
  Platform,
  ValidationReport,
  GenerationRequest,
  GenerationResult,
} from '../types/platform';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
});

// ─── Request/Response interceptors ────────────────────────────────────────────

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const message =
      (error.response?.data as { detail?: string })?.detail ||
      error.message ||
      'An unexpected error occurred';
    return Promise.reject(new Error(message));
  }
);

// ─── Diagram Parsing ───────────────────────────────────────────────────────────

export async function parseDiagram(file: File): Promise<ParseResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<ParseResponse>('/diagram/parse', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function parseMermaid(
  text: string,
  name: string
): Promise<ParseResponse> {
  const response = await api.post<ParseResponse>('/diagram/mermaid', {
    text,
    name,
  });
  return response.data;
}

// ─── Architecture Validation ───────────────────────────────────────────────────

export async function validateArchitecture(
  platform: Platform
): Promise<ValidationReport> {
  const response = await api.post<ValidationReport>(
    '/architecture/validate',
    platform
  );
  return response.data;
}

// ─── Generation ────────────────────────────────────────────────────────────────

export async function generate(
  request: GenerationRequest
): Promise<GenerationResult> {
  const response = await api.post<GenerationResult>('/generate/', request);
  return response.data;
}

// ─── Export ────────────────────────────────────────────────────────────────────

export async function exportZip(request: GenerationRequest): Promise<Blob> {
  const response = await api.post('/export/zip', request, {
    responseType: 'blob',
  });
  return response.data as Blob;
}

// ─── Named exports bundle ─────────────────────────────────────────────────────

const apiClient = {
  parseDiagram,
  parseMermaid,
  validateArchitecture,
  generate,
  exportZip,
};

export default apiClient;

import axios from "axios";
import type {
  PreviewResponse,
  Report,
  ReportInput,
  ReportRun,
  Team,
  TeamRole,
  User,
} from "./types";

const api = axios.create({ baseURL: "/" });

const TOKEN_KEY = "reportes_token";

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      setToken(null);
      if (!location.pathname.startsWith("/login")) location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export const auth = {
  async login(email: string, password: string) {
    const { data } = await api.post<{ access_token: string; user: User }>(
      "/api/auth/login",
      { email, password }
    );
    setToken(data.access_token);
    return data.user;
  },
  me: () => api.get<User>("/api/auth/me").then((r) => r.data),
  logout() {
    setToken(null);
  },
};

export interface MembershipInput {
  team_id: number;
  role: TeamRole;
}

export interface AdminUserInput {
  email: string;
  password: string;
  is_admin: boolean;
  memberships: MembershipInput[];
}

export interface AdminUserUpdate {
  is_active?: boolean;
  is_admin?: boolean;
  password?: string;
  memberships?: MembershipInput[];
}

export const adminApi = {
  listTeams: () => api.get<Team[]>("/api/admin/teams").then((r) => r.data),
  createTeam: (name: string) =>
    api.post<Team>("/api/admin/teams", { name }).then((r) => r.data),
  updateTeam: (id: number, name: string) =>
    api.patch<Team>(`/api/admin/teams/${id}`, { name }).then((r) => r.data),
  deleteTeam: (id: number) => api.delete(`/api/admin/teams/${id}`),
  listUsers: () => api.get<User[]>("/api/admin/users").then((r) => r.data),
  createUser: (payload: AdminUserInput) =>
    api.post<User>("/api/admin/users", payload).then((r) => r.data),
  updateUser: (id: number, payload: AdminUserUpdate) =>
    api.patch<User>(`/api/admin/users/${id}`, payload).then((r) => r.data),
  deactivateUser: (id: number) => api.delete(`/api/admin/users/${id}`),
};

export const reportsApi = {
  list: () => api.get<Report[]>("/api/reports").then((r) => r.data),
  get: (id: number) => api.get<Report>(`/api/reports/${id}`).then((r) => r.data),
  create: (payload: ReportInput) =>
    api.post<Report>("/api/reports", payload).then((r) => r.data),
  update: (id: number, payload: ReportInput) =>
    api.put<Report>(`/api/reports/${id}`, payload).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/reports/${id}`),
  runNow: (id: number) =>
    api.post(`/api/reports/${id}/run`).then((r) => r.data),
  runs: (id: number) =>
    api.get<ReportRun[]>(`/api/reports/${id}/runs`).then((r) => r.data),
};

export const datadogApi = {
  fields: (sourceType: string) =>
    api
      .get<{ fields: string[] }>(`/api/datadog/fields`, {
        params: { source_type: sourceType },
      })
      .then((r) => r.data.fields),
  preview: (sourceType: string, query: string, timeWindow: string) =>
    api
      .post<PreviewResponse>("/api/datadog/preview", {
        source_type: sourceType,
        query,
        time_window: timeWindow,
        limit: 20,
      })
      .then((r) => r.data),
};

export function downloadUrl(runId: number) {
  return `/api/runs/${runId}/download`;
}

/**
 * Convierte un error de axios en un mensaje legible para el usuario.
 * El backend (FastAPI/Pydantic) puede devolver `detail` como string o como
 * array de errores de validación; aquí se normaliza a una sola frase.
 */
export function apiError(e: any, fallback = "Ocurrió un error inesperado"): string {
  const detail = e?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return (
      detail
        .map((d: any) => d?.msg ?? (typeof d === "string" ? d : JSON.stringify(d)))
        .filter(Boolean)
        .join("; ") || fallback
    );
  }
  return typeof detail === "object" ? fallback : String(detail);
}

export default api;

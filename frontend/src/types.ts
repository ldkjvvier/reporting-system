export type TeamRole = "editor" | "viewer";

export interface Team {
  id: number;
  name: string;
}

export interface Membership {
  team_id: number;
  team_name: string;
  role: TeamRole;
}

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  memberships: Membership[];
}

export interface Report {
  id: number;
  team_id: number;
  created_by_id: number | null;
  name: string;
  description: string;
  source_type: "logs" | "signals" | "metrics";
  query: string;
  time_window: string;
  columns: string[];
  output_format: "csv" | "xlsx";
  recipients: string[];
  cron: string;
  timezone: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  next_run: string | null;
}

export type ReportInput = Omit<
  Report,
  "id" | "created_by_id" | "created_at" | "updated_at" | "next_run"
>;

export interface ReportRun {
  id: number;
  report_id: number;
  status: "pending" | "running" | "success" | "failed";
  trigger: "manual" | "scheduled";
  started_at: string;
  finished_at: string | null;
  row_count: number;
  file_path: string | null;
  delivery_status: string | null;
  error_message: string | null;
}

export interface PreviewResponse {
  fields: string[];
  rows: Record<string, unknown>[];
  total: number;
  available_fields?: string[];
}

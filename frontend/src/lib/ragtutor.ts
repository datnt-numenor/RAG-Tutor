import api from "@/lib/api";

export type Project = {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  target_score: number | null;
  exam_date: string | null;
  weekly_study_minutes: number | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type DocumentRecord = {
  id: string;
  project_id: string;
  display_name: string;
  status: string;
  active_version_id: string | null;
  created_at: string;
  updated_at: string;
  document_versions?: {
    status: string;
    version_number: number;
  } | null;
};

export type DocumentJob = {
  id: string;
  document_id: string;
  document_version_id: string | null;
  job_type: "ingest" | "delete";
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  stage: string | null;
  progress_current: number;
  progress_total: number;
  attempt_count: number;
  max_attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatSession = {
  id: string;
  project_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Citation = {
  chunk_id?: string;
  document_id?: string;
  document_version_id?: string;
  source_file?: string;
  page?: number | null;
  similarity?: number;
};

export type ChatMessage = {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  status: string;
  citations?: Citation[] | null;
  retrieval_params?: Record<string, unknown> | null;
  model_name?: string | null;
  prompt_version?: string | null;
  created_at: string;
};

export async function listProjects() {
  const { data } = await api.get<Project[]>("/projects");
  return data;
}

export async function createProject(payload: {
  name: string;
  description?: string | null;
  target_score?: number | null;
  exam_date?: string | null;
  weekly_study_minutes?: number | null;
}) {
  const { data } = await api.post<Project>("/projects", payload);
  return data;
}

export async function getProject(projectId: string) {
  const { data } = await api.get<Project>(`/projects/${projectId}`);
  return data;
}

export async function listDocuments(projectId: string) {
  const { data } = await api.get<DocumentRecord[]>(
    `/projects/${projectId}/documents`,
  );
  return data;
}

export async function uploadDocument(projectId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<{
    document_id: string;
    version_id: string;
    job_id: string;
  }>(`/projects/${projectId}/documents`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listProjectJobs(projectId: string) {
  const { data } = await api.get<DocumentJob[]>(
    `/projects/${projectId}/document-jobs`,
  );
  return data;
}

export async function getJob(jobId: string) {
  const { data } = await api.get<DocumentJob>(`/document-jobs/${jobId}`);
  return data;
}

export async function retryJob(jobId: string) {
  const { data } = await api.post(`/document-jobs/${jobId}/retry`);
  return data;
}

export async function listChatSessions(projectId: string) {
  const { data } = await api.get<ChatSession[]>(
    `/projects/${projectId}/chat/sessions`,
  );
  return data;
}

export async function createChatSession(projectId: string) {
  const { data } = await api.post<ChatSession>(
    `/projects/${projectId}/chat/sessions`,
  );
  return data;
}

export async function listMessages(projectId: string, sessionId: string) {
  const { data } = await api.get<ChatMessage[]>(
    `/projects/${projectId}/chat/sessions/${sessionId}/messages`,
  );
  return data;
}

export async function sendMessage(
  projectId: string,
  sessionId: string,
  content: string,
) {
  const { data } = await api.post<ChatMessage>(
    `/projects/${projectId}/chat/sessions/${sessionId}/messages`,
    { content },
  );
  return data;
}

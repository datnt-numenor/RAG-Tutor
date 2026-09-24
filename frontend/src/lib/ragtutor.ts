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


export async function uploadDocumentVersion(
  projectId: string,
  documentId: string,
  file: File,
) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<{
    document_id: string;
    version_id: string;
    version_number: number;
    job_id: string;
  }>(`/projects/${projectId}/documents/${documentId}/versions`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function deleteDocument(projectId: string, documentId: string) {
  const { data } = await api.delete<{ job_id: string; message: string }>(
    `/projects/${projectId}/documents/${documentId}`,
  );
  return data;
}


export type QuizQuestion = {
  id: string;
  project_id: string;
  question_type: "mcq" | "essay";
  question_text: string;
  options: string[] | null;
  correct_answer: string | null;
  model_answer: string | null;
  key_points: string[] | null;
  max_score: number;
  model_name: string | null;
  prompt_version: string | null;
};

export type QuizSession = {
  id: string;
  project_id: string;
  user_id: string;
  status: "in_progress" | "submitted" | "graded" | "abandoned";
  question_ids: string[];
  total_score: number | null;
  max_score: number | null;
  started_at: string;
  submitted_at: string | null;
  graded_at: string | null;
};

export type QuizAttempt = {
  id: string;
  quiz_session_id: string;
  question_id: string | null;
  user_answer: string | null;
  score: number | null;
  is_correct: boolean | null;
  feedback: string | null;
  status: string;
};

export async function generateQuiz(
  projectId: string,
  payload: { count: number; question_type: "mcq" | "essay" },
) {
  const { data } = await api.post<{
    session: QuizSession;
    questions: QuizQuestion[];
  }>(\`/projects/\${projectId}/quiz/generate\`, payload);
  return data;
}

export async function listQuizSessions(projectId: string) {
  const { data } = await api.get<QuizSession[]>(
    \`/projects/\${projectId}/quiz/sessions\`,
  );
  return data;
}

export async function getQuizSession(projectId: string, sessionId: string) {
  const { data } = await api.get<{
    session: QuizSession;
    questions: QuizQuestion[];
    attempts: QuizAttempt[];
  }>(\`/projects/\${projectId}/quiz/sessions/\${sessionId}\`);
  return data;
}

export async function answerQuizQuestion(
  projectId: string,
  sessionId: string,
  questionId: string,
  answer: string,
) {
  const { data } = await api.post<QuizAttempt>(
    \`/projects/\${projectId}/quiz/sessions/\${sessionId}/questions/\${questionId}/answer\`,
    { answer },
  );
  return data;
}

export async function submitQuiz(projectId: string, sessionId: string) {
  const { data } = await api.post<QuizSession>(
    \`/projects/\${projectId}/quiz/sessions/\${sessionId}/submit\`,
  );
  return data;
}


export type ProgressOverview = {
  projects: number;
  documents: number;
  ready_documents: number;
  chat_sessions: number;
  chat_messages: number;
  quiz_sessions: number;
  quiz_attempts: number;
  quiz_correct: number;
  avg_quiz_score: number;
  reviews_due: number;
  project_breakdown: Array<{
    project_id: string;
    name: string;
    documents: number;
    ready_documents: number;
    chat_sessions: number;
    quiz_sessions: number;
    quiz_attempts: number;
    quiz_correct: number;
  }>;
};

export async function getProgressOverview() {
  const { data } = await api.get<ProgressOverview>("/progress/overview");
  return data;
}

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
  source_deleted?: boolean;
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
  submission_type?: "text" | "image_scan";
  user_answer: string | null;
  ocr_raw_text?: string | null;
  ocr_confirmed_text?: string | null;
  ocr_uncertain_regions?: Array<{ text: string; reason: string }> | null;
  image_storage_path?: string | null;
  image_deleted_at?: string | null;
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
  }>(`/projects/${projectId}/quiz/generate`, payload);
  return data;
}

export async function listQuizSessions(projectId: string) {
  const { data } = await api.get<QuizSession[]>(
    `/projects/${projectId}/quiz/sessions`,
  );
  return data;
}

export async function getQuizSession(projectId: string, sessionId: string) {
  const { data } = await api.get<{
    session: QuizSession;
    questions: QuizQuestion[];
    attempts: QuizAttempt[];
  }>(`/projects/${projectId}/quiz/sessions/${sessionId}`);
  return data;
}

export async function answerQuizQuestion(
  projectId: string,
  sessionId: string,
  questionId: string,
  answer: string,
) {
  const { data } = await api.post<QuizAttempt>(
    `/projects/${projectId}/quiz/sessions/${sessionId}/questions/${questionId}/answer`,
    { answer },
  );
  return data;
}

export async function submitQuiz(projectId: string, sessionId: string) {
  const { data } = await api.post<QuizSession>(
    `/projects/${projectId}/quiz/sessions/${sessionId}/submit`,
  );
  return data;
}


export type DueReviewState = {
  id: string;
  question_id: string;
  due_at: string;
  interval_days: number;
  repetitions: number;
  ease_factor: number;
  last_score: number | null;
  last_reviewed_at: string | null;
  questions: QuizQuestion;
};

export async function listDueReviews(projectId: string, limit = 20) {
  const { data } = await api.get<DueReviewState[]>(
    `/projects/${projectId}/reviews/due`,
    { params: { limit } },
  );
  return data;
}

export async function startDueReview(projectId: string, count = 10) {
  const { data } = await api.post<{
    session: QuizSession;
    questions: QuizQuestion[];
    review_states: Omit<DueReviewState, "questions">[];
  }>(`/projects/${projectId}/reviews/start`, { count });
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


export type ProjectInvitation = {
  id: string;
  invited_email: string;
  status: string;
  expires_at: string;
  created_at: string;
};

export async function createProjectInvitation(projectId: string, email: string) {
  const { data } = await api.post<{
    invitation_id: string;
    invite_link: string;
    expires_at: string;
  }>(`/projects/${projectId}/invitations`, { email });
  return data;
}

export async function listProjectInvitations(projectId: string) {
  const { data } = await api.get<ProjectInvitation[]>(
    `/projects/${projectId}/invitations`,
  );
  return data;
}

export async function revokeProjectInvitation(
  projectId: string,
  invitationId: string,
) {
  await api.delete(
    `/projects/${projectId}/invitations/${invitationId}`,
  );
}

export async function previewInvitation(rawToken: string) {
  const { data } = await api.get<{
    invitation_id: string;
    project_name: string;
    invited_by: string | null;
    expires_at: string;
  }>(`/invitations/${rawToken}`);
  return data;
}

export async function acceptInvitation(rawToken: string) {
  const { data } = await api.post<{ message: string }>(
    `/invitations/${rawToken}/accept`,
  );
  return data;
}

export async function rejectInvitation(rawToken: string) {
  await api.post(`/invitations/${rawToken}/reject`);
}


export type DocumentVersionDetail = {
  id: string;
  version_number: number;
  original_filename: string;
  mime_type: string;
  file_size: number;
  page_count: number | null;
  status: string;
  summary: string | null;
  summary_status: string | null;
  embedding_model: string | null;
  chunker_version: string | null;
  created_at: string;
  processed_at: string | null;
};

export type DocumentDetail = DocumentRecord & {
  versions: DocumentVersionDetail[];
};

export type AnnotationRectangle = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type AnnotationRecord = {
  id: string;
  user_id: string;
  project_id: string;
  document_id: string;
  document_version_id: string;
  page_number: number;
  annotation_type: "text_highlight" | "rectangle";
  selected_text: string | null;
  rectangles: AnnotationRectangle[] | null;
  content: string | null;
  color: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export async function getDocumentDetail(
  projectId: string,
  documentId: string,
) {
  const { data } = await api.get<DocumentDetail>(
    `/projects/${projectId}/documents/${documentId}`,
  );
  return data;
}

export async function getDocumentVersionSignedUrl(versionId: string) {
  const { data } = await api.get<{ signed_url: string }>(
    `/document-versions/${versionId}/signed-url`,
  );
  return data.signed_url;
}

export async function listAnnotations(
  projectId: string,
  documentId: string,
  versionId: string,
  page?: number,
) {
  const { data } = await api.get<AnnotationRecord[]>(
    `/projects/${projectId}/documents/${documentId}/versions/${versionId}/annotations`,
    { params: page ? { page } : undefined },
  );
  return data;
}

export async function createAnnotation(
  projectId: string,
  documentId: string,
  versionId: string,
  payload: {
    page_number: number;
    annotation_type: "text_highlight" | "rectangle";
    selected_text?: string | null;
    rectangles: AnnotationRectangle[];
    content?: string | null;
    color: string;
  },
) {
  const { data } = await api.post<AnnotationRecord>(
    `/projects/${projectId}/documents/${documentId}/versions/${versionId}/annotations`,
    payload,
  );
  return data;
}

export async function updateAnnotation(
  annotationId: string,
  payload: Partial<Pick<AnnotationRecord, "content" | "color" | "rectangles" | "selected_text">>,
) {
  const { data } = await api.patch<AnnotationRecord>(
    `/annotations/${annotationId}`,
    payload,
  );
  return data;
}

export async function deleteAnnotation(annotationId: string) {
  await api.delete(`/annotations/${annotationId}`);
}


export type RoadmapTopic = {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  difficulty: "basic" | "intermediate" | "advanced" | null;
  bloom_level: "remember" | "understand" | "apply" | "analyze" | null;
  is_core: boolean;
  model_name: string | null;
  prompt_version: string | null;
  created_at: string;
  order: number;
  prerequisites: string[];
};

export type RoadmapData = {
  project: {
    id: string;
    name: string;
    target_score: number | null;
    exam_date: string | null;
    weekly_study_minutes: number | null;
  };
  topics: RoadmapTopic[];
};

export type StudySchedule = {
  id: string;
  project_id: string;
  created_by: string;
  topic_id: string | null;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string | null;
  event_type: "study" | "quiz" | "review" | "deadline";
  source: "manual" | "ai_suggested";
  suggestion_status: "suggested" | "accepted" | "rejected";
  created_at: string;
  completed_by_me?: boolean;
  topics?: { id: string; name: string } | null;
};

export async function updateProject(
  projectId: string,
  payload: {
    name: string;
    description?: string | null;
    target_score?: number | null;
    exam_date?: string | null;
    weekly_study_minutes?: number | null;
  },
) {
  const { data } = await api.patch<Project>(`/projects/${projectId}`, payload);
  return data;
}

export async function getRoadmap(projectId: string) {
  const { data } = await api.get<RoadmapData>(
    `/projects/${projectId}/roadmap`,
  );
  return data;
}

export async function generateRoadmap(projectId: string) {
  const { data } = await api.post<{
    project_id: string;
    topics: RoadmapTopic[];
  }>(`/projects/${projectId}/roadmap/generate`);
  return data;
}

export async function listSchedules(projectId: string) {
  const { data } = await api.get<StudySchedule[]>(
    `/projects/${projectId}/schedules`,
  );
  return data;
}

export async function generateSchedules(projectId: string) {
  const { data } = await api.post<StudySchedule[]>(
    `/projects/${projectId}/schedules/generate`,
  );
  return data;
}

export async function acceptSchedule(scheduleId: string) {
  const { data } = await api.post<StudySchedule>(
    `/schedules/${scheduleId}/accept`,
  );
  return data;
}

export async function rejectSchedule(scheduleId: string) {
  const { data } = await api.post<StudySchedule>(
    `/schedules/${scheduleId}/reject`,
  );
  return data;
}

export async function completeSchedule(scheduleId: string) {
  const { data } = await api.post(
    `/schedules/${scheduleId}/complete`,
  );
  return data;
}

export async function uncompleteSchedule(scheduleId: string) {
  await api.delete(`/schedules/${scheduleId}/complete`);
}


export async function uploadEssayScan(
  projectId: string,
  sessionId: string,
  questionId: string,
  file: File,
) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<QuizAttempt>(
    `/projects/${projectId}/quiz/sessions/${sessionId}/questions/${questionId}/scan`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}

export async function confirmEssayScan(
  attemptId: string,
  text: string,
) {
  const { data } = await api.post<QuizAttempt>(
    `/quiz-attempts/${attemptId}/confirm-scan`,
    { text },
  );
  return data;
}

export async function getEssayScanSignedUrl(attemptId: string) {
  const { data } = await api.get<{ signed_url: string }>(
    `/quiz-attempts/${attemptId}/scan-url`,
  );
  return data.signed_url;
}

export async function deleteEssayScan(attemptId: string) {
  await api.delete(`/quiz-attempts/${attemptId}/scan`);
}

export async function startQuizFromBank(
  projectId: string,
  payload: { count: number; question_type?: "mcq" | "essay" | null },
) {
  const { data } = await api.post<{
    session: QuizSession;
    questions: QuizQuestion[];
  }>(`/projects/${projectId}/quiz/start`, payload);
  return data;
}


export type ProgressSnapshot = {
  id: string;
  user_id: string;
  project_id: string;
  snapshot_date: string;
  questions_attempted: number;
  questions_correct: number;
  avg_score: number;
  topics_covered: number;
  study_minutes: number;
  created_at: string;
  projects?: { name: string } | null;
};

export async function getProgressHistory(
  days = 30,
  projectId?: string,
) {
  const { data } = await api.get<ProgressSnapshot[]>("/progress/history", {
    params: {
      days,
      ...(projectId ? { project_id: projectId } : {}),
    },
  });
  return data;
}

export async function rebuildProgress(
  projectId: string,
  days = 30,
) {
  const { data } = await api.post<{
    project_id: string;
    start_date: string;
    end_date: string;
    snapshots_rebuilt: number;
  }>(`/projects/${projectId}/progress/rebuild`, null, {
    params: { days },
  });
  return data;
}


export type ChatStreamEvent =
  | {
      type: "meta";
      payload: {
        status: string;
        sources: Citation[];
        retrieval_params: Record<string, unknown>;
      };
    }
  | { type: "token"; payload: { text: string } }
  | { type: "done"; payload: { message_id: string } }
  | { type: "error"; payload: { message: string; error_type?: string } };

export async function streamChatMessage(
  projectId: string,
  sessionId: string,
  content: string,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000/api/v1";
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("sb-access-token")
      : null;

  const response = await fetch(
    `${baseUrl}/projects/${projectId}/chat/sessions/${sessionId}/messages/stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    },
  );

  if (!response.ok) {
    let detail = "Streaming chat request failed";
    try {
      const payload = await response.json();
      detail =
        typeof payload?.detail === "string"
          ? payload.detail
          : JSON.stringify(payload?.detail ?? payload);
    } catch {
      // Keep generic message.
    }
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("Streaming response has no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  function processBlock(block: string) {
    let eventName = "";
    const dataLines: string[] = [];

    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice("event:".length).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice("data:".length).trimStart());
      }
    }

    if (!eventName || dataLines.length === 0) return;

    const payload = JSON.parse(dataLines.join("\n"));
    onEvent({
      type: eventName,
      payload,
    } as ChatStreamEvent);
  }

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    let separator = buffer.indexOf("\n\n");
    while (separator >= 0) {
      const block = buffer.slice(0, separator).trim();
      buffer = buffer.slice(separator + 2);
      if (block) processBlock(block);
      separator = buffer.indexOf("\n\n");
    }

    if (done) break;
  }

  const finalBlock = buffer.trim();
  if (finalBlock) processBlock(finalBlock);
}


export type ProjectMember = {
  id: string;
  project_id: string;
  user_id: string;
  role: "owner" | "member";
  joined_at: string;
  users?: {
    id: string;
    full_name: string | null;
    email: string;
    avatar_url: string | null;
  } | null;
};

export async function listProjectMembers(projectId: string) {
  const { data } = await api.get<ProjectMember[]>(
    `/projects/${projectId}/members`,
  );
  return data;
}

export async function removeProjectMember(
  projectId: string,
  userId: string,
) {
  await api.delete(`/projects/${projectId}/members/${userId}`);
}


export type GlobalSearchResult = {
  type: "project" | "document";
  id: string;
  project_id: string;
  title: string;
  subtitle: string | null;
  href: string;
};

export async function globalSearch(query: string) {
  const { data } = await api.get<GlobalSearchResult[]>("/search", {
    params: { q: query },
  });
  return data;
}


export type UserProfile = {
  user_id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  timezone: string;
  created_at: string | null;
  updated_at: string | null;
};

export async function getMyProfile() {
  const { data } = await api.get<UserProfile>("/auth/me");
  return data;
}

export async function updateMyProfile(payload: {
  full_name?: string;
  timezone?: string;
}) {
  const { data } = await api.patch<UserProfile>("/auth/me", payload);
  return data;
}

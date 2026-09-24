"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  MessageSquare,
  Paperclip,
  RefreshCcw,
  Send,
  Upload,
} from "lucide-react";
import {
  createChatSession,
  getProject,
  listChatSessions,
  listDocuments,
  listMessages,
  listProjectJobs,
  retryJob,
  sendMessage,
  uploadDocument,
} from "@/lib/ragtutor";

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const documents = useQuery({
    queryKey: ["documents", projectId],
    queryFn: () => listDocuments(projectId),
    refetchInterval: 5000,
  });

  const jobs = useQuery({
    queryKey: ["document-jobs", projectId],
    queryFn: () => listProjectJobs(projectId),
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      return items.some((job) => ["queued", "running"].includes(job.status))
        ? 2500
        : 10000;
    },
  });

  const sessions = useQuery({
    queryKey: ["chat-sessions", projectId],
    queryFn: () => listChatSessions(projectId),
  });

  const effectiveSessionId = activeSessionId ?? sessions.data?.[0]?.id ?? null;

  const messages = useQuery({
    queryKey: ["messages", projectId, effectiveSessionId],
    queryFn: () => listMessages(projectId, effectiveSessionId!),
    enabled: Boolean(effectiveSessionId),
  });

  const upload = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error("No file selected");
      return uploadDocument(projectId, selectedFile);
    },
    onSuccess: async () => {
      setSelectedFile(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["documents", projectId] }),
        queryClient.invalidateQueries({ queryKey: ["document-jobs", projectId] }),
      ]);
    },
  });

  const createSession = useMutation({
    mutationFn: () => createChatSession(projectId),
    onSuccess: async (session) => {
      setActiveSessionId(session.id);
      await queryClient.invalidateQueries({ queryKey: ["chat-sessions", projectId] });
    },
  });

  const send = useMutation({
    mutationFn: async (content: string) => {
      let sessionId = effectiveSessionId;
      if (!sessionId) {
        const session = await createChatSession(projectId);
        sessionId = session.id;
        setActiveSessionId(session.id);
      }
      return sendMessage(projectId, sessionId, content);
    },
    onSuccess: async () => {
      setMessage("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["messages", projectId] }),
        queryClient.invalidateQueries({ queryKey: ["chat-sessions", projectId] }),
      ]);
    },
  });

  const retry = useMutation({
    mutationFn: retryJob,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["document-jobs", projectId] });
    },
  });

  const latestJobs = useMemo(() => jobs.data?.slice(0, 8) ?? [], [jobs.data]);

  function submitMessage(e: FormEvent) {
    e.preventDefault();
    const clean = message.trim();
    if (!clean || send.isPending) return;
    send.mutate(clean);
  }

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <section>
        <div className="font-hand text-2xl text-[#b9634c]">Project workspace</div>
        <h1 className="font-display mt-1 text-4xl font-semibold md:text-5xl">
          {project.data?.name ?? "Loading project..."}
        </h1>
        <p className="mt-2 max-w-3xl text-[#7d7167]">
          {project.data?.description || "Upload tài liệu, ingest thành chunks rồi chat bằng RAG trong cùng project."}
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_.95fr]">
        <div className="space-y-6">
          <div className="paper-card rounded-[26px] p-5 md:p-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h2 className="font-display text-2xl font-semibold">Documents</h2>
                <p className="mt-1 text-sm text-[#8a7b70]">PDF hoặc DOCX, tối đa 50 MB.</p>
              </div>
              <label className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-2xl bg-[#b9634c] px-4 py-2.5 text-sm font-semibold text-white">
                <Upload size={17} />
                Chọn file
                <input
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="hidden"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                />
              </label>
            </div>

            {selectedFile && (
              <div className="mt-4 flex flex-col gap-3 rounded-2xl bg-[#fff9f2] p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{selectedFile.name}</div>
                  <div className="mt-1 text-xs text-[#8a7b70]">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
                <button
                  onClick={() => upload.mutate()}
                  disabled={upload.isPending}
                  className="rounded-xl bg-[#8f4738] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {upload.isPending ? "Đang upload..." : "Upload & ingest"}
                </button>
              </div>
            )}

            {upload.isError && (
              <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
                Upload thất bại. Kiểm tra Redis/Celery worker và backend log.
              </div>
            )}

            <div className="mt-5 space-y-3">
              {documents.data?.map((doc) => (
                <div key={doc.id} className="flex items-center gap-3 rounded-2xl border border-[#755640]/9 bg-white/60 p-4">
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#efd3c7] text-[#a8523e]">
                    <FileText size={19} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-semibold">{doc.display_name}</div>
                    <div className="mt-1 text-xs text-[#8a7b70]">
                      {doc.active_version_id ? "Ready for RAG" : "Waiting for active version"}
                    </div>
                  </div>
                  <span
                    className={
                      "rounded-full px-3 py-1 text-xs font-medium " +
                      (doc.active_version_id
                        ? "bg-[#dce6d8] text-[#56704f]"
                        : "bg-[#f5e3c3] text-[#8b662e]")
                    }
                  >
                    {doc.active_version_id ? "Ready" : "Processing"}
                  </span>
                </div>
              ))}
              {!documents.isLoading && !documents.data?.length && (
                <div className="rounded-2xl border border-dashed border-[#8b6b53]/20 p-7 text-center text-sm text-[#8a7b70]">
                  Chưa có tài liệu.
                </div>
              )}
            </div>
          </div>

          <div className="paper-card rounded-[26px] p-5 md:p-6">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="font-display text-2xl font-semibold">Ingestion & Jobs</h2>
                <p className="mt-1 text-sm text-[#8a7b70]">Theo dõi extract → chunk → embedding → ready.</p>
              </div>
              <RefreshCcw size={18} className={jobs.isFetching ? "animate-spin text-[#b9634c]" : "text-[#8a7b70]"} />
            </div>

            <div className="space-y-3">
              {latestJobs.map((job) => {
                const total = job.progress_total || 4;
                const pct = Math.min(100, Math.round((job.progress_current / total) * 100));
                return (
                  <div key={job.id} className="rounded-2xl bg-white/58 p-4">
                    <div className="flex items-center gap-3">
                      <JobIcon status={job.status} />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="text-sm font-semibold">
                            {job.job_type === "ingest" ? "Document ingestion" : "Document deletion"}
                          </div>
                          <div className="text-xs text-[#8a7b70]">
                            attempt {job.attempt_count}/{job.max_attempts}
                          </div>
                        </div>
                        <div className="mt-1 text-xs capitalize text-[#8a7b70]">
                          {job.status} · {job.stage || "waiting"}
                        </div>
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#eadfd5]">
                          <div
                            className={
                              "h-full rounded-full transition-all " +
                              (job.status === "failed" ? "bg-red-400" : "bg-[#8b7ab8]")
                            }
                            style={{ width: `${job.status === "succeeded" ? 100 : pct}%` }}
                          />
                        </div>
                        {job.last_error && (
                          <div className="mt-2 line-clamp-2 text-xs text-red-700">{job.last_error}</div>
                        )}
                      </div>
                      {job.status === "failed" && job.job_type === "ingest" && (
                        <button
                          onClick={() => retry.mutate(job.id)}
                          className="rounded-xl border border-[#b9634c]/20 px-3 py-2 text-xs font-semibold text-[#9b4d3b]"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
              {!jobs.isLoading && !latestJobs.length && (
                <div className="rounded-2xl bg-white/45 p-5 text-sm text-[#8a7b70]">
                  Chưa có processing job.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="paper-card flex min-h-[760px] flex-col rounded-[26px] p-5 md:p-6">
          <div className="flex items-center justify-between gap-3 border-b border-[#755640]/10 pb-4">
            <div>
              <h2 className="font-display text-2xl font-semibold">Study Chat</h2>
              <p className="mt-1 text-xs text-[#8a7b70]">Grounded in this project’s active documents.</p>
            </div>
            <button
              onClick={() => createSession.mutate()}
              disabled={createSession.isPending}
              className="rounded-xl bg-[#b9634c] px-4 py-2 text-sm font-semibold text-white"
            >
              New chat
            </button>
          </div>

          <div className="mt-4 flex gap-2 overflow-x-auto pb-2">
            {sessions.data?.map((session) => (
              <button
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                className={
                  "max-w-48 shrink-0 truncate rounded-full px-3 py-1.5 text-xs " +
                  (effectiveSessionId === session.id
                    ? "bg-[#efd3c7] text-[#8f4738]"
                    : "bg-white/65 text-[#7d7167]")
                }
              >
                {session.title}
              </button>
            ))}
          </div>

          <div className="soft-scrollbar mt-4 flex-1 space-y-4 overflow-y-auto pr-1">
            {messages.data?.map((item) => (
              <div key={item.id} className={item.role === "user" ? "ml-auto max-w-[85%]" : "mr-auto max-w-[94%]"}>
                <div
                  className={
                    "rounded-2xl px-4 py-3 text-sm leading-6 " +
                    (item.role === "user"
                      ? "bg-[#f0d7cb] text-[#4d382e]"
                      : "border border-[#755640]/10 bg-white/72")
                  }
                >
                  {item.content}
                </div>
                {item.role === "assistant" && item.citations && item.citations.length > 0 && (
                  <div className="mt-2 space-y-2">
                    {item.citations.map((source, index) => (
                      <div key={index} className="rounded-xl border border-[#755640]/10 bg-[#fff9f2] p-3 text-xs">
                        <div className="flex items-start gap-2">
                          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#dce6d8] font-semibold text-[#597154]">
                            {index + 1}
                          </span>
                          <div>
                            <div className="font-semibold">{source.source_file || "Document"}</div>
                            <div className="mt-1 text-[#8a7b70]">
                              {source.page ? `Page ${source.page}` : "Page unknown"}
                              {typeof source.similarity === "number"
                                ? ` · similarity ${source.similarity.toFixed(3)}`
                                : ""}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {!effectiveSessionId && (
              <div className="grid h-full place-items-center py-16 text-center">
                <div>
                  <MessageSquare className="mx-auto text-[#b9634c]" size={34} />
                  <div className="font-display mt-3 text-xl font-semibold">Start a study chat</div>
                  <div className="mt-1 max-w-sm text-sm leading-6 text-[#8a7b70]">
                    Sau khi document ingest xong, hãy hỏi câu có nội dung nằm trong tài liệu để kiểm tra retrieval và citation.
                  </div>
                </div>
              </div>
            )}

            {send.isPending && (
              <div className="flex items-center gap-2 text-sm text-[#8a7b70]">
                <Loader2 size={16} className="animate-spin" />
                RAG đang retrieve context và gọi Gemini...
              </div>
            )}
          </div>

          <form onSubmit={submitMessage} className="mt-4 border-t border-[#755640]/10 pt-4">
            {send.isError && (
              <div className="mb-3 rounded-xl bg-red-50 p-3 text-xs text-red-700">
                Gửi câu hỏi thất bại. Kiểm tra chunks, match_chunks RPC và Gemini backend log.
              </div>
            )}
            <div className="flex items-end gap-2 rounded-2xl border border-[#755640]/14 bg-white/75 p-2">
              <button type="button" className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-[#8a7b70]">
                <Paperclip size={18} />
              </button>
              <textarea
                rows={2}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Ask a question about your documents..."
                className="min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-[#a29387]"
              />
              <button
                type="submit"
                disabled={send.isPending || !message.trim()}
                className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#b9634c] text-white disabled:opacity-50"
              >
                <Send size={17} />
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}

function JobIcon({ status }: { status: string }) {
  if (status === "succeeded") {
    return (
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#dce6d8] text-[#587152]">
        <CheckCircle2 size={19} />
      </div>
    );
  }
  if (status === "failed") {
    return (
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-red-100 text-red-700">
        <AlertCircle size={19} />
      </div>
    );
  }
  return (
    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#e8e1f2] text-[#77659d]">
      <Loader2 size={19} className="animate-spin" />
    </div>
  );
}

"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  CheckCircle2,
  FileText,
  MessageSquare,
  RotateCcw,
  Trophy,
} from "lucide-react";
import {
  getProgressHistory,
  getProgressOverview,
  rebuildProgress,
} from "@/lib/ragtutor";

export default function ProgressPage() {
  const queryClient = useQueryClient();

  const progress = useQuery({
    queryKey: ["progress-overview"],
    queryFn: getProgressOverview,
    refetchInterval: 15000,
  });

  const history = useQuery({
    queryKey: ["progress-history", 30],
    queryFn: () => getProgressHistory(30),
  });

  const rebuild = useMutation({
    mutationFn: (projectId: string) => rebuildProgress(projectId, 30),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["progress-history"] }),
        queryClient.invalidateQueries({ queryKey: ["progress-overview"] }),
      ]);
    },
  });

  const data = progress.data;

  const daily = new Map<
    string,
    { studyMinutes: number; attempts: number; correct: number }
  >();
  for (const row of history.data ?? []) {
    const current = daily.get(row.snapshot_date) ?? {
      studyMinutes: 0,
      attempts: 0,
      correct: 0,
    };
    current.studyMinutes += row.study_minutes;
    current.attempts += row.questions_attempted;
    current.correct += row.questions_correct;
    daily.set(row.snapshot_date, current);
  }

  const chartRows = Array.from(daily.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14);

  const maxActivity = Math.max(
    1,
    ...chartRows.map(([, row]) => row.studyMinutes + row.attempts * 10),
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section>
        <div className="font-hand text-2xl text-[#b9634c]">See what is changing</div>
        <h1 className="font-display text-4xl font-semibold">Progress</h1>
        <p className="mt-2 text-[#7d7167]">
          Số liệu lấy trực tiếp từ documents, chat, quiz và review state hiện tại.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Metric icon={<FileText size={20} />} label="Documents" value={data ? String(data.documents) : "…"} note={data ? data.ready_documents + " ready" : ""} />
        <Metric icon={<MessageSquare size={20} />} label="Chat messages" value={data ? String(data.chat_messages) : "…"} note={data ? data.chat_sessions + " sessions" : ""} />
        <Metric icon={<BookOpen size={20} />} label="Quiz attempts" value={data ? String(data.quiz_attempts) : "…"} note={data ? data.quiz_sessions + " sessions" : ""} />
        <Metric icon={<Trophy size={20} />} label="Average score" value={data ? data.avg_quiz_score + "%" : "…"} note={data ? data.quiz_correct + " correct" : ""} />
        <Metric icon={<RotateCcw size={20} />} label="Reviews due" value={data ? String(data.reviews_due) : "…"} note="spaced review" />
      </section>

      {progress.isError && (
        <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-700">
          Không tải được progress. Kiểm tra backend endpoint /progress/overview.
        </div>
      )}

      <section className="paper-card rounded-[26px] p-5 md:p-6">
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl font-semibold">
              14-day study activity
            </h2>
            <p className="mt-1 text-sm text-[#8a7b70]">
              Snapshot theo timezone tài khoản; chiều cao kết hợp study minutes và quiz attempts.
            </p>
          </div>
          <div className="text-xs text-[#8a7b70]">last 30 days loaded</div>
        </div>

        {history.isLoading ? (
          <div className="h-44 animate-pulse rounded-2xl bg-white/45" />
        ) : chartRows.length > 0 ? (
          <div className="flex h-52 items-end gap-2 overflow-x-auto rounded-2xl bg-white/45 p-4">
            {chartRows.map(([date, row]) => {
              const activity = row.studyMinutes + row.attempts * 10;
              const height = Math.max(5, Math.round((activity / maxActivity) * 100));
              return (
                <div
                  key={date}
                  className="flex min-w-10 flex-1 flex-col items-center justify-end gap-2"
                  title={
                    date +
                    " · " +
                    row.studyMinutes +
                    " study min · " +
                    row.attempts +
                    " attempts"
                  }
                >
                  <div
                    className="w-full max-w-10 rounded-t-xl bg-[#b9634c]/75"
                    style={{ height: height + "%" }}
                  />
                  <div className="text-[10px] text-[#8a7b70]">
                    {date.slice(5)}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-[#8b6b53]/20 p-7 text-center text-sm text-[#8a7b70]">
            Chưa có snapshot. Hoàn thành lịch học hoặc làm quiz để tạo dữ liệu.
          </div>
        )}
      </section>

      <section className="paper-card rounded-[26px] p-5 md:p-6">
        <div className="mb-5">
          <h2 className="font-display text-2xl font-semibold">By project</h2>
          <p className="mt-1 text-sm text-[#8a7b70]">
            So sánh lượng tài liệu, chat và quiz của từng knowledge base.
          </p>
        </div>

        <div className="space-y-3">
          {data?.project_breakdown.map((project) => {
            const accuracy =
              project.quiz_attempts > 0
                ? Math.round((project.quiz_correct / project.quiz_attempts) * 100)
                : 0;

            return (
              <div
                key={project.project_id}
                className="rounded-2xl border border-[#755640]/10 bg-white/58 p-4 transition hover:bg-white/80"
              >
                <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                  <div>
                    <Link
                      href={"/projects/" + project.project_id}
                      className="font-display text-xl font-semibold hover:text-[#9b4d3b]"
                    >
                      {project.name}
                    </Link>
                    <div className="mt-1 text-xs text-[#8a7b70]">
                      {project.ready_documents}/{project.documents} documents ready
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-5 text-center text-sm">
                    <div>
                      <div className="font-semibold">{project.chat_sessions}</div>
                      <div className="mt-1 text-xs text-[#8a7b70]">Chats</div>
                    </div>
                    <div>
                      <div className="font-semibold">{project.quiz_attempts}</div>
                      <div className="mt-1 text-xs text-[#8a7b70]">Attempts</div>
                    </div>
                    <div>
                      <div className="font-semibold">{accuracy}%</div>
                      <div className="mt-1 text-xs text-[#8a7b70]">Accuracy</div>
                    </div>
                  </div>
                  <button
                    onClick={() => rebuild.mutate(project.project_id)}
                    disabled={rebuild.isPending}
                    className="rounded-xl border border-[#b9634c]/20 bg-[#fff8f3] px-3 py-2 text-xs font-semibold text-[#9b4d3b] disabled:opacity-50"
                  >
                    {rebuild.isPending ? "Rebuilding..." : "Rebuild 30d"}
                  </button>
                </div>

                <div className="mt-4 h-2 overflow-hidden rounded-full bg-[#eadfd5]">
                  <div
                    className="h-full rounded-full bg-[#8b9d83]"
                    style={{ width: accuracy + "%" }}
                  />
                </div>
              </div>
            );
          })}

          {!progress.isLoading && !data?.project_breakdown.length && (
            <div className="rounded-2xl border border-dashed border-[#8b6b53]/20 p-8 text-center">
              <CheckCircle2 className="mx-auto text-[#8b9d83]" />
              <div className="font-display mt-3 text-xl font-semibold">Chưa có dữ liệu học tập</div>
              <p className="mt-2 text-sm text-[#8a7b70]">
                Tạo project, upload tài liệu và làm quiz để bắt đầu có progress.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
  note,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="paper-card rounded-[22px] p-5">
      <div className="mb-4 grid h-11 w-11 place-items-center rounded-xl bg-[#f3ddd4] text-[#9c513e]">
        {icon}
      </div>
      <div className="text-xs uppercase tracking-wide text-[#8a7b70]">{label}</div>
      <div className="font-display mt-1 text-3xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-[#8a7b70]">{note}</div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  CheckCircle2,
  FileText,
  MessageSquare,
  RotateCcw,
  Trophy,
} from "lucide-react";
import { getProgressOverview } from "@/lib/ragtutor";

export default function ProgressPage() {
  const progress = useQuery({
    queryKey: ["progress-overview"],
    queryFn: getProgressOverview,
    refetchInterval: 15000,
  });

  const data = progress.data;

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
              <Link
                href={"/projects/" + project.project_id}
                key={project.project_id}
                className="block rounded-2xl border border-[#755640]/10 bg-white/58 p-4 transition hover:bg-white/80"
              >
                <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
                  <div>
                    <div className="font-display text-xl font-semibold">{project.name}</div>
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
                </div>

                <div className="mt-4 h-2 overflow-hidden rounded-full bg-[#eadfd5]">
                  <div
                    className="h-full rounded-full bg-[#8b9d83]"
                    style={{ width: accuracy + "%" }}
                  />
                </div>
              </Link>
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

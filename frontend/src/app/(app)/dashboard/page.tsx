"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  FileText,
  FolderKanban,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { listProjects, listDocuments, listChatSessions } from "@/lib/ragtutor";

export default function DashboardPage() {
  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const firstProjectId = projects.data?.[0]?.id;

  const documents = useQuery({
    queryKey: ["documents", firstProjectId],
    queryFn: () => listDocuments(firstProjectId!),
    enabled: Boolean(firstProjectId),
  });

  const sessions = useQuery({
    queryKey: ["chat-sessions", firstProjectId],
    queryFn: () => listChatSessions(firstProjectId!),
    enabled: Boolean(firstProjectId),
  });

  const loading = projects.isLoading;

  return (
    <div className="mx-auto max-w-[1500px] space-y-6">
      <section className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
        <div>
          <div className="font-hand text-2xl text-[#b9634c]">Welcome back</div>
          <h1 className="font-display mt-1 text-4xl font-semibold md:text-5xl">
            Keep learning, keep building.
          </h1>
          <p className="mt-2 text-[#7d7167]">
            Đây là không gian học tập được xây từ chính tài liệu của bạn.
          </p>
        </div>
        <div className="rotate-[-1deg] rounded-2xl bg-[#f1dfb8] px-6 py-4 shadow-sm">
          <div className="font-hand text-2xl text-[#54473d]">
            “Better questions lead to deeper understanding.”
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<FolderKanban size={22} />}
          label="Active Projects"
          value={loading ? "…" : String(projects.data?.length ?? 0)}
          tone="terracotta"
        />
        <StatCard
          icon={<FileText size={22} />}
          label="Documents"
          value={documents.isLoading ? "…" : String(documents.data?.length ?? 0)}
          tone="gold"
        />
        <StatCard
          icon={<MessageSquare size={22} />}
          label="Chat Sessions"
          value={sessions.isLoading ? "…" : String(sessions.data?.length ?? 0)}
          tone="sage"
        />
        <StatCard
          icon={<Sparkles size={22} />}
          label="RAG Status"
          value={firstProjectId ? "Ready" : "No project"}
          tone="cream"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_.65fr]">
        <div className="paper-card rounded-[26px] p-5 md:p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="font-display text-2xl font-semibold">My Projects</h2>
              <p className="mt-1 text-sm text-[#8a7b70]">
                Mỗi project là một knowledge base riêng.
              </p>
            </div>
            <Link href="/projects" className="flex items-center gap-1 text-sm font-semibold text-[#a8523e]">
              View all <ArrowRight size={16} />
            </Link>
          </div>

          {projects.isError && (
            <ErrorState text="Không tải được projects. Kiểm tra backend và phiên đăng nhập." />
          )}

          {!projects.isLoading && projects.data?.length === 0 && (
            <div className="rounded-2xl border border-dashed border-[#9d745b]/25 bg-white/45 p-8 text-center">
              <p className="font-display text-xl">Chưa có project nào</p>
              <Link
                href="/projects"
                className="mt-4 inline-flex rounded-xl bg-[#b9634c] px-4 py-2 text-sm font-semibold text-white"
              >
                Tạo project đầu tiên
              </Link>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {projects.data?.slice(0, 4).map((project, index) => (
              <Link
                href={`/projects/${project.id}`}
                key={project.id}
                className="group rounded-2xl border border-[#725643]/10 bg-white/60 p-4 transition hover:-translate-y-0.5 hover:bg-white/85 hover:shadow-md"
              >
                <div
                  className={
                    "mb-4 h-24 rounded-xl " +
                    (index % 3 === 0
                      ? "bg-gradient-to-br from-[#ead7c8] to-[#d9aa8d]"
                      : index % 3 === 1
                        ? "bg-gradient-to-br from-[#dce6d8] to-[#aabca4]"
                        : "bg-gradient-to-br from-[#eee0c6] to-[#d1b382]")
                  }
                />
                <div className="font-display text-xl font-semibold">{project.name}</div>
                <p className="mt-1 line-clamp-2 text-sm leading-6 text-[#7d7167]">
                  {project.description || "Knowledge base cho tài liệu học tập của bạn."}
                </p>
                <div className="mt-4 flex items-center justify-between text-xs text-[#8c7b70]">
                  <span>{project.status}</span>
                  <ArrowRight size={16} className="transition group-hover:translate-x-1" />
                </div>
              </Link>
            ))}
          </div>
        </div>

        <div className="paper-card rounded-[26px] p-5 md:p-6">
          <h2 className="font-display text-2xl font-semibold">Recent Documents</h2>
          <p className="mt-1 text-sm text-[#8a7b70]">
            Tài liệu trong project gần nhất.
          </p>
          <div className="mt-5 space-y-3">
            {documents.data?.slice(0, 6).map((doc) => (
              <div key={doc.id} className="flex items-center gap-3 rounded-xl bg-white/55 p-3">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#efd3c7] text-[#a8523e]">
                  <FileText size={18} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold">{doc.display_name}</div>
                  <div className="mt-1 text-xs text-[#8a7b70]">
                    {doc.active_version_id ? "Ready for retrieval" : "Processing"}
                  </div>
                </div>
              </div>
            ))}
            {!documents.isLoading && !documents.data?.length && (
              <div className="rounded-xl bg-white/45 p-5 text-sm text-[#8a7b70]">
                Chưa có tài liệu trong project.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: "terracotta" | "gold" | "sage" | "cream";
}) {
  const tones = {
    terracotta: "bg-[#f3ddd4] text-[#a8523e]",
    gold: "bg-[#f5e3c3] text-[#a46b24]",
    sage: "bg-[#dce6d8] text-[#62765d]",
    cream: "bg-[#eee7d9] text-[#756552]",
  };
  return (
    <div className="paper-card rounded-[22px] p-5">
      <div className={`mb-4 grid h-12 w-12 place-items-center rounded-2xl ${tones[tone]}`}>
        {icon}
      </div>
      <div className="text-sm text-[#7d7167]">{label}</div>
      <div className="font-display mt-1 text-3xl font-semibold">{value}</div>
    </div>
  );
}

function ErrorState({ text }: { text: string }) {
  return <div className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{text}</div>;
}

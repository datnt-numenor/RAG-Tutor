"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, MessageSquare } from "lucide-react";
import { listChatSessions, listProjects } from "@/lib/ragtutor";

export default function ChatIndexPage() {
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-7">
        <div className="font-hand text-2xl text-[#b9634c]">Ask from your own materials</div>
        <h1 className="font-display text-4xl font-semibold">Study Chat</h1>
        <p className="mt-2 text-[#7d7167]">
          Chọn project để chat. Mỗi session chỉ retrieve active chunks của project đó.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {projects.data?.map((project) => (
          <ProjectChatCard key={project.id} projectId={project.id} name={project.name} />
        ))}
      </div>
    </div>
  );
}

function ProjectChatCard({ projectId, name }: { projectId: string; name: string }) {
  const sessions = useQuery({
    queryKey: ["chat-sessions", projectId],
    queryFn: () => listChatSessions(projectId),
  });

  return (
    <Link
      href={`/projects/${projectId}`}
      className="paper-card group rounded-[24px] p-5 transition hover:-translate-y-0.5 hover:shadow-lg"
    >
      <div className="flex items-start gap-4">
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[#dce6d8] text-[#61785a]">
          <MessageSquare size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-2xl font-semibold">{name}</h2>
          <p className="mt-1 text-sm text-[#8a7b70]">
            {sessions.data?.length ?? 0} chat sessions
          </p>
        </div>
        <ArrowRight className="mt-2 transition group-hover:translate-x-1" size={18} />
      </div>
    </Link>
  );
}

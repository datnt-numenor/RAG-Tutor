"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FileText, FolderKanban } from "lucide-react";
import { listDocuments, listProjects } from "@/lib/ragtutor";

export default function DocumentsPage() {
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-7">
        <div className="font-hand text-2xl text-[#b9634c]">Your study library</div>
        <h1 className="font-display text-4xl font-semibold">Documents</h1>
        <p className="mt-2 text-[#7d7167]">
          Documents được quản lý theo project để retrieval không lẫn knowledge base.
        </p>
      </div>

      <div className="space-y-5">
        {projects.data?.map((project) => (
          <ProjectDocuments key={project.id} projectId={project.id} projectName={project.name} />
        ))}
      </div>
    </div>
  );
}

function ProjectDocuments({ projectId, projectName }: { projectId: string; projectName: string }) {
  const docs = useQuery({
    queryKey: ["documents", projectId],
    queryFn: () => listDocuments(projectId),
  });

  return (
    <section className="paper-card rounded-[24px] p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#f3ddd4] text-[#a8523e]">
            <FolderKanban size={18} />
          </div>
          <div>
            <h2 className="font-display text-xl font-semibold">{projectName}</h2>
            <p className="text-xs text-[#8a7b70]">{docs.data?.length ?? 0} documents</p>
          </div>
        </div>
        <Link href={`/projects/${projectId}`} className="text-sm font-semibold text-[#9b4d3b]">
          Open workspace
        </Link>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {docs.data?.map((doc) => (
          <div key={doc.id} className="flex items-center gap-3 rounded-2xl bg-white/58 p-4">
            <FileText size={18} className="shrink-0 text-[#b9634c]" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">{doc.display_name}</div>
              <div className="mt-1 text-xs text-[#8a7b70]">
                {doc.active_version_id ? "Ready" : "Processing"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

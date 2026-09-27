"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Plus } from "lucide-react";
import { createProject, listProjects } from "@/lib/ragtutor";

export default function ProjectsPage() {
  const queryClient = useQueryClient();
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const create = useMutation({
    mutationFn: createProject,
    onSuccess: async () => {
      setName("");
      setDescription("");
      setOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate({ name: name.trim(), description: description.trim() || null });
  }

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="font-hand text-2xl text-[#b9634c]">Organize your learning</div>
          <h1 className="font-display text-4xl font-semibold">Projects</h1>
          <p className="mt-2 text-[#7d7167]">Tách tài liệu theo môn học, đề tài hoặc mục tiêu học tập.</p>
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#b9634c] px-5 py-3 font-semibold text-white"
        >
          <Plus size={18} /> New project
        </button>
      </div>

      {open && (
        <form onSubmit={submit} className="paper-card mb-6 rounded-[24px] p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Tên project"
              maxLength={200}
              className="rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none focus:border-[#b9634c]/40"
            />
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Mô tả ngắn"
              className="rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none focus:border-[#b9634c]/40"
            />
          </div>
          {create.isError && (
            <p className="mt-3 text-sm text-red-700">Tạo project thất bại. Kiểm tra backend hoặc token.</p>
          )}
          <button
            disabled={create.isPending}
            className="mt-4 rounded-xl bg-[#8f4738] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
          >
            {create.isPending ? "Đang tạo..." : "Create project"}
          </button>
        </form>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {projects.data?.map((project, index) => (
          <Link
            key={project.id}
            href={`/projects/${project.id}`}
            className="paper-card group rounded-[24px] p-5 transition hover:-translate-y-1 hover:shadow-lg"
          >
            <div
              className={
                "mb-5 h-32 rounded-2xl " +
                (index % 3 === 0
                  ? "bg-gradient-to-br from-[#e7cfc0] via-[#eeddd0] to-[#b97c5d]"
                  : index % 3 === 1
                    ? "bg-gradient-to-br from-[#e3eadf] via-[#d4e0cf] to-[#8ea186]"
                    : "bg-gradient-to-br from-[#f4e8cf] via-[#ead8b6] to-[#bf9454]")
              }
            />
            <h2 className="font-display text-2xl font-semibold">{project.name}</h2>
            <p className="mt-2 min-h-12 text-sm leading-6 text-[#7d7167]">
              {project.description || "Không có mô tả."}
            </p>
            <div className="mt-5 flex items-center justify-between border-t border-[#705541]/10 pt-4 text-sm text-[#8a5a48]">
              <span>{project.status}</span>
              <ArrowRight size={17} className="transition group-hover:translate-x-1" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

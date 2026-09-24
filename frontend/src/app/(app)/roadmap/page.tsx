"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Map, Target } from "lucide-react";
import { listProjects } from "@/lib/ragtutor";

export default function RoadmapIndexPage() {
  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-7">
        <div className="font-hand text-2xl text-[#b9634c]">Learn in the right order</div>
        <h1 className="font-display text-4xl font-semibold">Roadmap</h1>
        <p className="mt-2 text-[#7d7167]">
          Topic graph, prerequisite và lịch học được tách riêng cho từng project.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {projects.data?.map((project) => (
          <Link
            key={project.id}
            href={"/projects/" + project.id + "/roadmap"}
            className="paper-card group rounded-[24px] p-5 transition hover:-translate-y-0.5 hover:shadow-lg"
          >
            <div className="flex items-start gap-4">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[#f3ddd4] text-[#9c513e]">
                <Map size={21} />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="font-display text-2xl font-semibold">{project.name}</h2>
                <div className="mt-3 space-y-1 text-sm text-[#7d7167]">
                  <div className="flex items-center gap-2">
                    <Target size={15} />
                    Target: {project.target_score ?? "chưa đặt"}
                  </div>
                  <div>
                    {project.exam_date ? "Exam: " + project.exam_date : "Chưa đặt ngày thi"}
                  </div>
                  <div>
                    {project.weekly_study_minutes
                      ? project.weekly_study_minutes + " phút/tuần"
                      : "Chưa đặt thời gian học/tuần"}
                  </div>
                </div>
              </div>
              <ArrowRight size={18} className="mt-2 transition group-hover:translate-x-1" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

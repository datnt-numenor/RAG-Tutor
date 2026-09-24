"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  Check,
  CheckCircle2,
  Clock3,
  Loader2,
  Map,
  RefreshCcw,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import {
  acceptSchedule,
  completeSchedule,
  generateRoadmap,
  generateSchedules,
  getProject,
  getRoadmap,
  listSchedules,
  rejectSchedule,
  uncompleteSchedule,
  updateProject,
} from "@/lib/ragtutor";

export function ProjectRoadmap({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const roadmap = useQuery({
    queryKey: ["roadmap", projectId],
    queryFn: () => getRoadmap(projectId),
  });

  const schedules = useQuery({
    queryKey: ["schedules", projectId],
    queryFn: () => listSchedules(projectId),
  });

  const [targetScore, setTargetScore] = useState("80");
  const [examDate, setExamDate] = useState("");
  const [weeklyMinutes, setWeeklyMinutes] = useState("300");

  useEffect(() => {
    if (!project.data) return;
    setTargetScore(String(project.data.target_score ?? 80));
    setExamDate(project.data.exam_date ?? "");
    setWeeklyMinutes(String(project.data.weekly_study_minutes ?? 300));
  }, [project.data]);

  const saveGoals = useMutation({
    mutationFn: () =>
      updateProject(projectId, {
        name: project.data?.name ?? "Project",
        description: project.data?.description ?? null,
        target_score: Number(targetScore),
        exam_date: examDate || null,
        weekly_study_minutes: Number(weeklyMinutes),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project", projectId] }),
        queryClient.invalidateQueries({ queryKey: ["roadmap", projectId] }),
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
      ]);
    },
  });

  const generate = useMutation({
    mutationFn: () => generateRoadmap(projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["roadmap", projectId] });
    },
  });

  const generatePlan = useMutation({
    mutationFn: () => generateSchedules(projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["schedules", projectId] });
    },
  });

  const accept = useMutation({
    mutationFn: acceptSchedule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["schedules", projectId] });
    },
  });

  const reject = useMutation({
    mutationFn: rejectSchedule,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["schedules", projectId] });
    },
  });

  const complete = useMutation({
    mutationFn: ({
      id,
      completed,
    }: {
      id: string;
      completed: boolean;
    }) => (completed ? uncompleteSchedule(id) : completeSchedule(id)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["schedules", projectId] });
    },
  });

  const acceptedSchedules = useMemo(
    () =>
      (schedules.data ?? []).filter(
        (item) => item.suggestion_status !== "rejected",
      ),
    [schedules.data],
  );

  function submitGoals(event: FormEvent) {
    event.preventDefault();
    saveGoals.mutate();
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-6">
      <section>
        <div className="font-hand text-2xl text-[#b9634c]">Personalized study path</div>
        <h1 className="font-display text-4xl font-semibold">
          {project.data?.name ?? "Roadmap"}
        </h1>
        <p className="mt-2 text-[#7d7167]">
          Topic order dựa trên prerequisite; thời lượng lịch học thay đổi theo mục tiêu và thời gian còn lại.
        </p>
      </section>

      <section className="paper-card rounded-[26px] p-5 md:p-6">
        <form
          onSubmit={submitGoals}
          className="grid gap-4 md:grid-cols-[1fr_1fr_1fr_auto]"
        >
          <label className="text-sm">
            <span className="mb-2 flex items-center gap-2 font-medium text-[#66584f]">
              <Target size={16} />
              Target score
            </span>
            <input
              type="number"
              min={0}
              max={100}
              value={targetScore}
              onChange={(event) => setTargetScore(event.target.value)}
              className="w-full rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none"
            />
          </label>

          <label className="text-sm">
            <span className="mb-2 flex items-center gap-2 font-medium text-[#66584f]">
              <CalendarDays size={16} />
              Exam date
            </span>
            <input
              type="date"
              value={examDate}
              onChange={(event) => setExamDate(event.target.value)}
              className="w-full rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none"
            />
          </label>

          <label className="text-sm">
            <span className="mb-2 flex items-center gap-2 font-medium text-[#66584f]">
              <Clock3 size={16} />
              Minutes / week
            </span>
            <input
              type="number"
              min={30}
              value={weeklyMinutes}
              onChange={(event) => setWeeklyMinutes(event.target.value)}
              className="w-full rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none"
            />
          </label>

          <button
            disabled={saveGoals.isPending || !project.data}
            className="self-end rounded-2xl bg-[#8f4738] px-5 py-3 font-semibold text-white disabled:opacity-50"
          >
            {saveGoals.isPending ? "Đang lưu..." : "Lưu mục tiêu"}
          </button>
        </form>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_.9fr]">
        <div className="paper-card rounded-[26px] p-5 md:p-6">
          <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="font-display text-2xl font-semibold">Topic roadmap</h2>
              <p className="mt-1 text-sm text-[#8a7b70]">
                Gemini trích xuất topic + source + prerequisite từ active chunks.
              </p>
            </div>
            <button
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#b9634c] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {generate.isPending ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Đang phân tích...
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  Generate roadmap
                </>
              )}
            </button>
          </div>

          {generate.isError && (
            <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
              Không generate được roadmap. Project cần document đã ingest xong.
            </div>
          )}

          <div className="space-y-3">
            {roadmap.data?.topics.map((topic) => (
              <div
                key={topic.id}
                className="rounded-2xl border border-[#755640]/10 bg-white/58 p-4"
              >
                <div className="flex gap-4">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#f3ddd4] font-display text-lg font-semibold text-[#9c513e]">
                    {topic.order}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-display text-xl font-semibold">{topic.name}</h3>
                      {topic.is_core && (
                        <span className="rounded-full bg-[#dce6d8] px-2.5 py-1 text-[11px] font-semibold text-[#587052]">
                          Core
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm leading-6 text-[#74665c]">
                      {topic.description || "Không có mô tả."}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      <span className="rounded-full bg-[#f5e3c3] px-2.5 py-1 text-[#876225]">
                        {topic.difficulty || "n/a"}
                      </span>
                      <span className="rounded-full bg-[#e6e0f0] px-2.5 py-1 text-[#695b8b]">
                        Bloom: {topic.bloom_level || "n/a"}
                      </span>
                    </div>
                    {topic.prerequisites.length > 0 && (
                      <div className="mt-3 text-xs text-[#8a7b70]">
                        Prerequisite: {topic.prerequisites.join(" → ")}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {!roadmap.isLoading && !roadmap.data?.topics.length && (
              <div className="rounded-2xl border border-dashed border-[#8b6b53]/20 p-8 text-center">
                <Map className="mx-auto text-[#b9634c]" size={28} />
                <div className="font-display mt-3 text-xl font-semibold">Chưa có topic roadmap</div>
                <p className="mt-2 text-sm text-[#8a7b70]">
                  Generate sau khi ít nhất một document đã ở trạng thái Ready.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="paper-card rounded-[26px] p-5 md:p-6">
          <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="font-display text-2xl font-semibold">Study schedule</h2>
              <p className="mt-1 text-sm text-[#8a7b70]">
                Lịch gợi ý theo timezone của tài khoản.
              </p>
            </div>
            <button
              onClick={() => generatePlan.mutate()}
              disabled={generatePlan.isPending || !roadmap.data?.topics.length}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-[#b9634c]/20 bg-[#fff8f3] px-4 py-2.5 text-sm font-semibold text-[#9b4d3b] disabled:opacity-50"
            >
              <RefreshCcw
                size={16}
                className={generatePlan.isPending ? "animate-spin" : ""}
              />
              Generate schedule
            </button>
          </div>

          {generatePlan.isError && (
            <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
              Không sinh được lịch. Hãy generate topic roadmap trước.
            </div>
          )}

          <div className="space-y-3">
            {acceptedSchedules.map((item) => (
              <div
                key={item.id}
                className={
                  "rounded-2xl border p-4 " +
                  (item.completed_by_me
                    ? "border-[#8b9d83]/20 bg-[#eef3eb]"
                    : "border-[#755640]/10 bg-white/58")
                }
              >
                <div className="flex gap-3">
                  <button
                    onClick={() =>
                      complete.mutate({
                        id: item.id,
                        completed: Boolean(item.completed_by_me),
                      })
                    }
                    className={
                      "mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full border " +
                      (item.completed_by_me
                        ? "border-[#71866a] bg-[#8b9d83] text-white"
                        : "border-[#8b9d83]/35 bg-white text-[#71866a]")
                    }
                    title={item.completed_by_me ? "Mark incomplete" : "Mark complete"}
                  >
                    {item.completed_by_me ? <Check size={15} /> : null}
                  </button>

                  <div className="min-w-0 flex-1">
                    <div className="font-semibold">{item.title}</div>
                    <div className="mt-1 text-xs text-[#8a7b70]">
                      {new Date(item.start_time).toLocaleString()}
                      {item.end_time
                        ? " → " +
                          new Date(item.end_time).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : ""}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                      <span className="rounded-full bg-[#f5e3c3] px-2 py-1 text-[#876225]">
                        {item.event_type}
                      </span>
                      <span className="rounded-full bg-[#eee7dc] px-2 py-1 text-[#75675c]">
                        {item.suggestion_status}
                      </span>
                    </div>
                  </div>

                  {item.suggestion_status === "suggested" && (
                    <div className="flex shrink-0 gap-1">
                      <button
                        onClick={() => accept.mutate(item.id)}
                        className="grid h-8 w-8 place-items-center rounded-lg bg-[#dce6d8] text-[#587052]"
                        title="Accept"
                      >
                        <CheckCircle2 size={15} />
                      </button>
                      <button
                        onClick={() => reject.mutate(item.id)}
                        className="grid h-8 w-8 place-items-center rounded-lg bg-red-50 text-red-600"
                        title="Reject"
                      >
                        <X size={15} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {!schedules.isLoading && acceptedSchedules.length === 0 && (
              <div className="rounded-2xl border border-dashed border-[#8b6b53]/20 p-7 text-center text-sm text-[#8a7b70]">
                Chưa có lịch học.
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

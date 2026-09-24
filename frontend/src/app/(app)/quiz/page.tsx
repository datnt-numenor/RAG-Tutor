"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  CircleHelp,
  Loader2,
  Sparkles,
  XCircle,
} from "lucide-react";
import {
  answerQuizQuestion,
  generateQuiz,
  getQuizSession,
  listProjects,
  listQuizSessions,
  submitQuiz,
  type QuizAttempt,
  type QuizQuestion,
} from "@/lib/ragtutor";

export default function QuizPage() {
  const queryClient = useQueryClient();
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const [projectId, setProjectId] = useState("");
  const [type, setType] = useState<"mcq" | "essay">("mcq");
  const [count, setCount] = useState(5);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const selectedProjectId = projectId || projects.data?.[0]?.id || "";

  const sessions = useQuery({
    queryKey: ["quiz-sessions", selectedProjectId],
    queryFn: () => listQuizSessions(selectedProjectId),
    enabled: Boolean(selectedProjectId),
  });

  const effectiveSessionId =
    activeSessionId ??
    sessions.data?.find((session) => session.status === "in_progress")?.id ??
    null;

  const activeQuiz = useQuery({
    queryKey: ["quiz-session", selectedProjectId, effectiveSessionId],
    queryFn: () => getQuizSession(selectedProjectId, effectiveSessionId!),
    enabled: Boolean(selectedProjectId && effectiveSessionId),
  });

  const generate = useMutation({
    mutationFn: () =>
      generateQuiz(selectedProjectId, {
        count,
        question_type: type,
      }),
    onSuccess: async (data) => {
      setActiveSessionId(data.session.id);
      setAnswers({});
      await queryClient.invalidateQueries({
        queryKey: ["quiz-sessions", selectedProjectId],
      });
    },
  });

  const answer = useMutation({
    mutationFn: async ({
      questionId,
      value,
    }: {
      questionId: string;
      value: string;
    }) =>
      answerQuizQuestion(
        selectedProjectId,
        effectiveSessionId!,
        questionId,
        value,
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["quiz-session", selectedProjectId, effectiveSessionId],
      });
    },
  });

  const submit = useMutation({
    mutationFn: () => submitQuiz(selectedProjectId, effectiveSessionId!),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["quiz-session", selectedProjectId, effectiveSessionId],
        }),
        queryClient.invalidateQueries({
          queryKey: ["quiz-sessions", selectedProjectId],
        }),
      ]);
    },
  });

  const attemptsByQuestion = useMemo(() => {
    const map = new Map<string, QuizAttempt>();
    for (const attempt of activeQuiz.data?.attempts ?? []) {
      if (attempt.question_id) map.set(attempt.question_id, attempt);
    }
    return map;
  }, [activeQuiz.data?.attempts]);

  const answeredCount = attemptsByQuestion.size;
  const totalQuestions = activeQuiz.data?.questions.length ?? 0;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <section>
        <div className="font-hand text-2xl text-[#b9634c]">Practice what you learned</div>
        <h1 className="font-display text-4xl font-semibold">Quiz</h1>
        <p className="mt-2 text-[#7d7167]">
          Câu hỏi được sinh từ active chunks của tài liệu trong project, không dùng knowledge ngoài.
        </p>
      </section>

      <section className="paper-card rounded-[26px] p-5 md:p-6">
        <div className="grid gap-4 md:grid-cols-[1fr_auto_auto_auto] md:items-end">
          <label className="text-sm">
            <span className="mb-2 block font-medium text-[#66584f]">Project</span>
            <select
              value={selectedProjectId}
              onChange={(e) => {
                setProjectId(e.target.value);
                setActiveSessionId(null);
              }}
              className="w-full rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none"
            >
              {projects.data?.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm">
            <span className="mb-2 block font-medium text-[#66584f]">Loại câu hỏi</span>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as "mcq" | "essay")}
              className="rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none"
            >
              <option value="mcq">Trắc nghiệm</option>
              <option value="essay">Tự luận</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="mb-2 block font-medium text-[#66584f]">Số câu</span>
            <input
              type="number"
              min={1}
              max={20}
              value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(20, Number(e.target.value))))}
              className="w-24 rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none"
            />
          </label>

          <button
            disabled={!selectedProjectId || generate.isPending}
            onClick={() => generate.mutate()}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#b9634c] px-5 py-3 font-semibold text-white disabled:opacity-50"
          >
            {generate.isPending ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Đang sinh...
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Generate quiz
              </>
            )}
          </button>
        </div>

        {generate.isError && (
          <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            Không sinh được quiz. Project cần ít nhất một document đã ingest xong.
          </div>
        )}
      </section>

      {effectiveSessionId && activeQuiz.data && (
        <section className="grid gap-6 xl:grid-cols-[1fr_290px]">
          <div className="space-y-4">
            {activeQuiz.data.questions.map((question, index) => (
              <QuestionCard
                key={question.id}
                index={index + 1}
                question={question}
                attempt={attemptsByQuestion.get(question.id)}
                value={answers[question.id] ?? ""}
                disabled={
                  answer.isPending ||
                  activeQuiz.data.session.status !== "in_progress"
                }
                onChange={(value) =>
                  setAnswers((current) => ({
                    ...current,
                    [question.id]: value,
                  }))
                }
                onSubmit={(value) =>
                  answer.mutate({
                    questionId: question.id,
                    value,
                  })
                }
              />
            ))}
          </div>

          <aside className="space-y-4">
            <div className="paper-card sticky top-28 rounded-[24px] p-5">
              <h2 className="font-display text-xl font-semibold">Quiz progress</h2>
              <div className="mt-4 text-4xl font-semibold">
                {answeredCount}/{totalQuestions}
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#eadfd5]">
                <div
                  className="h-full rounded-full bg-[#8b9d83]"
                  style={{
                    width:
                      totalQuestions > 0
                        ? \`\${Math.round((answeredCount / totalQuestions) * 100)}%\`
                        : "0%",
                  }}
                />
              </div>

              {activeQuiz.data.session.status === "graded" ? (
                <div className="mt-5 rounded-2xl bg-[#dce6d8] p-4 text-[#50664c]">
                  <div className="text-xs uppercase tracking-wide">Score</div>
                  <div className="font-display mt-1 text-3xl font-semibold">
                    {activeQuiz.data.session.total_score ?? 0}/
                    {activeQuiz.data.session.max_score ?? 0}
                  </div>
                </div>
              ) : (
                <button
                  disabled={
                    submit.isPending ||
                    answeredCount === 0 ||
                    activeQuiz.data.session.status !== "in_progress"
                  }
                  onClick={() => submit.mutate()}
                  className="mt-5 w-full rounded-2xl bg-[#8f4738] px-4 py-3 font-semibold text-white disabled:opacity-50"
                >
                  {submit.isPending ? "Đang nộp..." : "Nộp bài"}
                </button>
              )}

              <div className="mt-5 border-t border-[#755640]/10 pt-4">
                <div className="mb-2 text-xs font-medium uppercase tracking-wide text-[#8a7b70]">
                  Recent sessions
                </div>
                <div className="space-y-2">
                  {sessions.data?.slice(0, 5).map((session) => (
                    <button
                      key={session.id}
                      onClick={() => setActiveSessionId(session.id)}
                      className={
                        "w-full rounded-xl px-3 py-2 text-left text-xs transition " +
                        (effectiveSessionId === session.id
                          ? "bg-[#efd3c7] text-[#8f4738]"
                          : "bg-white/55 text-[#786a60]")
                      }
                    >
                      <div className="font-medium">{session.status}</div>
                      <div className="mt-1">
                        {session.total_score ?? "—"}/{session.max_score ?? "—"}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </aside>
        </section>
      )}

      {!effectiveSessionId && !generate.isPending && (
        <div className="paper-card rounded-[26px] p-10 text-center">
          <CircleHelp className="mx-auto text-[#b9634c]" size={38} />
          <h2 className="font-display mt-4 text-2xl font-semibold">Chưa có quiz đang mở</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#8a7b70]">
            Chọn project đã có tài liệu ở trạng thái Ready, sau đó generate quiz để kiểm tra retrieval → Gemini → grading → spaced review.
          </p>
        </div>
      )}
    </div>
  );
}

function QuestionCard({
  index,
  question,
  attempt,
  value,
  disabled,
  onChange,
  onSubmit,
}: {
  index: number;
  question: QuizQuestion;
  attempt?: QuizAttempt;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
}) {
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!value.trim() || attempt) return;
    onSubmit(value.trim());
  }

  return (
    <form onSubmit={submit} className="paper-card rounded-[24px] p-5 md:p-6">
      <div className="flex items-start gap-4">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#f3ddd4] font-semibold text-[#9f503d]">
          {index}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-xl font-semibold leading-8">
            {question.question_text}
          </h3>

          {question.question_type === "mcq" && question.options ? (
            <div className="mt-5 grid gap-2">
              {question.options.map((option) => (
                <label
                  key={option}
                  className={
                    "flex cursor-pointer items-center gap-3 rounded-2xl border p-3.5 text-sm transition " +
                    (value === option
                      ? "border-[#b9634c]/35 bg-[#f5e2d9]"
                      : "border-[#755640]/10 bg-white/55 hover:bg-white/80")
                  }
                >
                  <input
                    type="radio"
                    name={question.id}
                    value={option}
                    checked={value === option}
                    disabled={disabled || Boolean(attempt)}
                    onChange={() => onChange(option)}
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
          ) : (
            <textarea
              rows={5}
              value={value}
              disabled={disabled || Boolean(attempt)}
              onChange={(e) => onChange(e.target.value)}
              placeholder="Nhập câu trả lời..."
              className="mt-5 w-full resize-y rounded-2xl border border-[#755640]/12 bg-white/65 p-4 text-sm leading-6 outline-none focus:border-[#b9634c]/35"
            />
          )}

          {attempt ? (
            <div
              className={
                "mt-4 rounded-2xl p-4 text-sm " +
                (attempt.is_correct
                  ? "bg-[#dce6d8] text-[#50664c]"
                  : "bg-[#f6dddd] text-[#8d4545]")
              }
            >
              <div className="flex items-center gap-2 font-semibold">
                {attempt.is_correct ? (
                  <CheckCircle2 size={17} />
                ) : (
                  <XCircle size={17} />
                )}
                {attempt.is_correct ? "Đúng" : "Chưa đúng"} · {attempt.score ?? 0}/
                {question.max_score}
              </div>
              {attempt.feedback && (
                <p className="mt-2 leading-6">{attempt.feedback}</p>
              )}
            </div>
          ) : (
            <button
              disabled={disabled || !value.trim()}
              className="mt-4 rounded-xl bg-[#8f4738] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              Chấm câu này
            </button>
          )}
        </div>
      </div>
    </form>
  );
}

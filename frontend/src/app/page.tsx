export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      <div className="text-center space-y-6 px-4">
        <h1 className="text-5xl font-bold tracking-tight">
          📚 RAGTutor
        </h1>
        <p className="text-xl text-slate-300 max-w-lg mx-auto">
          AI Study Assistant — Upload tài liệu, chat hỏi đáp có trích dẫn,
          lộ trình học cá nhân và quiz tự chấm điểm.
        </p>
        <div className="flex gap-4 justify-center flex-wrap">
          <a
            href="/login"
            className="bg-purple-600 hover:bg-purple-500 transition-colors px-6 py-3 rounded-xl font-semibold"
          >
            Bắt đầu học →
          </a>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="border border-slate-500 hover:border-purple-400 transition-colors px-6 py-3 rounded-xl font-semibold"
          >
            API Docs
          </a>
        </div>
        <p className="text-sm text-slate-500 mt-8">
          Stack: Next.js 15 + FastAPI + Supabase + LangChain + Gemini
        </p>
      </div>
    </main>
  );
}

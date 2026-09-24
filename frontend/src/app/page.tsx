import Link from "next/link";
import { BookOpen, ArrowRight, Sparkles } from "lucide-react";

export default function Home() {
  return (
    <main className="paper-grid min-h-screen px-6 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center">
        <section className="paper-card relative w-full overflow-hidden rounded-[32px] p-8 md:p-14">
          <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-[#ead8bd]/50 blur-3xl" />
          <div className="absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-[#dce6d8]/60 blur-3xl" />

          <div className="relative grid gap-12 lg:grid-cols-[1.1fr_.9fr] lg:items-center">
            <div>
              <div className="mb-7 inline-flex items-center gap-3 rounded-full border border-[#b9634c]/20 bg-[#fffaf4] px-4 py-2 text-sm text-[#8f4738]">
                <Sparkles size={16} />
                AI Study Assistant dựa trên tài liệu của bạn
              </div>

              <div className="mb-7 flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[#b9634c] text-white shadow-lg shadow-[#b9634c]/20">
                  <BookOpen size={26} />
                </div>
                <div>
                  <div className="font-display text-3xl font-semibold">RAGTutor</div>
                  <div className="text-xs tracking-wide text-[#7d7167]">
                    Your knowledge, deeper understanding.
                  </div>
                </div>
              </div>

              <h1 className="font-display max-w-3xl text-5xl font-semibold leading-[1.08] md:text-7xl">
                Học sâu hơn từ chính
                <span className="text-[#b9634c]"> tài liệu của bạn.</span>
              </h1>

              <p className="mt-7 max-w-2xl text-lg leading-8 text-[#6f6258]">
                Upload PDF/DOCX, đặt câu hỏi, nhận câu trả lời có trích dẫn,
                theo dõi tiến trình xử lý và biến tài liệu thành một không gian
                học tập có tổ chức.
              </p>

              <div className="mt-9 flex flex-wrap gap-3">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-2xl bg-[#b9634c] px-6 py-3.5 font-semibold text-white shadow-lg shadow-[#b9634c]/20 transition hover:bg-[#a65440]"
                >
                  Bắt đầu học
                  <ArrowRight size={18} />
                </Link>
                <Link
                  href="/signup"
                  className="rounded-2xl border border-[#8f4738]/15 bg-white/70 px-6 py-3.5 font-semibold text-[#8f4738] transition hover:bg-white"
                >
                  Tạo tài khoản
                </Link>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-md">
              <div className="rotate-2 rounded-[28px] border border-[#a66d50]/15 bg-[#f4dfaa] p-8 shadow-xl shadow-[#7f5b3e]/10">
                <div className="font-hand text-4xl leading-tight text-[#4f4238]">
                  “Better questions lead to deeper understanding.”
                </div>
                <div className="mt-8 h-px bg-[#7f5b3e]/15" />
                <div className="mt-6 grid gap-4 text-sm text-[#66584e]">
                  <div>01 — Upload tài liệu học tập</div>
                  <div>02 — RAG truy xuất đoạn liên quan</div>
                  <div>03 — Gemini trả lời dựa trên nguồn</div>
                  <div>04 — Citation dẫn về đúng tài liệu và trang</div>
                </div>
              </div>
              <div className="absolute -bottom-8 -left-10 -z-10 h-32 w-32 rounded-full bg-[#dce6d8]" />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

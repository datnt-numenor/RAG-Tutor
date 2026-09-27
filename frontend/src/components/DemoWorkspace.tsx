"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  Brain,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  GraduationCap,
  Map,
  MessageSquare,
  PlayCircle,
  Send,
  Sparkles,
  Target,
  Upload,
} from "lucide-react";

type DemoView = "overview" | "documents" | "chat" | "quiz" | "roadmap";

const navigation: Array<{
  id: DemoView;
  label: string;
  icon: typeof BarChart3;
}> = [
  { id: "overview", label: "Tổng quan", icon: BarChart3 },
  { id: "documents", label: "Tài liệu", icon: FileText },
  { id: "chat", label: "Chat RAG", icon: MessageSquare },
  { id: "quiz", label: "Quiz", icon: Brain },
  { id: "roadmap", label: "Lộ trình", icon: Map },
];

const documents = [
  { name: "Nhập môn Machine Learning.pdf", pages: 42, chunks: 186, color: "#b9634c" },
  { name: "Deep Learning Notes.pdf", pages: 28, chunks: 114, color: "#8b9d83" },
  { name: "Bài giảng Xử lý ảnh.docx", pages: 19, chunks: 76, color: "#c88b3b" },
];

const roadmap = [
  { title: "Nền tảng Machine Learning", detail: "Supervised learning, loss function, train/test split", status: "done" },
  { title: "Mô hình phân loại", detail: "Logistic regression, decision tree và đánh giá mô hình", status: "active" },
  { title: "Neural Networks", detail: "Forward pass, backpropagation và optimization", status: "next" },
  { title: "Dự án thực hành", detail: "Xây dựng pipeline phân loại hoàn chỉnh", status: "next" },
];

export function DemoWorkspace() {
  const [view, setView] = useState<DemoView>("overview");

  return (
    <main className="paper-grid min-h-screen bg-[#f8f2e9] text-[#29231f]">
      <header className="sticky top-0 z-20 border-b border-[#6b4f3d]/10 bg-[#fffaf4]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link href="/" className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-[#b9634c] text-white shadow-lg shadow-[#b9634c]/20">
              <BookOpen size={21} />
            </span>
            <span>
              <span className="font-display block text-xl font-semibold leading-5">RAGTutor</span>
              <span className="text-[10px] uppercase tracking-[0.18em] text-[#8b7d72]">portfolio demo</span>
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-2 rounded-full bg-[#dce6d8] px-3 py-2 text-xs font-semibold text-[#53634d] sm:flex">
              <CheckCircle2 size={14} /> Dữ liệu mẫu cục bộ
            </span>
            <Link href="/" className="inline-flex items-center gap-2 rounded-xl border border-[#6b4f3d]/10 bg-white/70 px-3 py-2 text-sm font-medium text-[#675a50] transition hover:bg-white">
              <ArrowLeft size={16} /> <span className="hidden sm:inline">Trang chủ</span>
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-4 py-5 sm:px-6 lg:grid-cols-[220px_minmax(0,1fr)] lg:py-8">
        <aside className="paper-card h-fit rounded-[24px] p-3 lg:sticky lg:top-24">
          <div className="mb-3 rounded-2xl bg-[#f3df9e]/70 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-[#665137]">
              <Sparkles size={16} /> Chế độ trải nghiệm
            </div>
            <p className="mt-2 text-xs leading-5 text-[#76644f]">
              Mọi thao tác trên trang này đều được mô phỏng trong trình duyệt, không gọi AI trả phí.
            </p>
          </div>
          <nav className="grid grid-cols-2 gap-1 sm:grid-cols-5 lg:grid-cols-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = view === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setView(item.id)}
                  className={`flex items-center gap-2 rounded-2xl px-3 py-3 text-left text-sm font-medium transition ${active ? "bg-[#b9634c] text-white shadow-md shadow-[#b9634c]/15" : "text-[#544940] hover:bg-white/70"}`}
                >
                  <Icon size={18} /> {item.label}
                </button>
              );
            })}
          </nav>
        </aside>

        <section className="min-w-0">
          {view === "overview" && <Overview onNavigate={setView} />}
          {view === "documents" && <Documents />}
          {view === "chat" && <Chat />}
          {view === "quiz" && <Quiz />}
          {view === "roadmap" && <Roadmap />}
        </section>
      </div>
    </main>
  );
}

function SectionHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="mb-6">
      <div className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#b9634c]">{eyebrow}</div>
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">{title}</h1>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-[#74675d] sm:text-base">{description}</p>
    </div>
  );
}

function Overview({ onNavigate }: { onNavigate: (view: DemoView) => void }) {
  const metrics = [
    { label: "Tài liệu", value: "3", note: "376 chunks", icon: FileText, tone: "bg-[#efd3c7] text-[#8f4738]" },
    { label: "Câu hỏi", value: "24", note: "92% chính xác", icon: Brain, tone: "bg-[#dce6d8] text-[#53634d]" },
    { label: "Tiến độ", value: "68%", note: "7 ngày liên tiếp", icon: Target, tone: "bg-[#f5e3c3] text-[#8a5c22]" },
  ];

  return (
    <div>
      <SectionHeading eyebrow="Workspace mẫu" title="Chào mừng trở lại, Minh" description="Một bản xem trước đầy đủ về cách RAGTutor biến tài liệu thành không gian tự học có trích dẫn." />
      <div className="grid gap-4 md:grid-cols-3">
        {metrics.map(({ label, value, note, icon: Icon, tone }) => (
          <article key={label} className="paper-card rounded-[24px] p-5">
            <div className={`grid h-11 w-11 place-items-center rounded-2xl ${tone}`}><Icon size={21} /></div>
            <div className="mt-5 flex items-end justify-between gap-3">
              <div><div className="text-sm text-[#7d7167]">{label}</div><div className="font-display mt-1 text-3xl font-semibold">{value}</div></div>
              <div className="text-right text-xs text-[#8b7d72]">{note}</div>
            </div>
          </article>
        ))}
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_.75fr]">
        <article className="paper-card rounded-[26px] p-5 sm:p-6">
          <div className="flex items-center justify-between gap-4">
            <div><h2 className="font-display text-xl font-semibold">Tiếp tục học</h2><p className="mt-1 text-sm text-[#7d7167]">Machine Learning căn bản</p></div>
            <span className="rounded-full bg-[#dce6d8] px-3 py-1.5 text-xs font-semibold text-[#53634d]">68% hoàn thành</span>
          </div>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-[#eadfd3]"><div className="h-full w-[68%] rounded-full bg-[#b9634c]" /></div>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <button onClick={() => onNavigate("chat")} className="group rounded-2xl border border-[#6b4f3d]/10 bg-white/55 p-4 text-left transition hover:-translate-y-0.5 hover:bg-white">
              <MessageSquare className="text-[#b9634c]" size={20} /><div className="mt-3 font-semibold">Hỏi đáp với tài liệu</div><div className="mt-1 text-xs leading-5 text-[#7d7167]">Câu trả lời kèm nguồn và số trang</div><ChevronRight className="mt-3 text-[#b9634c] transition group-hover:translate-x-1" size={18} />
            </button>
            <button onClick={() => onNavigate("quiz")} className="group rounded-2xl border border-[#6b4f3d]/10 bg-white/55 p-4 text-left transition hover:-translate-y-0.5 hover:bg-white">
              <Brain className="text-[#718269]" size={20} /><div className="mt-3 font-semibold">Làm bài kiểm tra</div><div className="mt-1 text-xs leading-5 text-[#7d7167]">Ôn tập bằng câu hỏi sinh từ tài liệu</div><ChevronRight className="mt-3 text-[#718269] transition group-hover:translate-x-1" size={18} />
            </button>
          </div>
        </article>
        <article className="rounded-[26px] bg-[#b9634c] p-6 text-white shadow-lg shadow-[#b9634c]/15">
          <GraduationCap size={28} />
          <div className="font-hand mt-5 text-3xl leading-9">Small steps create big progress.</div>
          <div className="mt-6 border-t border-white/20 pt-4 text-sm text-white/80">Mục tiêu hôm nay</div>
          <div className="mt-2 flex items-center gap-2 font-semibold"><CheckCircle2 size={18} /> Hoàn thành 1 quiz</div>
        </article>
      </div>
    </div>
  );
}

function Documents() {
  const [uploaded, setUploaded] = useState(false);
  return (
    <div>
      <SectionHeading eyebrow="Knowledge base" title="Tài liệu học tập" description="Tài liệu được chia thành các đoạn nhỏ, lập chỉ mục và sẵn sàng cho truy xuất ngữ nghĩa." />
      <label className="paper-card flex cursor-pointer flex-col items-center justify-center rounded-[26px] border-dashed p-7 text-center transition hover:border-[#b9634c]/30 hover:bg-white/60">
        <input type="file" className="sr-only" onChange={() => setUploaded(true)} />
        <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#efd3c7] text-[#9a4e3d]"><Upload size={22} /></span>
        <div className="mt-3 font-semibold">{uploaded ? "Đã mô phỏng upload thành công" : "Chọn một tài liệu để thử"}</div>
        <div className="mt-1 text-xs text-[#7d7167]">Demo chỉ đọc tên tệp trong trình duyệt, không tải nội dung lên máy chủ.</div>
      </label>
      <div className="mt-5 space-y-3">
        {documents.map((document) => (
          <article key={document.name} className="paper-card flex flex-col gap-4 rounded-[22px] p-4 sm:flex-row sm:items-center">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl text-white" style={{ background: document.color }}><FileText size={21} /></span>
            <div className="min-w-0 flex-1"><div className="truncate font-semibold">{document.name}</div><div className="mt-1 text-xs text-[#7d7167]">{document.pages} trang · {document.chunks} chunks</div></div>
            <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-[#dce6d8] px-3 py-1.5 text-xs font-semibold text-[#53634d]"><CheckCircle2 size={14} /> Sẵn sàng</span>
          </article>
        ))}
      </div>
    </div>
  );
}

function Chat() {
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState(false);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;
    setAsked(true);
    setQuestion("");
  };
  return (
    <div>
      <SectionHeading eyebrow="Grounded AI" title="Chat với tài liệu" description="Câu trả lời mẫu cho thấy cách hệ thống truy xuất ngữ cảnh và dẫn nguồn thay vì trả lời chung chung." />
      <article className="paper-card overflow-hidden rounded-[26px]">
        <div className="border-b border-[#6b4f3d]/10 bg-white/35 px-5 py-4"><div className="font-semibold">Machine Learning căn bản</div><div className="mt-1 text-xs text-[#7d7167]">3 tài liệu · hội thoại có citation</div></div>
        <div className="min-h-[390px] space-y-5 p-5 sm:p-6">
          <div className="ml-auto max-w-xl rounded-[22px_22px_6px_22px] bg-[#b9634c] px-5 py-4 text-sm leading-6 text-white">Overfitting là gì và làm sao để hạn chế?</div>
          <div className="max-w-2xl rounded-[6px_22px_22px_22px] border border-[#6b4f3d]/10 bg-white/70 px-5 py-4 text-sm leading-7">
            <div className="mb-3 flex items-center gap-2 font-semibold text-[#8f4738]"><Sparkles size={17} /> RAGTutor</div>
            Overfitting xảy ra khi mô hình học quá sát dữ liệu huấn luyện, kể cả nhiễu, nên hoạt động tốt trên tập train nhưng tổng quát kém với dữ liệu mới. Có thể hạn chế bằng regularization, cross-validation, data augmentation, early stopping hoặc giảm độ phức tạp của mô hình.
            <div className="mt-4 flex flex-wrap gap-2"><span className="rounded-lg bg-[#efd3c7]/60 px-2.5 py-1 text-xs text-[#8f4738]">[1] ML căn bản · trang 18</span><span className="rounded-lg bg-[#dce6d8] px-2.5 py-1 text-xs text-[#53634d]">[2] Deep Learning · trang 11</span></div>
          </div>
          {asked && (
            <div className="max-w-2xl rounded-[6px_22px_22px_22px] border border-[#6b4f3d]/10 bg-white/70 px-5 py-4 text-sm leading-7">
              <div className="mb-3 flex items-center gap-2 font-semibold text-[#8f4738]"><Sparkles size={17} /> Phản hồi demo</div>
              Trong bản production, câu hỏi này sẽ được embedding, so khớp với các chunks liên quan và gửi cho mô hình AI cùng nguồn trích dẫn. Bản portfolio dùng phản hồi mô phỏng để không phát sinh chi phí.
              <div className="mt-4"><span className="rounded-lg bg-[#f5e3c3] px-2.5 py-1 text-xs text-[#7c5725]">Không có dữ liệu nào được gửi đi</span></div>
            </div>
          )}
        </div>
        <form onSubmit={submit} className="flex gap-2 border-t border-[#6b4f3d]/10 bg-white/35 p-4">
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Thử nhập một câu hỏi..." className="min-w-0 flex-1 rounded-2xl border border-[#6b4f3d]/10 bg-white px-4 py-3 text-sm outline-none transition focus:border-[#b9634c]/50" />
          <button aria-label="Gửi câu hỏi demo" className="grid h-12 w-12 place-items-center rounded-2xl bg-[#b9634c] text-white transition hover:bg-[#a65440]"><Send size={19} /></button>
        </form>
      </article>
    </div>
  );
}

function Quiz() {
  const answers = ["Tăng số epoch vô hạn", "Regularization và early stopping", "Chỉ dùng tập huấn luyện", "Loại bỏ tập validation"];
  const [selected, setSelected] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const correct = selected === 1;
  return (
    <div>
      <SectionHeading eyebrow="Active recall" title="Kiểm tra kiến thức" description="Câu hỏi được xây dựng từ nội dung tài liệu và kết quả có thể đưa vào lịch ôn tập ngắt quãng." />
      <article className="paper-card rounded-[26px] p-5 sm:p-7">
        <div className="flex items-center justify-between gap-4 text-sm"><span className="font-semibold text-[#b9634c]">Câu 1 / 3</span><span className="flex items-center gap-1.5 text-[#7d7167]"><Clock3 size={15} /> Không giới hạn</span></div>
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-[#eadfd3]"><div className="h-full w-1/3 rounded-full bg-[#b9634c]" /></div>
        <h2 className="font-display mt-7 text-xl font-semibold leading-8 sm:text-2xl">Phương pháp nào phù hợp nhất để giảm overfitting?</h2>
        <div className="mt-5 grid gap-3">
          {answers.map((answer, index) => {
            const chosen = selected === index;
            const isCorrect = checked && index === 1;
            const isWrong = checked && chosen && index !== 1;
            return (
              <button key={answer} disabled={checked} onClick={() => setSelected(index)} className={`flex items-center gap-3 rounded-2xl border p-4 text-left text-sm transition ${isCorrect ? "border-[#718269] bg-[#dce6d8]" : isWrong ? "border-[#b9634c] bg-[#efd3c7]/60" : chosen ? "border-[#b9634c] bg-[#fff7f2]" : "border-[#6b4f3d]/10 bg-white/50 hover:bg-white"}`}>
                <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full border text-xs font-semibold ${chosen || isCorrect ? "border-[#b9634c] bg-[#b9634c] text-white" : "border-[#8b7d72]/25"}`}>{isCorrect ? <Check size={15} /> : String.fromCharCode(65 + index)}</span>{answer}
              </button>
            );
          })}
        </div>
        {checked && <div className={`mt-5 rounded-2xl p-4 text-sm leading-6 ${correct ? "bg-[#dce6d8] text-[#465740]" : "bg-[#f5e3c3] text-[#74501f]"}`}><strong>{correct ? "Chính xác!" : "Chưa chính xác."}</strong> Regularization giới hạn độ phức tạp của mô hình, còn early stopping dừng huấn luyện trước khi mô hình bắt đầu ghi nhớ nhiễu.</div>}
        <button disabled={selected === null || checked} onClick={() => setChecked(true)} className="mt-6 rounded-2xl bg-[#b9634c] px-5 py-3 text-sm font-semibold text-white transition enabled:hover:bg-[#a65440] disabled:cursor-not-allowed disabled:opacity-45">Kiểm tra đáp án</button>
      </article>
    </div>
  );
}

function Roadmap() {
  const progress = useMemo(() => roadmap.filter((item) => item.status === "done").length, []);
  return (
    <div>
      <SectionHeading eyebrow="Personalized plan" title="Lộ trình học tập" description="RAGTutor phân tích knowledge base để đề xuất thứ tự chủ đề và theo dõi tiến độ." />
      <div className="paper-card rounded-[26px] p-5 sm:p-7">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><div><h2 className="font-display text-xl font-semibold">Machine Learning trong 4 tuần</h2><p className="mt-1 text-sm text-[#7d7167]">Mục tiêu: hoàn thành nền tảng và một dự án thực hành</p></div><span className="w-fit rounded-full bg-[#f5e3c3] px-3 py-1.5 text-xs font-semibold text-[#7c5725]">{progress}/4 chặng hoàn thành</span></div>
        <div className="mt-7 space-y-3">
          {roadmap.map((item, index) => (
            <div key={item.title} className={`relative flex gap-4 rounded-2xl border p-4 ${item.status === "active" ? "border-[#b9634c]/35 bg-[#fff7f2]" : "border-[#6b4f3d]/10 bg-white/45"}`}>
              <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-2xl font-semibold ${item.status === "done" ? "bg-[#718269] text-white" : item.status === "active" ? "bg-[#b9634c] text-white" : "bg-[#eadfd3] text-[#7d7167]"}`}>{item.status === "done" ? <Check size={19} /> : index + 1}</span>
              <div><div className="font-semibold">{item.title}</div><div className="mt-1 text-sm leading-6 text-[#7d7167]">{item.detail}</div>{item.status === "active" && <div className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-[#b9634c]"><PlayCircle size={14} /> Đang học</div>}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

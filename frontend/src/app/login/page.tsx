"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen } from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);

    if (error || !data.session) {
      setError(error?.message ?? "Không thể đăng nhập.");
      return;
    }

    localStorage.setItem("sb-access-token", data.session.access_token);
    const inviteToken = localStorage.getItem("ragtutor-invite-token");
    if (inviteToken) {
      router.push("/invite/" + inviteToken);
    } else {
      router.push("/dashboard");
    }
    router.refresh();
  }

  return (
    <main className="paper-grid grid min-h-screen place-items-center px-5 py-10">
      <section className="paper-card w-full max-w-md rounded-[28px] p-7 md:p-9">
        <div className="mb-7 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#b9634c] text-white">
            <BookOpen size={22} />
          </div>
          <div>
            <div className="font-display text-2xl font-semibold">RAGTutor</div>
            <div className="text-xs text-[#7d7167]">Welcome back.</div>
          </div>
        </div>

        <h1 className="font-display text-3xl font-semibold">Đăng nhập</h1>
        <p className="mt-2 text-sm text-[#7d7167]">Tiếp tục học từ tài liệu của bạn.</p>

        <form onSubmit={onSubmit} className="mt-7 space-y-4">
          <input
            type="email"
            required
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-2xl border border-[#6f5340]/15 bg-white/80 px-4 py-3 outline-none focus:border-[#b9634c]/40"
          />
          <input
            type="password"
            required
            placeholder="Mật khẩu"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-2xl border border-[#6f5340]/15 bg-white/80 px-4 py-3 outline-none focus:border-[#b9634c]/40"
          />
          {error && <p className="text-sm text-red-700">{error}</p>}
          <button
            disabled={loading}
            className="w-full rounded-2xl bg-[#b9634c] px-4 py-3 font-semibold text-white transition hover:bg-[#a65440] disabled:opacity-60"
          >
            {loading ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[#7d7167]">
          Chưa có tài khoản?{" "}
          <Link href="/signup" className="font-semibold text-[#9b4d3b]">
            Đăng ký
          </Link>
        </p>
      </section>
    </main>
  );
}

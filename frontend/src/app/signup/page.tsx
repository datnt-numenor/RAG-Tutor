"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen } from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    });

    setLoading(false);

    if (error) {
      setError(error.message);
      return;
    }

    if (data.session) {
      localStorage.setItem("sb-access-token", data.session.access_token);
      router.push("/dashboard");
      router.refresh();
      return;
    }

    router.push("/login");
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
            <div className="text-xs text-[#7d7167]">Build your study space.</div>
          </div>
        </div>

        <h1 className="font-display text-3xl font-semibold">Tạo tài khoản</h1>
        <p className="mt-2 text-sm text-[#7d7167]">Bắt đầu xây knowledge base của riêng bạn.</p>

        <form onSubmit={onSubmit} className="mt-7 space-y-4">
          <input
            required
            placeholder="Họ tên"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-2xl border border-[#6f5340]/15 bg-white/80 px-4 py-3 outline-none focus:border-[#b9634c]/40"
          />
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
            minLength={6}
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
            {loading ? "Đang tạo..." : "Đăng ký"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[#7d7167]">
          Đã có tài khoản?{" "}
          <Link href="/login" className="font-semibold text-[#9b4d3b]">
            Đăng nhập
          </Link>
        </p>
      </section>
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { BookOpen, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/providers/AuthProvider";

type Profile = {
  email: string;
  fullName: string;
};

export default function SettingsPage() {
  const { signOut } = useAuth();
  const [profile, setProfile] = useState<Profile>({
    email: "",
    fullName: "",
  });

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      const user = data.user;
      setProfile({
        email: user?.email ?? "",
        fullName:
          typeof user?.user_metadata?.full_name === "string"
            ? user.user_metadata.full_name
            : "",
      });
    });
  }, []);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <section>
        <div className="font-hand text-2xl text-[#b9634c]">Your study space</div>
        <h1 className="font-display text-4xl font-semibold">Settings</h1>
        <p className="mt-2 text-[#7d7167]">
          Thông tin tài khoản và trạng thái bảo mật của phiên đăng nhập.
        </p>
      </section>

      <section className="paper-card rounded-[26px] p-5 md:p-6">
        <div className="flex items-center gap-4">
          <div className="grid h-14 w-14 place-items-center rounded-2xl bg-[#f3ddd4] text-[#9c513e]">
            <UserRound size={24} />
          </div>
          <div>
            <h2 className="font-display text-2xl font-semibold">
              {profile.fullName || "RAGTutor user"}
            </h2>
            <p className="mt-1 text-sm text-[#8a7b70]">{profile.email}</p>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl bg-white/58 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck size={18} className="text-[#70836a]" />
              Authentication
            </div>
            <p className="mt-2 text-sm leading-6 text-[#7d7167]">
              Supabase Auth access token được FastAPI verify bằng JWKS với ES256/RS256.
            </p>
          </div>

          <div className="rounded-2xl bg-white/58 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <BookOpen size={18} className="text-[#9c513e]" />
              Study data
            </div>
            <p className="mt-2 text-sm leading-6 text-[#7d7167]">
              Projects, documents, chunks, chats và quiz được tách theo project trên Supabase.
            </p>
          </div>
        </div>

        <button
          onClick={() => void signOut()}
          className="mt-6 inline-flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 px-5 py-3 font-semibold text-red-700"
        >
          <LogOut size={18} />
          Đăng xuất
        </button>
      </section>
    </div>
  );
}

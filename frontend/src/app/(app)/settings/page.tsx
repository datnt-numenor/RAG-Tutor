"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  Clock3,
  LogOut,
  Save,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { getMyProfile, updateMyProfile } from "@/lib/ragtutor";
import { useAuth } from "@/providers/AuthProvider";

const COMMON_TIMEZONES = [
  "Asia/Ho_Chi_Minh",
  "Asia/Bangkok",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Asia/Seoul",
  "Europe/London",
  "Europe/Paris",
  "America/New_York",
  "America/Los_Angeles",
  "UTC",
];

export default function SettingsPage() {
  const { signOut } = useAuth();
  const queryClient = useQueryClient();
  const profile = useQuery({
    queryKey: ["my-profile"],
    queryFn: getMyProfile,
  });

  const [fullNameOverride, setFullNameOverride] = useState<string | null>(null);
  const [timezoneOverride, setTimezoneOverride] = useState<string | null>(null);

  const fullName = fullNameOverride ?? profile.data?.full_name ?? "";
  const timezone =
    timezoneOverride ?? profile.data?.timezone ?? "Asia/Ho_Chi_Minh";

  const save = useMutation({
    mutationFn: () =>
      updateMyProfile({
        full_name: fullName.trim(),
        timezone: timezone.trim(),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["my-profile"] });
      setFullNameOverride(null);
      setTimezoneOverride(null);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!fullName.trim() || !timezone.trim()) return;
    save.mutate();
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <section>
        <div className="font-hand text-2xl text-[#b9634c]">Your study space</div>
        <h1 className="font-display text-4xl font-semibold">Settings</h1>
        <p className="mt-2 text-[#7d7167]">
          Profile và timezone được dùng trực tiếp cho roadmap, schedule và progress.
        </p>
      </section>

      <section className="paper-card rounded-[26px] p-5 md:p-6">
        <div className="flex items-center gap-4">
          <div className="grid h-14 w-14 place-items-center rounded-2xl bg-[#f3ddd4] text-[#9c513e]">
            <UserRound size={24} />
          </div>
          <div>
            <h2 className="font-display text-2xl font-semibold">
              {profile.data?.full_name || "RAGTutor user"}
            </h2>
            <p className="mt-1 text-sm text-[#8a7b70]">
              {profile.data?.email || "Đang tải..."}
            </p>
          </div>
        </div>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-[#66584f]">
              Họ tên
            </span>
            <input
              value={fullName}
              maxLength={120}
              onChange={(event) => setFullNameOverride(event.target.value)}
              className="w-full rounded-2xl border border-[#705541]/15 bg-white/75 px-4 py-3 outline-none focus:border-[#b9634c]/40"
              placeholder="Nguyễn Văn A"
            />
          </label>

          <label className="block">
            <span className="mb-2 flex items-center gap-2 text-sm font-semibold text-[#66584f]">
              <Clock3 size={16} />
              Timezone
            </span>
            <input
              list="ragtutor-timezones"
              value={timezone}
              onChange={(event) => setTimezoneOverride(event.target.value)}
              className="w-full rounded-2xl border border-[#705541]/15 bg-white/75 px-4 py-3 outline-none focus:border-[#b9634c]/40"
              placeholder="Asia/Ho_Chi_Minh"
            />
            <datalist id="ragtutor-timezones">
              {COMMON_TIMEZONES.map((value) => (
                <option key={value} value={value} />
              ))}
            </datalist>
            <p className="mt-2 text-xs leading-5 text-[#8a7b70]">
              Dùng IANA timezone, ví dụ Asia/Ho_Chi_Minh. Lịch AI được tạo theo giờ này rồi lưu UTC.
            </p>
          </label>

          {save.isError && (
            <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
              Không lưu được profile. Kiểm tra timezone có phải IANA timezone hợp lệ hay không.
            </div>
          )}
          {save.isSuccess && (
            <div className="rounded-xl bg-[#dce6d8] p-3 text-sm text-[#50664c]">
              Đã lưu profile.
            </div>
          )}

          <button
            disabled={save.isPending || !fullName.trim() || !timezone.trim()}
            className="inline-flex items-center gap-2 rounded-2xl bg-[#b9634c] px-5 py-3 font-semibold text-white disabled:opacity-50"
          >
            <Save size={17} />
            {save.isPending ? "Đang lưu..." : "Lưu thay đổi"}
          </button>
        </form>

        <div className="mt-7 grid gap-4 border-t border-[#755640]/10 pt-6 md:grid-cols-2">
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
              Projects, documents, vectors, chats, quiz và progress được tách theo project.
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

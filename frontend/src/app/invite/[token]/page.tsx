"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BookOpen, CheckCircle2, Clock3, UserPlus } from "lucide-react";
import {
  acceptInvitation,
  previewInvitation,
  rejectInvitation,
} from "@/lib/ragtutor";
import { useAuth } from "@/providers/AuthProvider";

export default function InvitePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = use(params);
  const router = useRouter();
  const { accessToken, loading } = useAuth();
  const [accepted, setAccepted] = useState(false);

  const preview = useQuery({
    queryKey: ["invitation-preview", token],
    queryFn: () => previewInvitation(token),
  });

  const accept = useMutation({
    mutationFn: () => acceptInvitation(token),
    onSuccess: () => {
      setAccepted(true);
      localStorage.removeItem("ragtutor-invite-token");
    },
  });

  const reject = useMutation({
    mutationFn: () => rejectInvitation(token),
    onSuccess: () => router.push("/dashboard"),
  });

  useEffect(() => {
    if (accepted) {
      const timer = setTimeout(() => router.push("/projects"), 1000);
      return () => clearTimeout(timer);
    }
  }, [accepted, router]);

  function handleAccept() {
    if (!accessToken) {
      localStorage.setItem("ragtutor-invite-token", token);
      router.push("/login");
      return;
    }
    accept.mutate();
  }

  return (
    <main className="paper-grid grid min-h-screen place-items-center px-5 py-10">
      <section className="paper-card w-full max-w-lg rounded-[30px] p-7 md:p-9">
        <div className="mb-7 flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[#b9634c] text-white">
            <BookOpen size={23} />
          </div>
          <div>
            <div className="font-display text-2xl font-semibold">RAGTutor</div>
            <div className="text-xs text-[#7d7167]">Project invitation</div>
          </div>
        </div>

        {preview.isLoading && (
          <div className="rounded-2xl bg-white/55 p-6 text-sm text-[#7d7167]">
            Đang kiểm tra invitation...
          </div>
        )}

        {preview.isError && (
          <div className="rounded-2xl bg-red-50 p-5 text-sm leading-6 text-red-700">
            Invitation không tồn tại, đã hết hạn hoặc không còn ở trạng thái pending.
          </div>
        )}

        {preview.data && !accepted && (
          <>
            <div className="font-hand text-2xl text-[#b9634c]">You have been invited</div>
            <h1 className="font-display mt-1 text-3xl font-semibold">
              {preview.data.project_name}
            </h1>
            <p className="mt-3 leading-7 text-[#71645a]">
              {preview.data.invited_by
                ? preview.data.invited_by + " đã mời bạn tham gia project này."
                : "Bạn được mời tham gia project này."}
            </p>

            <div className="mt-5 flex items-center gap-3 rounded-2xl bg-[#fff8e8] p-4 text-sm text-[#806633]">
              <Clock3 size={18} />
              Hết hạn: {new Date(preview.data.expires_at).toLocaleString()}
            </div>

            {!loading && !accessToken && (
              <div className="mt-4 rounded-2xl bg-[#eef3eb] p-4 text-sm leading-6 text-[#587052]">
                Bạn cần đăng nhập bằng đúng email được mời. Sau đăng nhập hệ thống sẽ đưa bạn quay lại invitation này.
              </div>
            )}

            {accept.isError && (
              <div className="mt-4 rounded-2xl bg-red-50 p-4 text-sm text-red-700">
                Không thể tham gia project. Kiểm tra email tài khoản có trùng email được mời hay không.
              </div>
            )}

            <div className="mt-7 flex gap-3">
              <button
                onClick={handleAccept}
                disabled={accept.isPending}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-2xl bg-[#b9634c] px-5 py-3 font-semibold text-white disabled:opacity-60"
              >
                <UserPlus size={18} />
                {accessToken ? "Tham gia project" : "Đăng nhập để tham gia"}
              </button>

              <button
                onClick={() => reject.mutate()}
                disabled={reject.isPending}
                className="rounded-2xl border border-[#755640]/15 bg-white/70 px-5 py-3 font-semibold text-[#76675d]"
              >
                Từ chối
              </button>
            </div>
          </>
        )}

        {accepted && (
          <div className="py-8 text-center">
            <CheckCircle2 className="mx-auto text-[#70836a]" size={44} />
            <h1 className="font-display mt-4 text-3xl font-semibold">
              Đã tham gia project
            </h1>
            <p className="mt-2 text-sm text-[#7d7167]">
              Đang chuyển tới danh sách projects...
            </p>
          </div>
        )}
      </section>
    </main>
  );
}

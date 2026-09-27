"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { loading, accessToken } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !accessToken) router.replace("/login");
  }, [loading, accessToken, router]);

  if (loading || !accessToken) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#f8f2e9]">
        <div className="rounded-2xl bg-white/70 px-5 py-3 text-sm text-[#7d7167] shadow-sm">
          Đang kiểm tra phiên đăng nhập...
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

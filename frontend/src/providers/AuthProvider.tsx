"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

type AuthContextValue = {
  loading: boolean;
  accessToken: string | null;
  signOut: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      const token = data.session?.access_token ?? null;
      setAccessToken(token);
      if (token) localStorage.setItem("sb-access-token", token);
      else localStorage.removeItem("sb-access-token");
      setLoading(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      const token = session?.access_token ?? null;
      setAccessToken(token);
      if (token) localStorage.setItem("sb-access-token", token);
      else localStorage.removeItem("sb-access-token");
    });

    return () => {
      mounted = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    loading,
    accessToken,
    refreshToken: async () => {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token ?? null;
      setAccessToken(token);
      if (token) localStorage.setItem("sb-access-token", token);
      return token;
    },
    signOut: async () => {
      await supabase.auth.signOut();
      localStorage.removeItem("sb-access-token");
      setAccessToken(null);
      router.push("/login");
      router.refresh();
    },
  }), [loading, accessToken, router]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

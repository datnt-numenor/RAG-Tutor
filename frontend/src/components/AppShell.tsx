"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  Brain,
  FileText,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Map,
  Menu,
  MessageSquare,
  Settings,
  X,
} from "lucide-react";
import { useAuth } from "@/providers/AuthProvider";
import { GlobalSearch } from "@/components/GlobalSearch";

const items = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/quiz", label: "Quiz", icon: Brain },
  { href: "/roadmap", label: "Roadmap", icon: Map },
  { href: "/progress", label: "Progress", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { signOut } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!mobileOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [mobileOpen]);

  return (
    <div className="min-h-screen bg-[#f8f2e9] text-[#29231f]">
      <DesktopSidebar pathname={pathname} signOut={signOut} />

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Đóng menu"
            className="absolute inset-0 bg-[#33271f]/35 backdrop-blur-[2px]"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 flex w-[min(86vw,320px)] flex-col border-r border-[#6b4f3d]/10 bg-[#f7efe3] p-5 shadow-2xl">
            <div className="mb-7 flex items-center justify-between">
              <Brand />
              <button
                aria-label="Đóng menu"
                onClick={() => setMobileOpen(false)}
                className="grid h-10 w-10 place-items-center rounded-xl bg-white/65 text-[#685a50]"
              >
                <X size={19} />
              </button>
            </div>

            <Navigation
              pathname={pathname}
              onNavigate={() => setMobileOpen(false)}
            />

            <div className="mt-auto space-y-4">
              <div className="rotate-[-1deg] rounded-2xl bg-[#f3df9e] p-4">
                <div className="font-hand text-2xl leading-7 text-[#4d4037]">
                  Small steps create big progress.
                </div>
              </div>
              <button
                onClick={() => void signOut()}
                className="flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-[#6c5f55] hover:bg-white/60"
              >
                <LogOut size={18} />
                Đăng xuất
              </button>
            </div>
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-20 items-center gap-3 border-b border-[#6b4f3d]/10 bg-[#fffaf4]/88 px-4 backdrop-blur md:px-8">
          <button
            aria-label="Mở menu"
            onClick={() => setMobileOpen(true)}
            className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-[#705541]/10 bg-white/70 text-[#725f52] lg:hidden"
          >
            <Menu size={20} />
          </button>

          <Link
            href="/dashboard"
            className="mr-1 flex shrink-0 items-center gap-2 lg:hidden"
          >
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#b9634c] text-white">
              <BookOpen size={19} />
            </div>
            <span className="font-display hidden text-xl font-semibold sm:inline">
              RAGTutor
            </span>
          </Link>

          <div className="relative mx-auto w-full max-w-3xl">
            <GlobalSearch />
          </div>
        </header>

        <main className="paper-grid min-h-[calc(100vh-5rem)] p-4 sm:p-5 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}

function DesktopSidebar({
  pathname,
  signOut,
}: {
  pathname: string;
  signOut: () => Promise<void>;
}) {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-[#6b4f3d]/10 bg-[#f4ecdf]/92 p-5 backdrop-blur lg:flex lg:flex-col">
      <div className="mb-8">
        <Brand />
      </div>

      <Navigation pathname={pathname} />

      <div className="mt-auto space-y-4">
        <div className="rotate-[-2deg] rounded-2xl bg-[#f3df9e] p-4 shadow-sm">
          <div className="font-hand text-2xl leading-7 text-[#4d4037]">
            Small steps create big progress.
          </div>
        </div>
        <button
          onClick={() => void signOut()}
          className="flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-[#6c5f55] transition hover:bg-white/60"
        >
          <LogOut size={18} />
          Đăng xuất
        </button>
      </div>
    </aside>
  );
}

function Brand() {
  return (
    <Link href="/dashboard" className="flex items-center gap-3">
      <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#b9634c] text-white shadow-lg shadow-[#b9634c]/20">
        <BookOpen size={23} />
      </div>
      <div>
        <div className="font-display text-2xl font-semibold">RAGTutor</div>
        <div className="text-[10px] tracking-wide text-[#7d7167]">
          deeper understanding
        </div>
      </div>
    </Link>
  );
}

function Navigation({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="space-y-1">
      {items.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(item.href + "/");
        const Icon = item.icon;

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={
              "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition " +
              (active
                ? "bg-[#b9634c] text-white shadow-md shadow-[#b9634c]/15"
                : "text-[#4e433b] hover:bg-white/60")
            }
          >
            <Icon size={19} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

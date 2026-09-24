"use client";

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
  MessageSquare,
  Settings,
} from "lucide-react";
import { useAuth } from "@/providers/AuthProvider";

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

  return (
    <div className="min-h-screen bg-[#f8f2e9] text-[#29231f]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-[#6b4f3d]/10 bg-[#f4ecdf]/92 p-5 backdrop-blur lg:flex lg:flex-col">
        <Link href="/dashboard" className="mb-8 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#b9634c] text-white shadow-lg shadow-[#b9634c]/20">
            <BookOpen size={23} />
          </div>
          <div>
            <div className="font-display text-2xl font-semibold">RAGTutor</div>
            <div className="text-[10px] tracking-wide text-[#7d7167]">deeper understanding</div>
          </div>
        </Link>

        <nav className="space-y-1">
          {items.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
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

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-20 items-center border-b border-[#6b4f3d]/10 bg-[#fffaf4]/88 px-5 backdrop-blur md:px-8">
          <div className="relative mx-auto w-full max-w-3xl">
            <input
              className="w-full rounded-2xl border border-[#705541]/12 bg-white/75 px-5 py-3 text-sm outline-none transition placeholder:text-[#9b8c81] focus:border-[#b9634c]/35 focus:ring-4 focus:ring-[#b9634c]/8"
              placeholder="Search your projects, documents, or ask a question..."
            />
          </div>
        </header>
        <main className="paper-grid min-h-[calc(100vh-5rem)] p-5 md:p-8">{children}</main>
      </div>
    </div>
  );
}

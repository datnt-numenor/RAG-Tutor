"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { FileText, FolderKanban, Search, X } from "lucide-react";
import { globalSearch } from "@/lib/ragtutor";

export function GlobalSearch() {
  const router = useRouter();
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [value, setValue] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebounced(value.trim());
    }, 220);
    return () => window.clearTimeout(timer);
  }, [value]);

  useEffect(() => {
    function close(event: MouseEvent) {
      if (!boxRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const results = useQuery({
    queryKey: ["global-search", debounced],
    queryFn: () => globalSearch(debounced),
    enabled: debounced.length >= 2,
    staleTime: 20_000,
  });

  function go(href: string) {
    setOpen(false);
    setValue("");
    setDebounced("");
    router.push(href);
  }

  return (
    <div ref={boxRef} className="relative w-full">
      <Search
        size={17}
        className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#9b8c81]"
      />
      <input
        value={value}
        onChange={(event) => {
          setValue(event.target.value);
          setOpen(true);
        }}
        onFocus={() => value.trim().length >= 2 && setOpen(true)}
        onKeyDown={(event) => {
          if (
            event.key === "Enter" &&
            results.data &&
            results.data.length > 0
          ) {
            go(results.data[0].href);
          }
          if (event.key === "Escape") setOpen(false);
        }}
        className="w-full rounded-2xl border border-[#705541]/12 bg-white/75 py-3 pl-11 pr-10 text-sm outline-none transition placeholder:text-[#9b8c81] focus:border-[#b9634c]/35 focus:ring-4 focus:ring-[#b9634c]/8"
        placeholder="Search projects or documents..."
        aria-label="Search projects and documents"
      />

      {value && (
        <button
          type="button"
          aria-label="Clear search"
          onClick={() => {
            setValue("");
            setDebounced("");
            setOpen(false);
          }}
          className="absolute right-3 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-lg text-[#8c7b70] hover:bg-[#efe5d8]"
        >
          <X size={14} />
        </button>
      )}

      {open && debounced.length >= 2 && (
        <div className="paper-card absolute left-0 right-0 top-[calc(100%+10px)] z-50 max-h-[min(420px,60vh)] overflow-y-auto rounded-2xl p-2 shadow-2xl">
          {results.isFetching && (
            <div className="px-4 py-4 text-sm text-[#8a7b70]">
              Đang tìm...
            </div>
          )}

          {!results.isFetching && results.data?.length === 0 && (
            <div className="px-4 py-5 text-sm text-[#8a7b70]">
              Không tìm thấy project hoặc document phù hợp.
            </div>
          )}

          {results.data?.map((item) => {
            const Icon = item.type === "project" ? FolderKanban : FileText;
            return (
              <button
                type="button"
                key={item.type + ":" + item.id}
                onClick={() => go(item.href)}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition hover:bg-[#f5ede3]"
              >
                <span
                  className={
                    "grid h-9 w-9 shrink-0 place-items-center rounded-xl " +
                    (item.type === "project"
                      ? "bg-[#dce6d8] text-[#5d7357]"
                      : "bg-[#f3ddd4] text-[#9c513e]")
                  }
                >
                  <Icon size={16} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold">
                    {item.title}
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-[#8a7b70]">
                    {item.type === "project" ? "Project" : item.subtitle || "Document"}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

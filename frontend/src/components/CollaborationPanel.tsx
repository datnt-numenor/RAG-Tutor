"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, MailPlus, Trash2, Users } from "lucide-react";
import {
  createProjectInvitation,
  listProjectInvitations,
  revokeProjectInvitation,
} from "@/lib/ragtutor";

export function CollaborationPanel({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [latestLink, setLatestLink] = useState("");

  const invitations = useQuery({
    queryKey: ["project-invitations", projectId],
    queryFn: () => listProjectInvitations(projectId),
  });

  const invite = useMutation({
    mutationFn: () => createProjectInvitation(projectId, email.trim()),
    onSuccess: async (data) => {
      setEmail("");
      const absolute =
        typeof window !== "undefined"
          ? window.location.origin + data.invite_link
          : data.invite_link;
      setLatestLink(absolute);
      await queryClient.invalidateQueries({
        queryKey: ["project-invitations", projectId],
      });
    },
  });

  const revoke = useMutation({
    mutationFn: (invitationId: string) =>
      revokeProjectInvitation(projectId, invitationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["project-invitations", projectId],
      });
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    invite.mutate();
  }

  return (
    <section className="paper-card rounded-[26px] p-5 md:p-6">
      <div className="mb-5 flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-[#dce6d8] text-[#5d7357]">
          <Users size={20} />
        </div>
        <div>
          <h2 className="font-display text-2xl font-semibold">Collaboration</h2>
          <p className="mt-1 text-sm text-[#8a7b70]">
            Owner mời member bằng email, link có hạn 7 ngày.
          </p>
        </div>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="student@example.com"
          className="min-w-0 flex-1 rounded-2xl border border-[#705541]/15 bg-white/80 px-4 py-3 outline-none focus:border-[#b9634c]/40"
        />
        <button
          disabled={invite.isPending}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-[#b9634c] px-5 py-3 font-semibold text-white disabled:opacity-60"
        >
          <MailPlus size={17} />
          {invite.isPending ? "Đang tạo..." : "Invite"}
        </button>
      </form>

      {invite.isError && (
        <div className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">
          Không tạo được invitation. Có thể email này đã có invitation pending hoặc bạn không phải owner.
        </div>
      )}

      {latestLink && (
        <div className="mt-4 rounded-2xl bg-[#fff8e8] p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-[#8f6b2d]">
            Invite link vừa tạo
          </div>
          <div className="mt-2 flex items-center gap-2">
            <input
              readOnly
              value={latestLink}
              className="min-w-0 flex-1 rounded-xl border border-[#9a7845]/15 bg-white/70 px-3 py-2 text-xs"
            />
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(latestLink)}
              className="grid h-9 w-9 place-items-center rounded-xl bg-white text-[#8f6b2d]"
              title="Copy invite link"
            >
              <Copy size={15} />
            </button>
          </div>
        </div>
      )}

      <div className="mt-5 space-y-2">
        {invitations.data?.map((item) => (
          <div
            key={item.id}
            className="flex items-center gap-3 rounded-2xl border border-[#755640]/9 bg-white/58 p-4"
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">
                {item.invited_email}
              </div>
              <div className="mt-1 text-xs text-[#8a7b70]">
                {item.status} · hết hạn {new Date(item.expires_at).toLocaleString()}
              </div>
            </div>
            {item.status === "pending" && (
              <button
                onClick={() => revoke.mutate(item.id)}
                disabled={revoke.isPending}
                className="grid h-9 w-9 place-items-center rounded-xl border border-red-200 text-red-600"
                title="Revoke"
              >
                <Trash2 size={15} />
              </button>
            )}
          </div>
        ))}

        {!invitations.isLoading && !invitations.data?.length && (
          <div className="rounded-2xl bg-white/45 p-4 text-sm text-[#8a7b70]">
            Chưa có invitation nào.
          </div>
        )}
      </div>
    </section>
  );
}

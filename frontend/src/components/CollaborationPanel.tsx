"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Crown, MailPlus, Trash2, UserRound, Users } from "lucide-react";
import {
  createProjectInvitation,
  deleteProject,
  listProjectInvitations,
  listProjectMembers,
  removeProjectMember,
  revokeProjectInvitation,
} from "@/lib/ragtutor";
import { supabase } from "@/lib/supabase";

export function CollaborationPanel({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [latestLink, setLatestLink] = useState("");
  const [currentUserId, setCurrentUserId] = useState("");

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      setCurrentUserId(data.user?.id ?? "");
    });
  }, []);

  const members = useQuery({
    queryKey: ["project-members", projectId],
    queryFn: () => listProjectMembers(projectId),
  });

  const myMembership = useMemo(
    () => members.data?.find((member) => member.user_id === currentUserId),
    [members.data, currentUserId],
  );
  const isOwner = myMembership?.role === "owner";

  const invitations = useQuery({
    queryKey: ["project-invitations", projectId],
    queryFn: () => listProjectInvitations(projectId),
    enabled: isOwner,
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

  const removeMember = useMutation({
    mutationFn: (userId: string) => removeProjectMember(projectId, userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["project-members", projectId],
      });
    },
  });

  const removeProject = useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.replace("/projects");
      router.refresh();
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!email.trim() || !isOwner) return;
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
            Thành viên trong project và invitation đang chờ.
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#8a7b70]">
          Members
        </div>
        {members.data?.map((member) => (
          <div
            key={member.id}
            className="flex items-center gap-3 rounded-2xl border border-[#755640]/9 bg-white/58 p-4"
          >
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#eee4d8] text-[#79685c]">
              <UserRound size={17} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">
                {member.users?.full_name || member.users?.email || "Member"}
              </div>
              <div className="mt-1 truncate text-xs text-[#8a7b70]">
                {member.users?.email}
              </div>
            </div>
            <span
              className={
                "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold " +
                (member.role === "owner"
                  ? "bg-[#f5e3c3] text-[#876225]"
                  : "bg-[#dce6d8] text-[#587052]")
              }
            >
              {member.role === "owner" && <Crown size={12} />}
              {member.role}
            </span>
            {isOwner && member.role !== "owner" && (
              <button
                type="button"
                onClick={() => {
                  const label =
                    member.users?.full_name ||
                    member.users?.email ||
                    "member này";
                  if (
                    window.confirm(
                      "Xóa " + label + " khỏi project?",
                    )
                  ) {
                    removeMember.mutate(member.user_id);
                  }
                }}
                disabled={removeMember.isPending}
                className="grid h-9 w-9 place-items-center rounded-xl border border-red-200 text-red-600 disabled:opacity-50"
                title="Remove member"
              >
                <Trash2 size={15} />
              </button>
            )}
          </div>
        ))}
      </div>

      {isOwner && (
        <>
          <div className="my-5 border-t border-[#755640]/10" />

          <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
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
              Không tạo được invitation. Email có thể đã là member hoặc đang có invitation pending.
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
                  onClick={() => void navigator.clipboard.writeText(latestLink)}
                  className="grid h-9 w-9 place-items-center rounded-xl bg-white text-[#8f6b2d]"
                  title="Copy invite link"
                >
                  <Copy size={15} />
                </button>
              </div>
            </div>
          )}

          <div className="mt-5 space-y-2">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#8a7b70]">
              Invitations
            </div>
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
                    {item.status} · hết hạn{" "}
                    {new Date(item.expires_at).toLocaleString()}
                  </div>
                </div>
                {item.status === "pending" && (
                  <button
                    type="button"
                    onClick={() => revoke.mutate(item.id)}
                    disabled={revoke.isPending}
                    className="grid h-9 w-9 place-items-center rounded-xl border border-red-200 text-red-600 disabled:opacity-50"
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

          <div className="my-5 border-t border-red-200/70" />

          <div className="rounded-2xl border border-red-200 bg-red-50/70 p-4">
            <div className="text-sm font-semibold text-red-800">
              Delete project permanently
            </div>
            <p className="mt-1 text-xs leading-5 text-red-700">
              Xóa toàn bộ documents, chunks, chat, quiz, roadmap, schedules,
              annotations và file Storage thuộc project này.
            </p>
            <button
              type="button"
              onClick={() => {
                if (
                  window.confirm(
                    "Xóa vĩnh viễn project này? Thao tác không thể hoàn tác.",
                  )
                ) {
                  removeProject.mutate();
                }
              }}
              disabled={removeProject.isPending}
              className="mt-3 inline-flex items-center gap-2 rounded-xl bg-red-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              <Trash2 size={15} />
              {removeProject.isPending ? "Đang xóa..." : "Delete project"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}

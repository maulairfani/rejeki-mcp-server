import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { RefreshCw, Unlink, User } from "lucide-react"
import { useBackupStatus, useTriggerBackup } from "@/hooks/useBackup"
import {
  useMorningBriefing,
  useUpdateMorningBriefing,
} from "@/hooks/useMorningBriefing"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { useAuth } from "@/hooks/useAuth"
import { PageHeader } from "@/components/shared/PageHeader"
import { Badge } from "@/components/shared/Badge"
import { cn } from "@/lib/utils"

const TABS = [
  { id: "account", label: "Account" },
  { id: "briefing", label: "Briefing" },
  { id: "backup", label: "Backup" },
] as const

type TabId = (typeof TABS)[number]["id"]

function formatDate(iso: string | null | undefined) {
  if (!iso) return "Never"
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get("tab")
  const tab: TabId = (TABS.find((t) => t.id === rawTab)?.id ?? "account")
  const setTab = (next: TabId) => setSearchParams({ tab: next }, { replace: true })

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <PageHeader title="Settings" hideAmountsBadge />

      {/* Mobile tab bar */}
      <div
        role="tablist"
        aria-label="Settings sections"
        className="flex shrink-0 gap-1 border-b border-border px-4 md:hidden"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "relative -mb-px px-3 py-2.5 text-[13px] font-semibold transition-colors",
              tab === t.id
                ? "text-text-primary after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:rounded-t-full after:bg-brand"
                : "text-text-muted hover:text-text-secondary",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop left nav */}
        <nav
          role="tablist"
          aria-label="Settings sections"
          className="hidden w-48 shrink-0 flex-col gap-0.5 border-r border-border px-3 py-5 md:flex"
        >
          <p className="mb-2 px-2.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            Settings
          </p>
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "relative flex h-8 w-full items-center rounded-md px-2.5 text-[13px] font-medium transition-colors",
                tab === t.id
                  ? "bg-brand/10 text-brand before:absolute before:left-0 before:top-1/2 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-brand"
                  : "text-text-secondary hover:bg-bg-muted hover:text-text-primary",
              )}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-5 md:px-8 md:py-7">
          <div className="mx-auto max-w-xl">
            {tab === "account" && <AccountCard />}
            {tab === "briefing" && <MorningBriefingCard />}
            {tab === "backup" && <BackupCard />}
          </div>
          <div className="h-10" />
        </div>
      </div>
    </div>
  )
}

function BackupCard() {
  const { data: status, isLoading } = useBackupStatus()
  const triggerBackup = useTriggerBackup()
  const queryClient = useQueryClient()

  const disconnect = useMutation({
    mutationFn: () => api("/api/backup/google/disconnect", { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["backup-status"] }),
  })

  return (
    <>
      {/* Google Drive Backup Card */}
          <div className="mt-6 rounded-xl border border-border bg-card p-5 shadow-xs">
            <div className="mb-4 flex items-start gap-3.5">
              <div
                className="flex size-10 items-center justify-center rounded-lg text-xl"
                style={{ background: "oklch(94% 0.05 255 / 0.7)" }}
              >
                🔄
              </div>
              <div>
                <p className="font-heading text-sm font-bold text-text-primary">
                  Google Drive Backup
                </p>
                <p className="text-[12.5px] text-text-muted">
                  Automatically back up your database daily
                </p>
              </div>
            </div>

            {isLoading ? (
              <div className="h-8 w-32 animate-pulse rounded bg-bg-muted" />
            ) : status?.connected ? (
              <>
                <div className="mb-3.5 flex items-center justify-between rounded-lg bg-bg-muted px-3.5 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="inline-block size-[7px] rounded-full bg-brand" />
                    <span className="text-[13px] font-semibold text-text-primary">
                      Connected
                    </span>
                    {status.google_email && (
                      <span className="text-[12px] text-text-muted">
                        · {status.google_email}
                      </span>
                    )}
                  </div>
                  <Badge color="success">Active</Badge>
                </div>

                <div className="mb-4">
                  <div className="mb-1 text-[11.5px] font-medium text-text-muted">
                    Last backup
                  </div>
                  <div className="mb-1 text-[13.5px] font-semibold text-text-primary">
                    {formatDate(status.last_backup_at)}
                  </div>
                  <div className="text-xs text-text-muted">
                    Backups run daily at 02:00 UTC · Last 7 backups are kept
                  </div>
                </div>

                <div className="flex gap-2.5">
                  <button
                    onClick={() => triggerBackup.mutate()}
                    disabled={triggerBackup.isPending}
                    className="inline-flex items-center gap-1.5 rounded-md bg-brand px-4 py-2 text-[13px] font-semibold text-white transition-opacity hover:opacity-85 disabled:cursor-wait"
                  >
                    <RefreshCw
                      className={`size-3.5 ${
                        triggerBackup.isPending ? "animate-spin" : ""
                      }`}
                    />
                    {triggerBackup.isPending ? "Backing up…" : "Back up now"}
                  </button>
                  <button
                    onClick={() => disconnect.mutate()}
                    disabled={disconnect.isPending}
                    className="inline-flex items-center gap-1.5 rounded-md bg-danger-light px-4 py-2 text-[13px] font-semibold text-[color:var(--danger)] transition-opacity hover:opacity-85"
                  >
                    <Unlink className="size-3.5" />
                    Disconnect
                  </button>
                </div>

                {triggerBackup.isSuccess && (
                  <p className="mt-3 text-xs text-[color:var(--success)]">
                    Backup completed successfully.
                  </p>
                )}
                {triggerBackup.isError && (
                  <p className="mt-3 text-xs text-[color:var(--danger)]">
                    {triggerBackup.error?.message ?? "Backup failed."}
                  </p>
                )}
              </>
            ) : (
              <>
                <p className="mb-4 text-[13px] text-text-secondary">
                  Connect your Google account to enable automatic daily backups to
                  Google Drive. Backups are stored in an{" "}
                  <strong className="text-text-primary">Envel Backup</strong> folder,
                  keeping the last 7 copies.
                </p>
                <button
                  onClick={() => {
                    window.location.href = "/api/backup/google/connect"
                  }}
                  className="inline-flex items-center gap-2 rounded-md border border-border bg-bg-elevated px-4 py-2 text-[13px] font-semibold text-text-primary transition-colors hover:bg-bg-muted"
                >
                  <svg width="15" height="15" viewBox="0 0 48 48">
                    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
                  </svg>
                  Connect Google Drive
                </button>
              </>
            )}
          </div>
    </>
  )
}

function MorningBriefingCard() {
  const { briefing, isLoading } = useMorningBriefing()
  const update = useUpdateMorningBriefing()

  const [draft, setDraft] = useState("")
  useEffect(() => {
    if (briefing?.prompt !== undefined) setDraft(briefing.prompt ?? "")
  }, [briefing?.prompt])

  const enabled = briefing?.enabled ?? true
  const dirty = (briefing?.prompt ?? "") !== draft

  return (
    <div className="mt-6 rounded-xl border border-border bg-card p-5 shadow-xs">
      <div className="mb-4 flex items-start justify-between gap-3.5">
        <div className="flex items-start gap-3.5">
          <div
            className="flex size-10 items-center justify-center rounded-lg text-xl"
            style={{ background: "oklch(94% 0.05 50 / 0.7)" }}
          >
            🌅
          </div>
          <div>
            <p className="font-heading text-sm font-bold text-text-primary">
              Morning Briefing
            </p>
            <p className="text-[12.5px] text-text-muted">
              Daily check-in fired the first time you chat with Claude each day
            </p>
          </div>
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          disabled={isLoading || update.isPending}
          onClick={() => update.mutate({ enabled: !enabled })}
          className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
            enabled ? "bg-brand" : "bg-bg-muted"
          }`}
        >
          <span
            className={`inline-block size-4 transform rounded-full bg-white shadow transition-transform ${
              enabled ? "translate-x-[18px]" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      {enabled && (
        <>
          <div className="mb-2 flex items-center justify-between">
            <label
              htmlFor="briefing-prompt"
              className="text-[12.5px] font-semibold text-text-secondary"
            >
              Briefing instruction
            </label>
            {briefing?.last_shown && (
              <span className="text-[11px] text-text-muted">
                Last shown:{" "}
                {new Date(briefing.last_shown).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
            )}
          </div>
          <textarea
            id="briefing-prompt"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={4}
            placeholder="e.g. Cek apakah envelope Makan dan Transport udah lewat 80% dari budget bulan ini, dan recap total pengeluaran kemarin."
            className="w-full rounded-md border border-border bg-bg px-3 py-2 text-[13px] text-text-primary placeholder:text-text-placeholder focus:border-brand focus:outline-none"
          />
          <p className="mt-1.5 text-[11.5px] text-text-muted">
            Plain English description of what you want each morning. Claude will
            figure out which tools to call.
          </p>

          <div className="mt-3 flex items-center gap-2.5">
            <button
              type="button"
              disabled={!dirty || update.isPending}
              onClick={() =>
                update.mutate(
                  draft.trim()
                    ? { prompt: draft }
                    : { clear_prompt: true }
                )
              }
              className="inline-flex items-center gap-1.5 rounded-md bg-brand px-4 py-2 text-[13px] font-semibold text-white transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {update.isPending ? "Saving…" : "Save"}
            </button>
            {briefing?.prompt && (
              <button
                type="button"
                onClick={() => {
                  setDraft("")
                  update.mutate({ clear_prompt: true })
                }}
                className="text-[12px] font-medium text-text-muted hover:text-text-secondary"
              >
                Clear prompt
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

interface UserProfile {
  username: string
  name: string | null
  email: string | null
}

function AccountCard() {
  const { username, name, email, hasPassword, refreshSession } = useAuth()

  const [draftName, setDraftName] = useState(name ?? "")
  const [draftEmail, setDraftEmail] = useState(email ?? "")
  const [profileError, setProfileError] = useState<string | null>(null)
  const [profileSavedAt, setProfileSavedAt] = useState<number | null>(null)

  useEffect(() => {
    setDraftName(name ?? "")
  }, [name])
  useEffect(() => {
    setDraftEmail(email ?? "")
  }, [email])

  const updateProfile = useMutation({
    mutationFn: (body: { name?: string; email?: string }) =>
      api<UserProfile>("/api/auth/me", {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: async () => {
      setProfileError(null)
      setProfileSavedAt(Date.now())
      await refreshSession()
    },
    onError: (err: Error) => setProfileError(err.message),
  })

  const profileDirty =
    (draftName.trim() !== (name ?? "")) || (draftEmail.trim().toLowerCase() !== (email ?? ""))

  const handleProfileSave = () => {
    setProfileError(null)
    const body: { name?: string; email?: string } = {}
    if (draftName.trim() !== (name ?? "")) body.name = draftName.trim()
    if (draftEmail.trim().toLowerCase() !== (email ?? "")) body.email = draftEmail.trim()
    if (Object.keys(body).length === 0) return
    updateProfile.mutate(body)
  }

  // Password form
  const [currentPw, setCurrentPw] = useState("")
  const [newPw, setNewPw] = useState("")
  const [confirmPw, setConfirmPw] = useState("")
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSavedAt, setPwSavedAt] = useState<number | null>(null)

  const changePassword = useMutation({
    mutationFn: (body: { current_password: string | null; new_password: string }) =>
      api<{ ok: true }>("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: async () => {
      setPwError(null)
      setPwSavedAt(Date.now())
      setCurrentPw("")
      setNewPw("")
      setConfirmPw("")
      await refreshSession()
    },
    onError: (err: Error) => setPwError(err.message),
  })

  const handlePasswordSave = () => {
    setPwError(null)
    if (hasPassword && !currentPw) {
      setPwError("Please enter your current password.")
      return
    }
    if (!newPw) {
      setPwError("Please enter a new password.")
      return
    }
    if (newPw !== confirmPw) {
      setPwError("New password and confirmation don't match.")
      return
    }
    changePassword.mutate({
      current_password: hasPassword ? currentPw : null,
      new_password: newPw,
    })
  }

  const inputClass =
    "w-full rounded-md border border-border bg-bg px-3 py-2 text-[13px] text-text-primary placeholder:text-text-placeholder focus:border-brand focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"

  return (
    <div className="mt-6 rounded-xl border border-border bg-card p-5 shadow-xs">
      <div className="mb-4 flex items-start gap-3.5">
        <div
          className="flex size-10 items-center justify-center rounded-lg text-text-secondary"
          style={{ background: "oklch(94% 0.05 145 / 0.4)" }}
        >
          <User className="size-5" />
        </div>
        <div>
          <p className="font-heading text-sm font-bold text-text-primary">Account</p>
          <p className="text-[12.5px] text-text-muted">
            Update your display name, email, and password
          </p>
        </div>
      </div>

      {/* Username (read-only) */}
      <div className="mb-3.5">
        <label className="mb-1 block text-[12.5px] font-semibold text-text-secondary">
          Username
        </label>
        <input value={username ?? ""} disabled className={inputClass} />
        <p className="mt-1 text-[11.5px] text-text-muted">
          Username can't be changed.
        </p>
      </div>

      {/* Display name */}
      <div className="mb-3.5">
        <label className="mb-1 block text-[12.5px] font-semibold text-text-secondary">
          Display name
        </label>
        <input
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          className={inputClass}
        />
      </div>

      {/* Email */}
      <div className="mb-3.5">
        <label className="mb-1 block text-[12.5px] font-semibold text-text-secondary">
          Email
        </label>
        <input
          type="email"
          value={draftEmail}
          onChange={(e) => setDraftEmail(e.target.value)}
          className={inputClass}
        />
      </div>

      <div className="flex items-center gap-2.5">
        <button
          type="button"
          disabled={!profileDirty || updateProfile.isPending}
          onClick={handleProfileSave}
          className="inline-flex items-center gap-1.5 rounded-md bg-brand px-4 py-2 text-[13px] font-semibold text-white transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {updateProfile.isPending ? "Saving…" : "Save profile"}
        </button>
        {profileSavedAt && !profileDirty && !updateProfile.isPending && (
          <span className="text-[12px] text-[color:var(--success)]">Saved.</span>
        )}
      </div>
      {profileError && (
        <p className="mt-2 text-[12px] text-[color:var(--danger)]">{profileError}</p>
      )}

      <div className="my-5 border-t border-border" />

      {/* Password */}
      <p className="mb-1 text-[13px] font-semibold text-text-primary">
        {hasPassword ? "Change password" : "Set a password"}
      </p>
      {!hasPassword && (
        <p className="mb-3 text-[12px] text-text-muted">
          You signed in with Google. Setting a password lets you sign in with your username and
          password too.
        </p>
      )}

      {hasPassword && (
        <div className="mb-3.5">
          <label className="mb-1 block text-[12.5px] font-semibold text-text-secondary">
            Current password
          </label>
          <input
            type="password"
            value={currentPw}
            onChange={(e) => setCurrentPw(e.target.value)}
            autoComplete="current-password"
            className={inputClass}
          />
        </div>
      )}
      <div className="mb-3.5">
        <label className="mb-1 block text-[12.5px] font-semibold text-text-secondary">
          New password
        </label>
        <input
          type="password"
          value={newPw}
          onChange={(e) => setNewPw(e.target.value)}
          autoComplete="new-password"
          className={inputClass}
        />
        <p className="mt-1 text-[11.5px] text-text-muted">
          At least 8 characters, with one letter and one number.
        </p>
      </div>
      <div className="mb-3.5">
        <label className="mb-1 block text-[12.5px] font-semibold text-text-secondary">
          Confirm new password
        </label>
        <input
          type="password"
          value={confirmPw}
          onChange={(e) => setConfirmPw(e.target.value)}
          autoComplete="new-password"
          className={inputClass}
        />
      </div>
      <div className="flex items-center gap-2.5">
        <button
          type="button"
          disabled={changePassword.isPending}
          onClick={handlePasswordSave}
          className="inline-flex items-center gap-1.5 rounded-md bg-brand px-4 py-2 text-[13px] font-semibold text-white transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {changePassword.isPending
            ? hasPassword
              ? "Updating…"
              : "Saving…"
            : hasPassword
              ? "Update password"
              : "Set password"}
        </button>
        {pwSavedAt && !changePassword.isPending && (
          <span className="text-[12px] text-[color:var(--success)]">
            {hasPassword ? "Password updated." : "Password set."}
          </span>
        )}
      </div>
      {pwError && <p className="mt-2 text-[12px] text-[color:var(--danger)]">{pwError}</p>}
    </div>
  )
}

import { useEffect, useState, type FormEvent } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { Check, Loader2, X } from "lucide-react"
import { LogoMark } from "@/components/shared/LogoMark"
import { useAuth } from "@/hooks/useAuth"

const USERNAME_RE = /^[a-zA-Z0-9_-]{3,32}$/

interface PendingInfo {
  google_email: string
  google_name: string
  suggested_username: string
}

type UsernameStatus =
  | { state: "idle" }
  | { state: "invalid" }
  | { state: "checking" }
  | { state: "available" }
  | { state: "taken" }
  | { state: "error" }

export function SignupConfirmForm() {
  const { markAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token") ?? ""

  const [pending, setPending] = useState<PendingInfo | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [username, setUsername] = useState("")
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [usernameStatus, setUsernameStatus] = useState<UsernameStatus>({ state: "idle" })

  // Fetch pending Google info on mount
  useEffect(() => {
    if (!token) {
      setLoadError("Missing signup token. Please try again.")
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(
          `/api/auth/google-pending?token=${encodeURIComponent(token)}`,
          { credentials: "include" },
        )
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          if (!cancelled) {
            setLoadError(body?.detail ?? "Signup session expired.")
          }
          return
        }
        const data: PendingInfo = await res.json()
        if (!cancelled) {
          setPending(data)
          setUsername(data.suggested_username)
        }
      } catch {
        if (!cancelled) setLoadError("Couldn't load signup session.")
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  // Debounced availability check
  useEffect(() => {
    const u = username.trim()
    if (!u) {
      setUsernameStatus({ state: "idle" })
      return
    }
    if (!USERNAME_RE.test(u)) {
      setUsernameStatus({ state: "invalid" })
      return
    }
    // Skip check if this is the originally suggested one (already known available)
    if (pending && u === pending.suggested_username) {
      setUsernameStatus({ state: "available" })
      return
    }
    setUsernameStatus({ state: "checking" })
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          `/api/auth/username-available?u=${encodeURIComponent(u)}`,
          { signal: controller.signal, credentials: "include" },
        )
        const data = await res.json()
        setUsernameStatus({ state: data.available ? "available" : "taken" })
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setUsernameStatus({ state: "error" })
        }
      }
    }, 400)
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [username, pending])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitError(null)
    if (usernameStatus.state !== "available") return
    setSubmitting(true)
    try {
      const res = await fetch("/api/auth/google-signup-complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ token, username: username.trim() }),
      })
      if (res.ok) {
        const data = await res.json()
        markAuthenticated(data.username)
        navigate("/connect")
        return
      }
      const err = await res.json().catch(() => null)
      if (err?.field === "username" && err?.code === "taken") {
        setUsernameStatus({ state: "taken" })
      }
      setSubmitError(err?.detail ?? "Signup failed")
    } catch {
      setSubmitError("Cannot connect to server")
    } finally {
      setSubmitting(false)
    }
  }

  // ── Error state (bad/expired token) ──
  if (loadError) {
    return (
      <div className="flex w-[400px] max-w-full flex-col items-center">
        <div
          className="w-full rounded-[18px] border border-border bg-card p-7 text-center"
          style={{ boxShadow: "var(--shadow-md, 0 4px 16px rgb(0 0 0 / 0.1))" }}
        >
          <h1 className="font-heading text-[20px] font-extrabold text-text-primary">
            Signup session expired
          </h1>
          <p className="mt-2 text-[13.5px] text-text-muted">{loadError}</p>
          <Link
            to="/signup"
            className="mt-5 inline-flex w-full items-center justify-center rounded-[10px] py-2.5 text-[14.5px] font-bold text-white"
            style={{
              background: "var(--brand)",
              boxShadow: "0 2px 8px oklch(50% 0.16 145 / 0.3)",
            }}
          >
            Start over
          </Link>
        </div>
      </div>
    )
  }

  // ── Loading state ──
  if (!pending) {
    return (
      <div className="flex min-h-[240px] items-center justify-center">
        <Loader2 className="size-5 animate-spin text-text-muted" />
      </div>
    )
  }

  const canSubmit = usernameStatus.state === "available" && !submitting

  return (
    <div className="flex w-[400px] max-w-full flex-col items-center">
      <div className="mb-7 flex flex-col items-center gap-3">
        <div
          className="flex size-[52px] items-center justify-center rounded-2xl"
          style={{
            background: "var(--brand)",
            boxShadow: "0 8px 24px oklch(50% 0.16 145 / 0.35)",
          }}
        >
          <LogoMark size={52} className="rounded-2xl" />
        </div>
        <div className="text-center">
          <div className="font-heading text-[22px] font-extrabold text-text-primary">
            One last step, {pending.google_name.split(" ")[0]}
          </div>
          <div className="mt-1 text-[13.5px] text-text-muted">
            Pick a username for your Envel account.
          </div>
        </div>
      </div>

      <div
        className="w-full rounded-[18px] border border-border bg-card p-7 pb-6"
        style={{ boxShadow: "var(--shadow-md, 0 4px 16px rgb(0 0 0 / 0.1))" }}
      >
        <div className="mb-4 flex items-center justify-between gap-3 rounded-[10px] bg-bg-muted px-3.5 py-2.5">
          <div className="min-w-0">
            <div className="text-[11.5px] font-semibold uppercase tracking-wide text-text-muted">
              Signed in as
            </div>
            <div className="truncate text-[13.5px] font-semibold text-text-primary">
              {pending.google_email}
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="username"
              className="mb-1.5 block text-[12.5px] font-semibold text-text-secondary"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={submitting}
              placeholder="your_username"
              className="w-full rounded-[10px] border-[1.5px] border-border bg-bg px-3.5 py-2.5 text-sm text-text-primary placeholder:text-text-placeholder transition-colors focus:border-brand focus:outline-none disabled:opacity-60"
            />
            <UsernameHint status={usernameStatus} raw={username} />
          </div>

          {submitError && (
            <p className="text-[12.5px] font-medium text-[color:var(--danger)]">
              {submitError}
            </p>
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="mt-1 inline-flex w-full items-center justify-center gap-2 rounded-[10px] py-2.5 text-[14.5px] font-bold text-white transition-all disabled:cursor-not-allowed disabled:opacity-60"
            style={{
              background: submitting ? "var(--brand-hover)" : "var(--brand)",
              boxShadow: "0 2px 8px oklch(50% 0.16 145 / 0.3)",
            }}
          >
            {submitting && <Loader2 className="size-4 animate-spin" />}
            {submitting ? "Creating account…" : "Continue"}
          </button>
        </form>
      </div>
    </div>
  )
}

function UsernameHint({ status, raw }: { status: UsernameStatus; raw: string }) {
  if (!raw) return null
  if (status.state === "invalid") {
    return (
      <p className="mt-1 text-[11.5px] font-medium text-[color:var(--danger)]">
        3–32 chars: letters, numbers, underscore, dash.
      </p>
    )
  }
  if (status.state === "checking") {
    return (
      <p className="mt-1 flex items-center gap-1 text-[11.5px] font-medium text-text-muted">
        <Loader2 className="size-3 animate-spin" />
        Checking availability…
      </p>
    )
  }
  if (status.state === "available") {
    return (
      <p
        className="mt-1 flex items-center gap-1 text-[11.5px] font-medium"
        style={{ color: "var(--brand-text)" }}
      >
        <Check className="size-3.5" />
        Username available.
      </p>
    )
  }
  if (status.state === "taken") {
    return (
      <p className="mt-1 flex items-center gap-1 text-[11.5px] font-medium text-[color:var(--danger)]">
        <X className="size-3.5" />
        This username is already taken.
      </p>
    )
  }
  if (status.state === "error") {
    return (
      <p className="mt-1 text-[11.5px] font-medium text-[color:var(--danger)]">
        Couldn't check availability. Retry.
      </p>
    )
  }
  return null
}

import { useEffect, useMemo, useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Check, Loader2, X } from "lucide-react"
import { LogoMark } from "@/components/shared/LogoMark"
import { useAuth } from "@/hooks/useAuth"

const USERNAME_RE = /^[a-zA-Z0-9_-]{3,32}$/
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

type UsernameStatus =
  | { state: "idle" }
  | { state: "invalid" }
  | { state: "checking" }
  | { state: "available" }
  | { state: "taken" }
  | { state: "error" }

function Rule({ ok, text }: { ok: boolean; text: string }) {
  return (
    <div
      className="flex items-center gap-1.5 text-[11.5px]"
      style={{ color: ok ? "var(--brand-text)" : "var(--text-muted)" }}
    >
      {ok ? <Check className="size-3.5" /> : <X className="size-3.5" />}
      <span>{text}</span>
    </div>
  )
}

export function SignupForm() {
  const { signup } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // ── Live field validation ──
  const emailLooksValid = EMAIL_RE.test(email.trim())
  const usernameFormatValid = USERNAME_RE.test(username.trim())
  const pwLongEnough = password.length >= 8
  const pwHasLetter = /[A-Za-z]/.test(password)
  const pwHasNumber = /\d/.test(password)
  const pwValid = pwLongEnough && pwHasLetter && pwHasNumber
  const confirmMatches = confirm.length > 0 && confirm === password

  // ── Debounced username availability check ──
  const [usernameStatus, setUsernameStatus] = useState<UsernameStatus>({ state: "idle" })

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
  }, [username])

  const formValid = useMemo(() => {
    return (
      name.trim().length > 0 &&
      emailLooksValid &&
      usernameFormatValid &&
      usernameStatus.state === "available" &&
      pwValid &&
      confirmMatches
    )
  }, [name, emailLooksValid, usernameFormatValid, usernameStatus, pwValid, confirmMatches])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitError(null)
    if (!formValid) return
    setSubmitting(true)
    const result = await signup({
      name: name.trim(),
      email: email.trim(),
      username: username.trim(),
      password,
    })
    setSubmitting(false)
    if (result.ok) {
      navigate("/connect")
      return
    }
    if (result.field === "username" && result.code === "taken") {
      setUsernameStatus({ state: "taken" })
    }
    setSubmitError(result.error ?? "Signup failed")
  }

  function startGoogleSignup() {
    window.location.href = "/api/auth/google-start?intent=signup"
  }

  return (
    <div className="flex w-[400px] max-w-full flex-col items-center">
      {/* Logo + title */}
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
            Create your Envel account
          </div>
          <div className="mt-1 text-[13.5px] text-text-muted">
            Free forever. No credit card required.
          </div>
        </div>
      </div>

      {/* Form card */}
      <div
        className="w-full rounded-[18px] border border-border bg-card p-7 pb-6"
        style={{ boxShadow: "var(--shadow-md, 0 4px 16px rgb(0 0 0 / 0.1))" }}
      >
        {/* Google button */}
        <button
          type="button"
          onClick={startGoogleSignup}
          className="mb-4 flex w-full items-center justify-center gap-2.5 rounded-[10px] border-[1.5px] border-border bg-bg-elevated px-3.5 py-2.5 text-sm font-semibold text-text-primary transition-colors hover:bg-bg-muted hover:border-text-muted"
        >
          <GoogleIcon />
          Continue with Google
        </button>

        <div className="my-3 flex items-center gap-2.5 text-[12px] font-medium text-text-muted">
          <span className="h-px flex-1 bg-border" />
          <span>or</span>
          <span className="h-px flex-1 bg-border" />
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Name */}
          <Field label="Name" htmlFor="name">
            <input
              id="name"
              type="text"
              required
              autoComplete="name"
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={submitting}
              placeholder="Your name"
              className={inputClass}
            />
          </Field>

          {/* Email */}
          <Field label="Email" htmlFor="email">
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
              placeholder="you@example.com"
              className={inputClass}
            />
            {email.length > 0 && !emailLooksValid && (
              <FieldError>Please enter a valid email address.</FieldError>
            )}
          </Field>

          {/* Username */}
          <Field label="Username" htmlFor="username">
            <input
              id="username"
              type="text"
              required
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={submitting}
              placeholder="your_username"
              className={inputClass}
            />
            <UsernameHint status={usernameStatus} raw={username} />
          </Field>

          {/* Password */}
          <Field label="Password" htmlFor="password">
            <input
              id="password"
              type="password"
              required
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
              placeholder="••••••••"
              className={inputClass}
            />
            {password.length > 0 && (
              <div className="mt-1.5 flex flex-col gap-0.5">
                <Rule ok={pwLongEnough} text="At least 8 characters" />
                <Rule ok={pwHasLetter} text="Contains a letter" />
                <Rule ok={pwHasNumber} text="Contains a number" />
              </div>
            )}
          </Field>

          {/* Confirm password */}
          <Field label="Confirm password" htmlFor="confirm">
            <input
              id="confirm"
              type="password"
              required
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              disabled={submitting}
              placeholder="••••••••"
              className={inputClass}
            />
            {confirm.length > 0 && !confirmMatches && (
              <FieldError>Passwords don't match.</FieldError>
            )}
          </Field>

          {submitError && (
            <p className="text-[12.5px] font-medium text-[color:var(--danger)]">
              {submitError}
            </p>
          )}

          <button
            type="submit"
            disabled={!formValid || submitting}
            className="mt-1 inline-flex w-full items-center justify-center gap-2 rounded-[10px] py-2.5 text-[14.5px] font-bold text-white transition-all disabled:cursor-not-allowed disabled:opacity-60"
            style={{
              background: submitting ? "var(--brand-hover)" : "var(--brand)",
              boxShadow: "0 2px 8px oklch(50% 0.16 145 / 0.3)",
            }}
          >
            {submitting && <Loader2 className="size-4 animate-spin" />}
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>
      </div>

      <p className="mt-5 text-[13px] text-text-muted">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-brand-text hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  )
}

const inputClass =
  "w-full rounded-[10px] border-[1.5px] border-border bg-bg px-3.5 py-2.5 text-sm text-text-primary placeholder:text-text-placeholder transition-colors focus:border-brand focus:outline-none disabled:opacity-60"

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string
  htmlFor: string
  children: React.ReactNode
}) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-[12.5px] font-semibold text-text-secondary"
      >
        {label}
      </label>
      {children}
    </div>
  )
}

function FieldError({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-1 text-[11.5px] font-medium text-[color:var(--danger)]">
      {children}
    </p>
  )
}

function UsernameHint({ status, raw }: { status: UsernameStatus; raw: string }) {
  if (!raw) return null
  if (status.state === "invalid") {
    return (
      <FieldError>3–32 chars: letters, numbers, underscore, dash.</FieldError>
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
    return <FieldError>This username is already taken.</FieldError>
  }
  if (status.state === "error") {
    return <FieldError>Couldn't check availability. Retry.</FieldError>
  }
  return null
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
      />
      <path
        fill="#FBBC05"
        d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
      />
    </svg>
  )
}

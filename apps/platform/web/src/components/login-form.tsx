import { useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { LogoMark } from "@/components/shared/LogoMark"
import { useAuth } from "@/hooks/useAuth"

export function LoginForm() {
  const { login } = useAuth()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const result = await login(username, password)
    if (!result.ok) setError(result.error ?? "Login failed")
    setLoading(false)
  }

  function startGoogleLogin() {
    window.location.href = "/api/auth/google-start?intent=login"
  }

  return (
    <div className="flex w-[380px] max-w-full flex-col items-center">
      {/* Logo + title */}
      <div className="mb-7 flex flex-col items-center gap-3">
        <div
          className="flex size-[52px] items-center justify-center rounded-2xl text-xl font-extrabold text-white"
          style={{
            background: "var(--brand)",
            boxShadow: "0 8px 24px oklch(50% 0.16 145 / 0.35)",
          }}
        >
          <LogoMark size={52} className="rounded-2xl" />
        </div>
        <div className="text-center">
          <div className="font-heading text-[22px] font-extrabold text-text-primary">
            Welcome back
          </div>
          <div className="mt-1 text-[13.5px] text-text-muted">
            Sign in to your Envel account
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
          onClick={startGoogleLogin}
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
              disabled={loading}
              placeholder="Your username"
              className="w-full rounded-[10px] border-[1.5px] border-border bg-bg px-3.5 py-2.5 text-sm text-text-primary placeholder:text-text-placeholder transition-colors focus:border-brand focus:outline-none disabled:opacity-60"
            />
          </div>
          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-[12.5px] font-semibold text-text-secondary"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              placeholder="••••••••"
              className="w-full rounded-[10px] border-[1.5px] border-border bg-bg px-3.5 py-2.5 text-sm text-text-primary placeholder:text-text-placeholder transition-colors focus:border-brand focus:outline-none disabled:opacity-60"
            />
          </div>

          {error && (
            <p className="text-[12.5px] font-medium text-[color:var(--danger)]">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-1 inline-flex w-full items-center justify-center gap-2 rounded-[10px] py-2.5 text-[14.5px] font-bold text-white transition-all disabled:cursor-wait"
            style={{
              background: loading ? "var(--brand-hover)" : "var(--brand)",
              boxShadow: "0 2px 8px oklch(50% 0.16 145 / 0.3)",
            }}
          >
            {loading && <Loader2 className="size-4 animate-spin" />}
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>

      <p className="mt-5 text-[13px] text-text-muted">
        Don't have an account?{" "}
        <Link to="/signup" className="font-semibold hover:underline" style={{ color: "var(--brand-text)" }}>
          Sign up
        </Link>
      </p>
    </div>
  )
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

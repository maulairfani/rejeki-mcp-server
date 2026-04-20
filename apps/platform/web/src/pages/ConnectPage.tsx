import { useEffect, useRef, useState } from "react"
import { Check, Copy, ExternalLink } from "lucide-react"
import { LogoMark } from "@/components/shared/LogoMark"
import { useAuth } from "@/hooks/useAuth"

const MCP_URL = "https://envel.dev/mcp"
const CLAUDE_CONNECTORS_URL = "https://claude.ai/settings/connectors?modal=add-custom-connector"
const CLAUDE_NEW_URL = "https://claude.ai/new"
const SUGGESTED_PHRASE = "Help me set up my envelope budget"
const POLL_INTERVAL_MS = 4000

export function ConnectPage() {
  const { username } = useAuth()
  const [urlCopied, setUrlCopied] = useState(false)
  const [phraseCopied, setPhraseCopied] = useState(false)
  const [connected, setConnected] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let stopped = false

    async function check() {
      try {
        const res = await fetch("/api/auth/me/connection-status", { credentials: "include" })
        if (res.ok) {
          const data = await res.json()
          if (data.connected && !stopped) {
            setConnected(true)
            if (pollRef.current) clearInterval(pollRef.current)
          }
        }
      } catch {
        // silently ignore — backend may not be running in dev
      }
    }

    check()
    pollRef.current = setInterval(check, POLL_INTERVAL_MS)
    return () => {
      stopped = true
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  function copyUrl() {
    navigator.clipboard.writeText(MCP_URL).then(() => {
      setUrlCopied(true)
      setTimeout(() => setUrlCopied(false), 2000)
    })
  }

  function copyPhrase() {
    navigator.clipboard.writeText(SUGGESTED_PHRASE).then(() => {
      setPhraseCopied(true)
      setTimeout(() => setPhraseCopied(false), 2000)
    })
  }

  if (connected) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center bg-bg px-4 py-12">
        <div className="flex w-full max-w-[420px] flex-col items-center text-center">
          <div
            className="mb-6 flex size-[72px] items-center justify-center rounded-full"
            style={{ background: "oklch(94% 0.05 145)", border: "3px solid var(--brand)" }}
          >
            <Check className="size-9" style={{ color: "var(--brand)" }} strokeWidth={2.5} />
          </div>
          <h1 className="font-heading text-[24px] font-extrabold text-text-primary">
            You're connected!
          </h1>
          <p className="mt-2 text-[14px] text-text-muted">
            Envel is now connected to Claude. Start chatting to manage your budget.
          </p>
          <a
            href="/envelopes"
            className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-[12px] py-3 text-[15px] font-bold text-white"
            style={{
              background: "var(--brand)",
              boxShadow: "0 4px 16px oklch(50% 0.16 145 / 0.35)",
            }}
          >
            Go to Dashboard →
          </a>
          <a
            href={CLAUDE_NEW_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-[12px] border-[1.5px] border-border py-3 text-[15px] font-bold text-text-primary"
          >
            Open Claude
            <ExternalLink className="size-3.5" />
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-bg px-4 py-12">
      {/* Logo + heading */}
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <div
          className="flex size-[52px] items-center justify-center rounded-2xl"
          style={{
            background: "var(--brand)",
            boxShadow: "0 8px 24px oklch(50% 0.16 145 / 0.35)",
          }}
        >
          <LogoMark size={52} className="rounded-2xl" />
        </div>
        <div>
          <h1 className="font-heading text-[22px] font-extrabold text-text-primary">
            Connect your MCP client
          </h1>
          <p className="mt-1 text-[13.5px] text-text-muted">
            {username ? `Hi ${username} — ` : ""}Add Envel to Claude to start budgeting with AI.
          </p>
        </div>
      </div>

      <div className="w-full max-w-[460px] space-y-3">
        {/* Client picker */}
        <div
          className="rounded-[18px] border border-border bg-card p-5"
          style={{ boxShadow: "var(--shadow-md, 0 4px 16px rgb(0 0 0 / 0.08))" }}
        >
          <p className="mb-3 text-[11.5px] font-semibold uppercase tracking-wide text-text-muted">
            Select client
          </p>
          <div className="grid grid-cols-3 gap-2">
            {/* Claude — active */}
            <div
              className="flex flex-col items-center gap-2 rounded-[10px] border-[1.5px] px-3 py-3 text-center"
              style={{
                borderColor: "var(--brand)",
                background: "oklch(97% 0.02 145)",
              }}
            >
              <ClaudeIcon />
              <div>
                <div className="text-[12.5px] font-bold text-text-primary">Claude</div>
                <div
                  className="mt-0.5 text-[10.5px] font-semibold"
                  style={{ color: "var(--brand-text)" }}
                >
                  Supported
                </div>
              </div>
            </div>

            {/* Cursor — coming soon */}
            <ComingSoonClient label="Cursor" icon={<CursorIcon />} />

            {/* ChatGPT — coming soon */}
            <ComingSoonClient label="ChatGPT" icon={<ChatGPTIcon />} />
          </div>
        </div>

        {/* Step 1: Copy MCP URL */}
        <StepCard step={1} title="Copy your MCP URL">
          <div className="mt-3 flex items-center gap-2 rounded-[10px] border border-border bg-bg px-3.5 py-2.5">
            <span className="flex-1 truncate font-mono text-[12.5px] text-text-secondary">
              {MCP_URL}
            </span>
            <button
              onClick={copyUrl}
              className="flex shrink-0 items-center gap-1.5 rounded-[7px] px-2.5 py-1.5 text-[12px] font-semibold transition-colors"
              style={{
                background: urlCopied ? "oklch(97% 0.02 145)" : "var(--bg-muted)",
                color: urlCopied ? "var(--brand-text)" : "var(--text-secondary)",
              }}
            >
              {urlCopied ? (
                <>
                  <Check className="size-3.5" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="size-3.5" />
                  Copy
                </>
              )}
            </button>
          </div>
        </StepCard>

        {/* Step 2: Open Claude Settings */}
        <StepCard step={2} title="Add connector in Claude Settings">
          <p className="mt-1.5 text-[13px] text-text-muted">
            Go to{" "}
            <span className="font-medium text-text-secondary">
              Settings → Connectors → Add connector
            </span>
            , then paste the URL above.
          </p>
          <a
            href={CLAUDE_CONNECTORS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-[10px] py-2.5 text-[14px] font-bold text-white transition-opacity hover:opacity-90"
            style={{
              background: "var(--brand)",
              boxShadow: "0 2px 8px oklch(50% 0.16 145 / 0.3)",
            }}
          >
            Open Claude Settings
            <ExternalLink className="size-3.5" />
          </a>
        </StepCard>

        {/* Step 3: Start chatting */}
        <StepCard step={3} title="Start your first budget session">
          <p className="mt-1.5 text-[13px] text-text-muted">
            Open Claude and try saying:
          </p>
          <div className="mt-2.5 flex items-center gap-2 rounded-[10px] border border-border bg-bg px-3.5 py-2.5">
            <span className="flex-1 text-[13px] font-medium italic text-text-secondary">
              "{SUGGESTED_PHRASE}"
            </span>
            <button
              onClick={copyPhrase}
              className="flex shrink-0 items-center gap-1.5 rounded-[7px] px-2.5 py-1.5 text-[12px] font-semibold transition-colors"
              style={{
                background: phraseCopied ? "oklch(97% 0.02 145)" : "var(--bg-muted)",
                color: phraseCopied ? "var(--brand-text)" : "var(--text-secondary)",
              }}
            >
              {phraseCopied ? (
                <>
                  <Check className="size-3.5" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="size-3.5" />
                  Copy
                </>
              )}
            </button>
          </div>
          <a
            href={CLAUDE_NEW_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-[10px] border-[1.5px] border-border bg-bg-elevated py-2.5 text-[14px] font-bold text-text-primary transition-colors hover:bg-bg-muted"
          >
            Open Claude
            <ExternalLink className="size-3.5" />
          </a>
        </StepCard>
      </div>

      {/* Skip link */}
      <p className="mt-6 text-[13px] text-text-muted">
        Already connected?{" "}
        <a
          href="/envelopes"
          className="font-semibold hover:underline"
          style={{ color: "var(--brand-text)" }}
        >
          Go to dashboard →
        </a>
      </p>
    </div>
  )
}

function StepCard({
  step,
  title,
  children,
}: {
  step: number
  title: string
  children: React.ReactNode
}) {
  return (
    <div
      className="rounded-[18px] border border-border bg-card px-5 py-4"
      style={{ boxShadow: "var(--shadow-md, 0 4px 16px rgb(0 0 0 / 0.08))" }}
    >
      <div className="flex items-center gap-2.5">
        <div
          className="flex size-6 shrink-0 items-center justify-center rounded-full text-[11.5px] font-bold text-white"
          style={{ background: "var(--brand)" }}
        >
          {step}
        </div>
        <span className="text-[14px] font-bold text-text-primary">{title}</span>
      </div>
      {children}
    </div>
  )
}

function ComingSoonClient({ label, icon }: { label: string; icon: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-[10px] border-[1.5px] border-border px-3 py-3 text-center opacity-40">
      {icon}
      <div>
        <div className="text-[12.5px] font-bold text-text-primary">{label}</div>
        <div className="mt-0.5 text-[10.5px] font-semibold text-text-muted">Coming soon</div>
      </div>
    </div>
  )
}

function ClaudeIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect width="24" height="24" rx="6" fill="#D97757" />
      <path
        d="M9.5 16.5L7 8.5h1.5l1.8 6.2 1.8-6.2H13.5L11 16.5H9.5z"
        fill="white"
        opacity="0"
      />
      {/* Anthropic/Claude simplified "A" shape */}
      <path
        d="M8 16l4-9 4 9M9.5 13h5"
        stroke="white"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CursorIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <rect width="28" height="28" rx="7" fill="#1A1A1A" />
      <path d="M14 6L22 10V18L14 22L6 18V10L14 6Z" stroke="white" strokeWidth="1.4" fill="none" />
      <path d="M14 6V22M6 10L22 18M22 10L6 18" stroke="white" strokeWidth="1.4" opacity="0.4" />
    </svg>
  )
}

function ChatGPTIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <rect width="28" height="28" rx="7" fill="#10A37F" />
      <path
        d="M14 7a5 5 0 0 1 4.8 6.4A4 4 0 0 1 20.5 17a4 4 0 0 1-3.7 2.5c-.3 0-.6 0-.9-.1A5 5 0 0 1 9.1 17c-.2-.4-.4-.8-.4-1.2A4 4 0 0 1 7 12.5 4 4 0 0 1 9.3 9a5 5 0 0 1 4.7-2z"
        stroke="white"
        strokeWidth="1.3"
        fill="none"
      />
      <circle cx="14" cy="14" r="2" fill="white" opacity="0.9" />
    </svg>
  )
}

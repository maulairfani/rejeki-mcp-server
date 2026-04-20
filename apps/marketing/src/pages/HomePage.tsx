import { useNavigate } from "react-router-dom"
import { AILogos } from "@/components/AILogos"
import { ChatMockup, type ChatMessage } from "@/components/ChatMockup"
import { FeatureCard } from "@/components/FeatureCard"
import { MethodCard } from "@/components/MethodCard"
import {
  IconApp,
  IconChat,
  IconEnvelope,
  IconPrompt,
  IconSeedling,
  IconStack,
  IconSun,
  IconSwap,
  IconWallet,
} from "@/components/icons"

const HERO_MESSAGES: ChatMessage[] = [
  { role: "user", text: "I just spent 85k on groceries" },
  {
    role: "bot",
    text: "Got it! Logged Rp 85,000 from your Food envelope. You have Rp 215,000 remaining this month.",
  },
  { role: "user", text: "How's my budget looking overall?" },
  {
    role: "bot",
    text: "You're doing well! 3 envelopes on track, 1 running low (Transport). Want me to move some funds?",
  },
]

const DEMO_MESSAGES: ChatMessage[] = [
  { role: "user", text: "I spent 50k on transport today, GoPay" },
  {
    role: "bot",
    text: "Logged! Rp 50,000 from Transport envelope via GoPay. You have Rp 150,000 left for transport this week.",
  },
  { role: "user", text: "Move 100k from my Food envelope to Transport" },
  {
    role: "bot",
    text: "Done. Moved Rp 100,000 from Food → Transport. Food now has Rp 300,000 remaining.",
  },
  { role: "user", text: "Give me a full budget summary" },
  {
    role: "bot",
    card: [
      { name: "Food", pct: 58, amount: "Rp 300k left" },
      { name: "Transport", pct: 72, amount: "Rp 250k left" },
      { name: "Bills", pct: 95, amount: "Rp 22k left" },
      { name: "Belanja", pct: 110, amount: "Over by 42k", over: true },
      { name: "Hiburan", pct: 40, amount: "Rp 180k left" },
    ],
  },
]

export function HomePage() {
  const navigate = useNavigate()

  return (
    <div>
      {/* ── HERO ── */}
      <section className="hero-section">
        <div className="container">
          <div className="hero-grid">
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              <div className="label" style={{ color: "var(--brand-text)" }}>
                AI-First Personal Finance
              </div>
              <h1 className="display">
                Ask.
                <br />
                Budget.
                <br />
                Done.
              </h1>
              <p className="body-lg" style={{ maxWidth: 420 }}>
                Connect Envel to your favorite AI assistant. Chat your way to better
                finances.
              </p>
              <div
                style={{
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                <button
                  className="btn btn-primary btn-lg"
                  onClick={() => {
                    window.location.href = "https://platform.envel.dev/signup"
                  }}
                >
                  Start for Free
                </button>
                <button
                  className="btn btn-outline"
                  onClick={() => navigate("/docs")}
                  style={{ padding: "14px 24px", borderRadius: 12 }}
                >
                  Read the Docs
                </button>
              </div>
              <AILogos />
            </div>
            <div style={{ position: "relative" }}>
              <div
                style={{
                  position: "absolute",
                  inset: -24,
                  background:
                    "radial-gradient(ellipse at center, oklch(94% 0.06 145) 0%, transparent 70%)",
                  borderRadius: 32,
                  zIndex: 0,
                }}
              />
              <div style={{ position: "relative", zIndex: 1 }}>
                <ChatMockup messages={HERO_MESSAGES} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── METHOD ── */}
      <section
        className="section"
        id="method"
        style={{
          background: "var(--bg-card)",
          borderTop: "1px solid var(--border)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div className="container">
          <div style={{ textAlign: "center", marginBottom: 64 }}>
            <div className="label" style={{ marginBottom: 12 }}>
              The Method
            </div>
            <h2 className="h1" style={{ marginBottom: 16 }}>
              A better way to
              <br />
              manage your money.
            </h2>
            <p className="body-lg" style={{ maxWidth: 500, margin: "0 auto" }}>
              No complicated dashboards. No guilt trips. Just a system that actually
              works.
            </p>
          </div>
          <div className="method-grid">
            <MethodCard
              num={1}
              icon={<IconEnvelope />}
              title="Every rupiah has a job"
              body="Before the month starts, assign your money to envelopes — food, rent, transport, fun. Spend from the envelope, not your total balance. When the envelope is empty, you decide what to do next."
            />
            <MethodCard
              num={2}
              icon={<IconSwap />}
              title="Overspent? Just move it."
              body="Life doesn't follow a spreadsheet. When something comes up, shift money between envelopes — no guilt, no starting over. Flexibility is built into the method."
            />
            <MethodCard
              num={3}
              icon={<IconChat />}
              title="Just tell your AI"
              body="No manual input. No logging into another app. Just tell your AI what you spent, and Envel handles the rest — automatically updating your envelopes in real time."
            />
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="section" id="features">
        <div className="container">
          <div style={{ textAlign: "center", marginBottom: 52 }}>
            <div className="label" style={{ marginBottom: 12 }}>
              Features
            </div>
            <h2 className="h1">
              Everything you need.
              <br />
              Nothing you don't.
            </h2>
          </div>
          <div className="feature-grid">
            <FeatureCard
              icon={<IconChat />}
              title="Your budget, in chat"
              body="Use Envel directly from Claude, ChatGPT, Gemini — or use our built-in chat on the Envel platform. No extra app to open, no learning curve. Just talk to your AI like you always do."
            />
            <FeatureCard
              icon={<IconWallet />}
              title="Multiple accounts, one view"
              body="Track all your accounts in one place — bank accounts, e-wallets, cash. Envel keeps everything organized so you always know exactly where your money sits."
            />
            <FeatureCard
              icon={<IconSeedling />}
              title="Wish Farm"
              body="Got something you're saving up for? Plant it in your Wish Farm and fund it a little each month. Set a goal, watch it grow, and harvest it when you're ready — guilt-free."
            />
            <FeatureCard
              icon={<IconStack />}
              title="Envelope Budgeting + Carryover"
              body="Assign money to envelopes before you spend it. If you overspend, move funds from another envelope. If you underspend, carry it forward. The system adapts to your real life."
            />
          </div>

          {/* Coming Soon */}
          <div style={{ marginTop: 48 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                marginBottom: 16,
              }}
            >
              <div className="label">Coming Soon</div>
              <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
            </div>
            <div className="coming-soon-grid">
              <FeatureCard
                muted
                icon={<IconSun />}
                title="Morning Briefing"
                body="Start your day with a personalized budget summary — delivered straight to your AI chat, every morning."
              />
              <FeatureCard
                muted
                icon={<IconPrompt />}
                title="MCP Prompts"
                body="Ready-to-use prompts for deeper financial analysis. Ask the right questions and get real, actionable answers."
              />
              <FeatureCard
                muted
                icon={<IconApp />}
                title="MCP Apps"
                body="Interactive budget charts, envelope overviews, and more — rendered inline inside your AI chat. No switching tabs."
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── DEMO ── */}
      <section className="section demo-section">
        <div className="container">
          <div style={{ textAlign: "center", marginBottom: 52 }}>
            <h2 className="h1" style={{ color: "#fff", marginBottom: 14 }}>
              See Envel in action.
            </h2>
            <p
              className="body-lg"
              style={{
                color: "oklch(65% 0.01 65)",
                maxWidth: 500,
                margin: "0 auto",
              }}
            >
              Log expenses, check balances, move money between envelopes — all without
              leaving your chat.
            </p>
          </div>
          <div style={{ maxWidth: 520, margin: "0 auto" }}>
            <ChatMockup dark messages={DEMO_MESSAGES} />
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ── */}
      <section
        className="section"
        style={{
          textAlign: "center",
          background: "var(--bg-card)",
          borderTop: "1px solid var(--border)",
        }}
      >
        <div className="container">
          <div
            style={{
              maxWidth: 560,
              margin: "0 auto",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 20,
            }}
          >
            <h2 className="h1">
              Take control of your money.
              <br />
              Starting today.
            </h2>
            <p className="body-lg">
              Free to get started. Works with the AI you already use.
            </p>
            <button
              className="btn btn-primary btn-lg"
              style={{ marginTop: 8 }}
              onClick={() => {
                window.location.href = "https://platform.envel.dev/signup"
              }}
            >
              Start for Free
            </button>
            <p className="caption">No credit card required.</p>
          </div>
        </div>
      </section>
    </div>
  )
}

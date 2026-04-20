import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"

interface AuthState {
  authenticated: boolean
  username: string | null
  loading: boolean
}

export interface SignupInput {
  name: string
  email: string
  username: string
  password: string
}

export interface SignupResult {
  ok: boolean
  error?: string
  field?: string
  code?: string
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<{ ok: boolean; error?: string }>
  signup: (input: SignupInput) => Promise<SignupResult>
  markAuthenticated: (username: string) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

// ── Mock mode (no backend) ──────────────────────────────
// When the platform server isn't running, fall back to mock auth
// so the frontend can still be developed standalone.

const MOCK_MODE = false

const mockLogin = async (
  username: string,
  password: string
): Promise<{ ok: boolean; error?: string }> => {
  // Accept any non-empty credentials in mock mode
  if (!username || !password) {
    return { ok: false, error: "Username and password required" }
  }
  return { ok: true }
}

// ── Provider ────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    authenticated: false,
    username: null,
    loading: true,
  })

  // Check existing session on mount
  useEffect(() => {
    if (MOCK_MODE) {
      const saved = localStorage.getItem("envel-mock-user")
      setState({
        authenticated: !!saved,
        username: saved,
        loading: false,
      })
      return
    }

    fetch("/api/auth/session", { credentials: "include" })
      .then((res) => res.json())
      .then((data) => {
        setState({
          authenticated: data.authenticated === true,
          username: data.username ?? null,
          loading: false,
        })
      })
      .catch(() => {
        setState({ authenticated: false, username: null, loading: false })
      })
  }, [])

  const login = useCallback(
    async (
      username: string,
      password: string
    ): Promise<{ ok: boolean; error?: string }> => {
      if (MOCK_MODE) {
        const result = await mockLogin(username, password)
        if (result.ok) {
          localStorage.setItem("envel-mock-user", username)
          setState({ authenticated: true, username, loading: false })
        }
        return result
      }

      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ username, password }),
        })

        if (res.ok) {
          const data = await res.json()
          setState({
            authenticated: true,
            username: data.username,
            loading: false,
          })
          return { ok: true }
        }

        const err = await res.json().catch(() => null)
        return { ok: false, error: err?.detail ?? "Invalid credentials" }
      } catch {
        return { ok: false, error: "Cannot connect to server" }
      }
    },
    []
  )

  const signup = useCallback(async (input: SignupInput): Promise<SignupResult> => {
    try {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(input),
      })
      if (res.ok) {
        const data = await res.json()
        setState({ authenticated: true, username: data.username, loading: false })
        return { ok: true }
      }
      const err = await res.json().catch(() => null)
      return {
        ok: false,
        error: err?.detail ?? "Signup failed",
        field: err?.field,
        code: err?.code,
      }
    } catch {
      return { ok: false, error: "Cannot connect to server" }
    }
  }, [])

  const markAuthenticated = useCallback((username: string) => {
    setState({ authenticated: true, username, loading: false })
  }, [])

  const logout = useCallback(async () => {
    if (MOCK_MODE) {
      localStorage.removeItem("envel-mock-user")
      setState({ authenticated: false, username: null, loading: false })
      return
    }

    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    }).catch(() => {})
    setState({ authenticated: false, username: null, loading: false })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, signup, markAuthenticated, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}

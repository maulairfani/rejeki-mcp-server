import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { getSession } from "@/lib/api"

interface AuthState {
  loading: boolean
  authenticated: boolean
  username: string | null
  refetch: () => Promise<void>
}

const AuthContext = createContext<AuthState>({
  loading: true,
  authenticated: false,
  username: null,
  refetch: async () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<Omit<AuthState, "refetch">>({
    loading: true,
    authenticated: false,
    username: null,
  })

  const refetch = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }))
    try {
      const res = await getSession()
      setState({ loading: false, authenticated: true, username: res.data.username })
    } catch {
      setState({ loading: false, authenticated: false, username: null })
    }
  }, [])

  useEffect(() => {
    refetch()
  }, [refetch])

  return (
    <AuthContext.Provider value={{ ...state, refetch }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

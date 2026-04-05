import { Navigate } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { loading, authenticated } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen">Loading…</div>
  if (!authenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

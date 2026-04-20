import { Route, Routes, Navigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { AppSidebar } from "@/components/sidebar-08/app-sidebar"
import { useTheme } from "@/hooks/useTheme"
import { useAuth } from "@/hooks/useAuth"
import { ShowNominalProvider, useShowNominal } from "@/hooks/useShowNominal"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { DashboardPage } from "@/pages/DashboardPage"
import { TransactionsPage } from "@/pages/TransactionsPage"
import { EnvelopesPage } from "@/pages/EnvelopesPage"
import { AccountsPage } from "@/pages/AccountsPage"
import { WishlistPage } from "@/pages/WishlistPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { LoginPage } from "@/pages/LoginPage"
import { SignupPage } from "@/pages/SignupPage"
import { SignupConfirmPage } from "@/pages/SignupConfirmPage"
import { ConnectPage } from "@/pages/ConnectPage"

export default function App() {
  const { authenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!authenticated) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/signup/confirm" element={<SignupConfirmPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <ShowNominalProvider>
      <Routes>
        {/* Chromeless authenticated routes */}
        <Route path="/connect" element={<ConnectPage />} />
        {/* Chromed routes (sidebar + main) */}
        <Route path="/*" element={<ChromedApp />} />
      </Routes>
    </ShowNominalProvider>
  )
}

function ChromedApp() {
  const { theme, setTheme } = useTheme()
  const { showNominal } = useShowNominal()

  return (
    <SidebarProvider>
      <AppSidebar theme={theme} setTheme={setTheme} />
      <SidebarInset className="flex flex-col overflow-hidden">
        <Routes>
          <Route path="/envelopes" element={<EnvelopesPage showNominal={showNominal} />} />
          <Route path="/transactions" element={<TransactionsPage showNominal={showNominal} />} />
          <Route path="/analytics" element={<DashboardPage showNominal={showNominal} />} />
          <Route path="/accounts" element={<AccountsPage showNominal={showNominal} />} />
          <Route path="/wishlist" element={<WishlistPage showNominal={showNominal} />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/envelopes" replace />} />
        </Routes>
      </SidebarInset>
    </SidebarProvider>
  )
}

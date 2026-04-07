import { Outlet, useLocation } from "react-router-dom"
import { AppSidebar } from "@/components/AppSidebar"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AuthGuard } from "@/components/AuthGuard"
import { Separator } from "@/components/ui/separator"

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/budget": "Budget",
  "/transactions": "Transactions",
  "/chat": "Chat",
  "/settings": "Settings",
}

export function AppLayout() {
  const { pathname } = useLocation()
  const title = pageTitles[pathname] ?? "Envel"

  return (
    <AuthGuard>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex items-center gap-3 px-4 h-12 border-b shrink-0 bg-background/80 backdrop-blur-sm sticky top-0 z-10">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="h-4" />
            <span className="text-sm font-medium text-foreground">{title}</span>
          </header>
          <main className="flex-1 overflow-auto p-6 page-enter">
            <Outlet />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </AuthGuard>
  )
}

import * as React from "react"
import { Link, useLocation } from "react-router-dom"
import {
  CreditCard,
  Heart,
  LayoutDashboard,
  List,
  Settings,
  Wallet,
} from "lucide-react"

import { NavMain } from "@/components/sidebar-08/nav-main"
import { NavUser } from "@/components/sidebar-08/nav-user"
import { LogoMark } from "@/components/shared/LogoMark"
import { useAuth } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

const data = {
  navMain: [
    { title: "Envelopes", url: "/envelopes", icon: Wallet },
    { title: "Transactions", url: "/transactions", icon: List },
    { title: "Analytics", url: "/analytics", icon: LayoutDashboard },
    { title: "Accounts", url: "/accounts", icon: CreditCard },
    { title: "Wishlist", url: "/wishlist", icon: Heart },
  ],
}

import type { Theme } from "@/hooks/useTheme"

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  theme: Theme
  setTheme: (t: Theme) => void
}

export function AppSidebar({ theme, setTheme, ...props }: AppSidebarProps) {
  const { username, name, email } = useAuth()
  const { pathname } = useLocation()
  const settingsActive = pathname === "/settings"

  const user = {
    name: name ?? username ?? "User",
    email: email ?? "",
    avatar: "",
  }

  return (
    <Sidebar variant="inset" collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              render={<Link to="/" />}
              className="group-data-[collapsible=icon]:!size-8 group-data-[collapsible=icon]:!p-0 group-data-[collapsible=icon]:justify-center [&>div]:group-data-[collapsible=icon]:hidden [&_svg]:group-data-[collapsible=icon]:!size-5"
            >
              <LogoMark size={30} />
              <div className="grid flex-1 text-left leading-tight">
                <span className="truncate font-heading text-sm font-bold text-text-primary">
                  Envel
                </span>
                <span className="truncate text-[11px] text-text-muted">
                  Envelope Budget
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu className="gap-1">
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<Link to="/settings" />}
              tooltip="Settings"
              isActive={settingsActive}
              className={cn(
                "relative h-10",
                settingsActive &&
                  "before:absolute before:left-0 before:top-1/2 before:h-6 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-brand [&_svg]:text-brand group-data-[collapsible=icon]:before:hidden",
              )}
            >
              <Settings />
              <span>Settings</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <NavUser user={user} theme={theme} setTheme={setTheme} />
      </SidebarFooter>
    </Sidebar>
  )
}

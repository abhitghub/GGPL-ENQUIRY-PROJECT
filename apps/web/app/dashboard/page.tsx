import { AppShell } from "@/components/app-shell/app-shell";
import { DashboardClient } from "./dashboard-client";

export default function DashboardPage() {
  return (
    <AppShell activePath="/dashboard" title="Dashboard" breadcrumb="Workspace">
      <DashboardClient />
    </AppShell>
  );
}

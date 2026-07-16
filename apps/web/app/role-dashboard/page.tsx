import { AppShell } from "@/components/app-shell/app-shell";
import { RoleDashboardClient } from "./role-dashboard-client";

// Feature-flagged (NEXT_PUBLIC_ENABLE_GRANULAR_WORKFLOW) role-routed dashboard.
// Additive: the existing /dashboard page and its components are untouched.
export default function RoleDashboardPage() {
  return (
    <AppShell activePath="/dashboard" title="My work" breadcrumb="Start">
      <RoleDashboardClient />
    </AppShell>
  );
}

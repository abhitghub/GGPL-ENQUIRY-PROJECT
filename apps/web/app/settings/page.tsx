import { AppShell } from "@/components/app-shell/app-shell";
import { SettingsClient } from "./settings-client";

export default function SettingsPage() {
  return (
    <AppShell activePath="/settings" title="Settings" breadcrumb="Workspace / Settings">
      <SettingsClient />
    </AppShell>
  );
}

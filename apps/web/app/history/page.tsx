import { AppShell } from "@/components/app-shell/app-shell";
import { HistoryClient } from "./history-client";

export default function HistoryPage() {
  return (
    <AppShell activePath="/history" title="Activity History" breadcrumb="Workspace / Activity History">
      <HistoryClient />
    </AppShell>
  );
}

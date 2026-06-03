import { AppShell } from "@/components/app-shell/app-shell";
import { HistoryClient } from "./history-client";

export default function HistoryPage() {
  return (
    <AppShell activePath="/history" title="Reports" breadcrumb="More / Reports">
      <HistoryClient />
    </AppShell>
  );
}

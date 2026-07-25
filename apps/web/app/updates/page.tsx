import { AppShell } from "@/components/app-shell/app-shell";
import { UpdatesClient } from "./updates-client";

export default function UpdatesPage() {
  return (
    <AppShell activePath="/updates" title="Updates" breadcrumb="Start">
      <UpdatesClient />
    </AppShell>
  );
}
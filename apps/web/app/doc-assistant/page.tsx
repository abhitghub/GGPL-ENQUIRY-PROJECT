import { AppShell } from "@/components/app-shell/app-shell";
import { DocAssistantClient } from "./doc-assistant-client";

export default function DocAssistantPage() {
  return (
    <AppShell activePath="/doc-assistant" title="Document Assistant" breadcrumb="Workspace / Assistant">
      <DocAssistantClient />
    </AppShell>
  );
}

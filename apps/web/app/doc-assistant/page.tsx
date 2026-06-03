import { AppShell } from "@/components/app-shell/app-shell";
import { DocAssistantClient } from "./doc-assistant-client";

export default function DocAssistantPage() {
  return (
    <AppShell activePath="/doc-assistant" title="Document assistant" breadcrumb="More / Document assistant">
      <DocAssistantClient />
    </AppShell>
  );
}

import { Suspense } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { QuotesClient } from "./quotes-client";

export default function QuotesPage() {
  return (
    <AppShell activePath="/quotes" title="Drafts" breadcrumb="Workspace / Drafts">
      <Suspense fallback={<div className="rounded-md border p-4 text-sm text-muted-foreground">Loading quote workspace...</div>}>
        <QuotesClient section="drafts" />
      </Suspense>
    </AppShell>
  );
}

import { Suspense } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { QuotesClient } from "../quotes-client";

export default function FinalQuotationPage() {
  return (
    <AppShell activePath="/quotes/final" title="Final Quotation" breadcrumb="Workspace / Final Quotation">
      <Suspense fallback={<div className="rounded-md border p-4 text-sm text-muted-foreground">Loading final quotation workspace...</div>}>
        <QuotesClient section="final" />
      </Suspense>
    </AppShell>
  );
}

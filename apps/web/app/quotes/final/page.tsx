import { Suspense } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { QuotesClient } from "../quotes-client";

export default function FinalQuotationPage() {
  return (
    <AppShell activePath="/quotes/final" title="Quotations" breadcrumb="Work / Quotations">
      <Suspense fallback={<div className="rounded-md border p-4 text-sm text-muted-foreground">Loading quotation workspace...</div>}>
        <QuotesClient section="final" />
      </Suspense>
    </AppShell>
  );
}

import { Suspense } from "react";

import { AppShell } from "@/components/app-shell/app-shell";
import { QuotesClient } from "../quotes/quotes-client";

export default function PurchaseOrdersPage() {
  return (
    <AppShell activePath="/purchase-orders" title="Orders" breadcrumb="Work / Orders">
      <Suspense fallback={<div className="rounded-md border p-4 text-sm text-muted-foreground">Loading purchase order workspace...</div>}>
        <QuotesClient section="po" />
      </Suspense>
    </AppShell>
  );
}

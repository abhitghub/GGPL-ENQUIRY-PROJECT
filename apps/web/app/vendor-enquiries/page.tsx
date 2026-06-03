import { AppShell } from "@/components/app-shell/app-shell";
import { VendorEnquiriesClient } from "./vendor-enquiries-client";

export default function VendorEnquiriesPage() {
  return (
    <AppShell activePath="/vendor-enquiries" title="Vendor enquiries" breadcrumb="More / Vendor enquiries">
      <VendorEnquiriesClient />
    </AppShell>
  );
}

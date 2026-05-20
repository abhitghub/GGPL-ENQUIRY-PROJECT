import { AppShell } from "@/components/app-shell/app-shell";
import { VendorEnquiriesClient } from "./vendor-enquiries-client";

export default function VendorEnquiriesPage() {
  return (
    <AppShell activePath="/vendor-enquiries" title="Vendor Enquiries" breadcrumb="Workspace / Vendor Enquiries">
      <VendorEnquiriesClient />
    </AppShell>
  );
}

import { AppShell } from "@/components/app-shell/app-shell";
import { ConverterClient } from "./converter-client";

export default function ConverterPage() {
  return (
    <AppShell activePath="/tools/converter" title="Unit Converter" breadcrumb="Workspace / Tools">
      <ConverterClient />
    </AppShell>
  );
}

import { Card, CardContent } from "@/components/ui/card";

export function MetricCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="text-xs font-semibold uppercase text-muted-foreground">{label}</div>
        <div className="mt-3 text-3xl font-bold tracking-normal">{value}</div>
        <div className="mt-2 text-sm text-muted-foreground">{hint}</div>
      </CardContent>
    </Card>
  );
}

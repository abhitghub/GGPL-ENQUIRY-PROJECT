import { Card, CardContent } from "@/components/ui/card";

export function MetricCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card>
      <CardContent className="p-3">
        <div className="flex items-baseline justify-between gap-3">
          <div className="text-sm font-medium text-muted-foreground">{label}</div>
          <div className="text-lg font-semibold tracking-normal">{value}</div>
        </div>
        <div className="mt-1 truncate text-xs text-muted-foreground">{hint}</div>
      </CardContent>
    </Card>
  );
}

import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
}: {
  icon: LucideIcon;
  title: string;
  body: string;
  action?: { label: string; href: string };
}) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-md bg-muted">
          <Icon className="h-6 w-6 text-muted-foreground" />
        </div>
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">{body}</p>
        {action ? (
          <Button asChild className="mt-5">
            <a href={action.href}>{action.label}</a>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

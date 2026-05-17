"use client";
import { ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export function SettingsClient() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-md border px-3 py-2">
            <div>
              <div className="text-sm font-medium">Authentication</div>
              <div className="text-sm text-muted-foreground">Supabase session or local dev session</div>
            </div>
            <Badge variant="secondary">Active</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-md border px-3 py-2">
            <Label htmlFor="email-alerts" className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-secondary" />
              Email alerts
            </Label>
            <Switch id="email-alerts" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

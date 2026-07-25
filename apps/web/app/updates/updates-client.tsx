"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowUpRight, Bell, ClipboardList, GitBranch, MessageSquareWarning, UserCheck } from "lucide-react";

import {
  WORK_NOTIFICATION_EVENT,
  markUpdatesSeen,
  workNotificationHref,
} from "@/components/providers/notification-listener";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  type AssignedWorkItem,
  type WorkUpdate,
  listAppUsers,
  listAssignedWork,
  listWorkUpdates,
  getCurrentAppUserRemote,
} from "@/lib/api";
import { AppUser, USERS_CHANGED_EVENT, getCurrentAppUser, roleLabels, setCurrentAppUser } from "@/lib/auth/users";

const TEAM_VIEWER_ROLES = new Set(["admin", "management"]);

const KIND_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  workflow: GitBranch,
  enquiry_created: ClipboardList,
  assignment: UserCheck,
  query: MessageSquareWarning,
};

function timeAgo(value: string): string {
  const at = Date.parse(value);
  if (!at) return "";
  const seconds = Math.max(0, Math.floor((Date.now() - at) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  return new Date(at).toLocaleDateString();
}

function assignedHref(item: AssignedWorkItem): string {
  return workNotificationHref({ quote_id: item.quote_id, stage: item.workflow_stage });
}

export function UpdatesClient() {
  const [me, setMe] = React.useState<AppUser>(() => getCurrentAppUser());
  const [people, setPeople] = React.useState<AppUser[]>([]);
  const [selectedId, setSelectedId] = React.useState("");
  const [updates, setUpdates] = React.useState<WorkUpdate[]>([]);
  const [assigned, setAssigned] = React.useState<AssignedWorkItem[]>([]);
  const [targetName, setTargetName] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");

  const canPickPerson = TEAM_VIEWER_ROLES.has(me.role);
  const viewingSelf = !selectedId || selectedId === me.id;

  // Opening this page counts as reading the feed: clear the sidebar badge.
  React.useEffect(() => {
    markUpdatesSeen();
  }, []);

  React.useEffect(() => {
    const refresh = () => setMe(getCurrentAppUser());
    refresh();
    getCurrentAppUserRemote()
      .then((user) => {
        setCurrentAppUser(user);
        setMe(getCurrentAppUser());
      })
      .catch(() => undefined);
    window.addEventListener(USERS_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(USERS_CHANGED_EVENT, refresh);
  }, []);

  React.useEffect(() => {
    if (!canPickPerson) return;
    listAppUsers()
      .then((users) => setPeople(users.filter((user) => user.active)))
      .catch(() => setPeople([]));
  }, [canPickPerson]);

  const load = React.useCallback(
    (userId: string, showSpinner: boolean) => {
      if (showSpinner) setLoading(true);
      Promise.all([listWorkUpdates(userId), listAssignedWork(userId)])
        .then(([feed, work]) => {
          setUpdates(feed.items);
          setAssigned(work.items);
          setTargetName(feed.target.name || feed.target.user_id);
          setError("");
        })
        .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load updates"))
        .finally(() => setLoading(false));
    },
    [],
  );

  React.useEffect(() => {
    load(viewingSelf ? "" : selectedId, true);
  }, [load, selectedId, viewingSelf]);

  // Live refresh: any incoming notification may change both lists, and since
  // the user is looking at this page it also counts as seen.
  React.useEffect(() => {
    const onNotification = () => {
      load(viewingSelf ? "" : selectedId, false);
      markUpdatesSeen();
    };
    window.addEventListener(WORK_NOTIFICATION_EVENT, onNotification);
    return () => window.removeEventListener(WORK_NOTIFICATION_EVENT, onNotification);
  }, [load, selectedId, viewingSelf]);

  const heading = viewingSelf ? "Your updates and assigned work" : `Updates and assigned work for ${targetName}`;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Bell className="h-4 w-4" />
              Updates
            </CardTitle>
            <CardDescription>{heading}</CardDescription>
          </div>
          {canPickPerson ? (
            <Select value={selectedId || me.id} onValueChange={(value) => setSelectedId(value === me.id ? "" : value)}>
              <SelectTrigger className="w-full sm:w-72">
                <SelectValue placeholder="Choose a person" />
              </SelectTrigger>
              <SelectContent>
                {(people.length ? people : [me]).map((person) => (
                  <SelectItem key={person.id} value={person.id}>
                    {person.name || person.id}
                    {person.id === me.id ? " (you)" : ""} — {roleLabels[person.role] ?? person.role}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
        </CardHeader>
        <CardContent>
          {error ? <div className="mb-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</div> : null}
          <Tabs defaultValue="updates">
            <TabsList>
              <TabsTrigger value="updates">Updates ({updates.length})</TabsTrigger>
              <TabsTrigger value="assigned">Assigned work ({assigned.length})</TabsTrigger>
            </TabsList>
            <TabsContent value="updates" className="mt-4">
              {loading ? (
                <div className="py-8 text-center text-sm text-muted-foreground">Loading updates...</div>
              ) : !updates.length ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No updates yet. Workflow handoffs, assignments and change queries will appear here.
                </div>
              ) : (
                <div className="divide-y rounded-md border">
                  {updates.map((update) => {
                    const Icon = KIND_ICONS[update.kind] ?? Bell;
                    return (
                      <div key={update.id} className="flex items-start gap-3 px-3 py-3">
                        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                          <Icon className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                            <span className="text-sm font-medium">{update.title}</span>
                            {update.stage_label ? <Badge variant="outline">{update.stage_label}</Badge> : null}
                          </div>
                          <p className="mt-0.5 text-sm text-muted-foreground">{update.message}</p>
                          <div className="mt-1 text-xs text-muted-foreground">
                            {update.by ? `${update.by} · ` : ""}
                            {timeAgo(update.at)}
                          </div>
                        </div>
                        {update.quote_id ? (
                          <Button variant="ghost" size="sm" asChild>
                            <Link href={workNotificationHref(update)}>
                              Open
                              <ArrowUpRight className="h-3.5 w-3.5" />
                            </Link>
                          </Button>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}
            </TabsContent>
            <TabsContent value="assigned" className="mt-4">
              {loading ? (
                <div className="py-8 text-center text-sm text-muted-foreground">Loading assigned work...</div>
              ) : !assigned.length ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  Nothing is waiting on {viewingSelf ? "you" : targetName} right now.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Enquiry</TableHead>
                        <TableHead>Customer</TableHead>
                        <TableHead>Current step</TableHead>
                        <TableHead>Assigned via</TableHead>
                        <TableHead>Owner</TableHead>
                        <TableHead>Updated</TableHead>
                        <TableHead className="w-16" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {assigned.map((item) => (
                        <TableRow key={item.quote_id}>
                          <TableCell className="font-medium">{item.quote_no || item.project_ref || "Untitled"}</TableCell>
                          <TableCell className="max-w-56 truncate">{item.customer || "—"}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{item.workflow_label}</Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {item.assigned_via === "owner" ? "Owner" : `${item.team || "Team"} queue`}
                          </TableCell>
                          <TableCell className="max-w-40 truncate text-sm text-muted-foreground">{item.owner_name || "Unassigned"}</TableCell>
                          <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{timeAgo(item.updated_at)}</TableCell>
                          <TableCell>
                            <Button variant="ghost" size="sm" asChild>
                              <Link href={assignedHref(item)}>Open</Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
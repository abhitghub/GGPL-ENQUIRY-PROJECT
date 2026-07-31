"use client";
import * as React from "react";
import { BrainCircuit, Check, Loader2, Plus, RotateCcw, Search, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  deleteLearnedDescription,
  getLearningSettings,
  listLearnedDescriptions,
  patchLearnedDescription,
  putLearningSettings,
  setLearnedDescriptionVerdict,
  teachLearnedDescription,
  type LearnedDescription,
  type LearnedStatus,
  type LearningSettings,
} from "@/lib/api";

const STATUS_LABELS: Record<LearnedStatus, string> = {
  pending: "Awaiting approval",
  approved: "Permanent",
  rejected: "Retired",
};

const STATUS_VARIANTS: Record<LearnedStatus, "default" | "secondary" | "outline"> = {
  pending: "secondary",
  approved: "default",
  rejected: "outline",
};

const SOURCE_LABELS: Record<string, string> = {
  edit: "Captured from a team edit",
  manual: "Added by hand",
  import: "Imported",
};

type Filter = "pending" | "approved" | "rejected" | "all";

const blankDraft = { source_text: "", ggpl_description: "", customer: "", note: "" };

/**
 * Curation screen for what the portal has learned.
 *
 * Every GGPL description the team corrects is captured here as "awaiting
 * approval" and already in use; approving one makes it permanent, retiring one
 * takes it out of service. New descriptions for gaskets the engine has no
 * format for are added straight into permanent memory from the form at the top.
 */
export function LearnedDescriptionsPanel({ canCurate }: { canCurate: boolean }) {
  const [entries, setEntries] = React.useState<LearnedDescription[]>([]);
  const [settings, setSettings] = React.useState<LearningSettings | null>(null);
  const [filter, setFilter] = React.useState<Filter>("pending");
  const [query, setQuery] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [busyId, setBusyId] = React.useState("");
  const [draft, setDraft] = React.useState(blankDraft);
  const [saving, setSaving] = React.useState(false);
  const [editing, setEditing] = React.useState<{ id: string; text: string } | null>(null);

  const reload = React.useCallback(async () => {
    setLoading(true);
    try {
      setEntries(await listLearnedDescriptions());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not load learned descriptions");
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void reload();
    getLearningSettings().then(setSettings).catch(() => setSettings(null));
  }, [reload]);

  const pendingCount = entries.filter((entry) => entry.status === "pending").length;
  const approvedCount = entries.filter((entry) => entry.status === "approved").length;

  const visible = React.useMemo(() => {
    const needle = query.trim().toUpperCase();
    return entries
      .filter((entry) => filter === "all" || entry.status === filter)
      .filter((entry) =>
        !needle
        || entry.source_text.toUpperCase().includes(needle)
        || entry.ggpl_description.toUpperCase().includes(needle)
        || entry.customer.toUpperCase().includes(needle));
  }, [entries, filter, query]);

  /** Replace one row in place so the list does not jump after an action. */
  function replace(updated: LearnedDescription) {
    setEntries((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
  }

  async function act(entry: LearnedDescription, verdict: "approve" | "reject") {
    setBusyId(entry.id);
    try {
      replace(await setLearnedDescriptionVerdict(entry.id, verdict));
      toast.success(verdict === "approve" ? "Saved to the portal permanently" : "Retired — the portal will stop using it");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update the entry");
    } finally {
      setBusyId("");
    }
  }

  async function remove(entry: LearnedDescription) {
    setBusyId(entry.id);
    try {
      await deleteLearnedDescription(entry.id);
      setEntries((rows) => rows.filter((row) => row.id !== entry.id));
      toast.success("Deleted");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not delete the entry");
    } finally {
      setBusyId("");
    }
  }

  async function saveEdit() {
    if (!editing) return;
    const text = editing.text.trim();
    if (!text) return toast.error("The GGPL description cannot be empty");
    setBusyId(editing.id);
    try {
      replace(await patchLearnedDescription(editing.id, { ggpl_description: text }));
      setEditing(null);
      toast.success("Updated");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update the entry");
    } finally {
      setBusyId("");
    }
  }

  async function addEntry() {
    const sourceText = draft.source_text.trim();
    const description = draft.ggpl_description.trim();
    if (!sourceText) return toast.error("Paste the customer wording this should match");
    if (!description) return toast.error("Enter the GGPL description to answer it with");
    setSaving(true);
    try {
      const created = await teachLearnedDescription({
        source_text: sourceText,
        ggpl_description: description,
        customer: draft.customer.trim(),
        note: draft.note.trim(),
        approve: true,
      });
      setEntries((rows) => [created, ...rows.filter((row) => row.id !== created.id)]);
      setDraft(blankDraft);
      setFilter(created.status === "approved" ? "approved" : "pending");
      toast.success(
        created.status === "approved"
          ? "Saved to the portal permanently"
          : "Submitted for approval — it is in use, pending review",
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not save the description");
    } finally {
      setSaving(false);
    }
  }

  async function toggleSetting(key: keyof LearningSettings, value: boolean) {
    const previous = settings;
    setSettings(settings ? { ...settings, [key]: value } : settings);
    try {
      setSettings(await putLearningSettings({ [key]: value }));
    } catch (error) {
      setSettings(previous);
      toast.error(error instanceof Error ? error.message : "Could not save the setting");
    }
  }

  return (
    <Card className="order-4 lg:col-span-2">
      <CardHeader className="flex flex-row items-start justify-between gap-3 border-b px-4 py-3">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <BrainCircuit className="h-4 w-4" />
            What the portal has learned
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Every GGPL description the team corrects is remembered here and reused the next time the same
            customer wording arrives. Approve one to make it permanent.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant="secondary">{pendingCount} to review</Badge>
          <Badge variant="outline">{approvedCount} permanent</Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 p-3">
        {!canCurate ? (
          <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
            Your corrections are captured and used automatically. Estimation, management and admin decide which
            ones become permanent.
          </div>
        ) : null}

        {canCurate && settings ? (
          <div className="grid gap-2 rounded-md border bg-muted/20 p-3 sm:grid-cols-3">
            <SettingToggle
              id="auto-capture"
              label="Learn from team edits"
              hint="Remember every corrected GGPL description"
              checked={settings.auto_capture}
              onChange={(value) => void toggleSetting("auto_capture", value)}
            />
            <SettingToggle
              id="apply-pending"
              label="Use before approval"
              hint="Apply a correction while it waits for review"
              checked={settings.apply_pending}
              onChange={(value) => void toggleSetting("apply_pending", value)}
            />
            <SettingToggle
              id="suggest-similar"
              label="Flag similar wording"
              hint="Suggest, but never auto-apply, near matches"
              checked={settings.suggest_similar}
              onChange={(value) => void toggleSetting("suggest_similar", value)}
            />
          </div>
        ) : null}

        <details className="rounded-md border bg-background">
          <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
            Add a description the portal does not know
          </summary>
          <div className="space-y-2 border-t p-3">
            <div className="grid gap-2 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Customer wording to match *</Label>
                <textarea
                  className="min-h-20 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  placeholder="Paste the enquiry line exactly as the customer sends it"
                  value={draft.source_text}
                  onChange={(event) => setDraft({ ...draft, source_text: event.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">GGPL description to answer with *</Label>
                <textarea
                  className="min-h-20 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  placeholder="SIZE : 2&quot; X 150# X 4.5MM THK ,SS316 + GRAPHITE ,ASME B16.20"
                  value={draft.ggpl_description}
                  onChange={(event) => setDraft({ ...draft, ggpl_description: event.target.value })}
                />
              </div>
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <Input
                placeholder="Only for this customer (leave blank for all)"
                value={draft.customer}
                onChange={(event) => setDraft({ ...draft, customer: event.target.value })}
              />
              <Input
                placeholder="Note for the team (optional)"
                value={draft.note}
                onChange={(event) => setDraft({ ...draft, note: event.target.value })}
              />
            </div>
            <Button size="sm" onClick={() => void addEntry()} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Save to the portal
            </Button>
          </div>
        </details>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-56">
            <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-8"
              placeholder="Search wording, description or customer"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <Select value={filter} onValueChange={(value) => setFilter(value as Filter)}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pending">Awaiting approval</SelectItem>
              <SelectItem value="approved">Permanent</SelectItem>
              <SelectItem value="rejected">Retired</SelectItem>
              <SelectItem value="all">All</SelectItem>
            </SelectContent>
          </Select>
          <Button size="sm" variant="outline" onClick={() => void reload()} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
            Refresh
          </Button>
        </div>

        {loading && !entries.length ? (
          <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
            Loading what the portal has learned...
          </div>
        ) : null}

        {!loading && !visible.length ? (
          <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
            {entries.length
              ? "Nothing matches this filter."
              : "Nothing learned yet. Correct a GGPL description on an enquiry and it will appear here."}
          </div>
        ) : null}

        <div className="space-y-2">
          {visible.map((entry) => (
            <div key={entry.id} className="rounded-md border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={STATUS_VARIANTS[entry.status]}>{STATUS_LABELS[entry.status]}</Badge>
                <Badge variant="outline">{entry.customer || "All customers"}</Badge>
                <span className="text-xs text-muted-foreground">
                  {SOURCE_LABELS[entry.source] ?? entry.source}
                  {entry.created_by ? ` by ${entry.created_by}` : ""}
                </span>
                {entry.hit_count ? (
                  <span className="text-xs text-muted-foreground">· used {entry.hit_count}x</span>
                ) : null}
              </div>

              <div className="mt-2 grid gap-2 md:grid-cols-2">
                <div>
                  <div className="text-xs font-medium text-muted-foreground">Customer wording</div>
                  <div className="mt-0.5 break-words text-sm">{entry.source_text}</div>
                </div>
                <div>
                  <div className="text-xs font-medium text-muted-foreground">GGPL description</div>
                  {editing?.id === entry.id ? (
                    <textarea
                      className="mt-0.5 min-h-16 w-full resize-y rounded-md border border-input bg-background px-2 py-1 text-sm outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      value={editing.text}
                      onChange={(event) => setEditing({ id: entry.id, text: event.target.value })}
                    />
                  ) : (
                    <div className="mt-0.5 break-words text-sm font-medium">{entry.ggpl_description || "—"}</div>
                  )}
                </div>
              </div>

              {Object.keys(entry.fields || {}).length ? (
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(entry.fields).map(([field, value]) => (
                    <Badge key={field} variant="outline" className="font-normal">
                      {field}: {String(value)}
                    </Badge>
                  ))}
                </div>
              ) : null}

              {entry.note ? <div className="mt-2 text-xs text-muted-foreground">{entry.note}</div> : null}

              {canCurate ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {editing?.id === entry.id ? (
                    <>
                      <Button size="sm" onClick={() => void saveEdit()} disabled={busyId === entry.id}>
                        <Check className="h-4 w-4" />Save
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setEditing(null)}>
                        <X className="h-4 w-4" />Cancel
                      </Button>
                    </>
                  ) : (
                    <>
                      {entry.status !== "approved" ? (
                        <Button size="sm" onClick={() => void act(entry, "approve")} disabled={busyId === entry.id}>
                          <Check className="h-4 w-4" />Make permanent
                        </Button>
                      ) : null}
                      {entry.status !== "rejected" ? (
                        <Button size="sm" variant="outline" onClick={() => void act(entry, "reject")} disabled={busyId === entry.id}>
                          <X className="h-4 w-4" />Retire
                        </Button>
                      ) : null}
                      <Button size="sm" variant="outline" onClick={() => setEditing({ id: entry.id, text: entry.ggpl_description })}>
                        Edit wording
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => void remove(entry)} disabled={busyId === entry.id}>
                        <Trash2 className="h-4 w-4" />Delete
                      </Button>
                    </>
                  )}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function SettingToggle({
  id,
  label,
  hint,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-2 rounded-md border bg-background px-3 py-2">
      <div>
        <Label htmlFor={id} className="text-sm">{label}</Label>
        <div className="text-xs text-muted-foreground">{hint}</div>
      </div>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </div>
  );
}

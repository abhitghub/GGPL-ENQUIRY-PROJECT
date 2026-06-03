"use client";

import * as React from "react";
import { AlertCircle, CheckCircle2, ChevronDown, ChevronUp, Clock3, ExternalLink, FileSearch, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getJobStatus, type JobStatusRead } from "@/lib/api";
import {
  BACKGROUND_JOBS_EVENT,
  BackgroundExtractionJob,
  listBackgroundJobs,
  removeBackgroundJob,
} from "@/lib/background-jobs";

type DisplayJob = BackgroundExtractionJob & {
  status: JobStatusRead["status"] | "checking";
  progress: number;
  message: string;
  parsedCount: number;
  skippedCount: number;
  error: string | null;
};

function openQuote(job: BackgroundExtractionJob) {
  if (!job.quoteId) return;
  window.location.href = `/quotes?quote=${job.quoteId}`;
}

function toDisplayJob(job: BackgroundExtractionJob): DisplayJob {
  return {
    ...job,
    status: "checking",
    progress: 0,
    message: "Waiting for processing to start...",
    parsedCount: 0,
    skippedCount: 0,
    error: null,
  };
}

function mergeActiveJobs(current: DisplayJob[], active: BackgroundExtractionJob[]) {
  const byId = new Map(current.map((job) => [job.id, job]));
  for (const job of active) {
    if (!byId.has(job.id)) byId.set(job.id, toDisplayJob(job));
  }
  return Array.from(byId.values());
}

function isTerminal(job: DisplayJob) {
  return job.status === "succeeded" || job.status === "failed";
}

function clampProgress(progress: number) {
  const percent = progress <= 1 ? progress * 100 : progress;
  return Math.max(0, Math.min(100, Math.round(percent)));
}

function formatElapsed(startedAt: string, now: number) {
  const elapsedSeconds = Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000));
  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  return minutes ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

export function BackgroundJobMonitor() {
  const [activeJobs, setActiveJobs] = React.useState<BackgroundExtractionJob[]>([]);
  const [displayJobs, setDisplayJobs] = React.useState<DisplayJob[]>([]);
  const [collapsed, setCollapsed] = React.useState(false);
  const [now, setNow] = React.useState(() => Date.now());
  const notifiedJobs = React.useRef(new Set<string>());

  React.useEffect(() => {
    const sync = () => {
      const jobs = listBackgroundJobs();
      setActiveJobs(jobs);
      setDisplayJobs((current) => mergeActiveJobs(current, jobs));
    };
    sync();
    window.addEventListener(BACKGROUND_JOBS_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(BACKGROUND_JOBS_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  React.useEffect(() => {
    if (!displayJobs.some((job) => !isTerminal(job))) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [displayJobs]);

  React.useEffect(() => {
    if (!activeJobs.length) return undefined;
    let cancelled = false;

    async function poll() {
      for (const job of listBackgroundJobs()) {
        try {
          const status = await getJobStatus(job.id);
          if (cancelled) return;
          setDisplayJobs((current) => current.map((item) => item.id === job.id ? {
            ...item,
            status: status.status,
            progress: clampProgress(status.progress),
            message: status.message || (status.status === "succeeded" ? "Item list ready" : "Processing enquiry..."),
            parsedCount: status.parsed_count,
            skippedCount: status.skipped_count,
            error: status.error,
          } : item));
          if (status.status === "succeeded") {
            removeBackgroundJob(job.id);
            if (!notifiedJobs.current.has(job.id)) {
              notifiedJobs.current.add(job.id);
              toast.success(`${job.label} is ready`, {
                description: `${status.parsed_count} item(s) added to the list.`,
                action: job.quoteId ? { label: "Open", onClick: () => openQuote(job) } : undefined,
              });
            }
          } else if (status.status === "failed") {
            removeBackgroundJob(job.id);
            if (!notifiedJobs.current.has(job.id)) {
              notifiedJobs.current.add(job.id);
              toast.error(`${job.label} failed`, {
                description: status.error ?? "Could not create the item list.",
                action: job.quoteId ? { label: "Open", onClick: () => openQuote(job) } : undefined,
              });
            }
          }
        } catch (error) {
          if (cancelled) return;
          const message = error instanceof Error ? error.message : "";
          if (message.includes("404")) {
            removeBackgroundJob(job.id);
            setDisplayJobs((current) => current.map((item) => item.id === job.id ? {
              ...item,
              status: "failed",
              message: "Processing status is no longer available.",
              error: "This job could not be found. Start the extraction again if the item list was not created.",
            } : item));
          }
        }
      }
    }

    void poll();
    const timer = window.setInterval(() => void poll(), 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [activeJobs]);

  function dismiss(jobId: string) {
    removeBackgroundJob(jobId);
    setDisplayJobs((current) => current.filter((job) => job.id !== jobId));
  }

  if (!displayJobs.length) return null;

  return (
    <div className="fixed bottom-4 left-4 z-40 w-[min(360px,calc(100vw-2rem))] rounded-lg border bg-background/95 shadow-lg backdrop-blur" aria-live="polite">
      <div className="flex items-center justify-between gap-3 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <FileSearch className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="truncate text-sm font-medium">Enquiry processing</span>
          <Badge variant="secondary">{displayJobs.length}</Badge>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={() => setCollapsed((current) => !current)} aria-label={collapsed ? "Show processing jobs" : "Hide processing jobs"}>
          {collapsed ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>
      </div>

      {!collapsed && (
        <div className="max-h-[420px] space-y-2 overflow-auto border-t p-2">
          {displayJobs.map((job) => {
            const progress = job.status === "succeeded" ? 100 : clampProgress(job.progress);
            return (
              <div key={job.id} className="rounded-md border bg-card p-2.5 text-xs">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 font-medium">
                      {job.status === "succeeded" && <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-green-600" />}
                      {job.status === "failed" && <AlertCircle className="h-3.5 w-3.5 shrink-0 text-red-600" />}
                      {!isTerminal(job) && <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />}
                      <span className="truncate">{job.label}</span>
                    </div>
                    <div className="mt-1 text-muted-foreground">{job.message}</div>
                  </div>
                  {isTerminal(job) && (
                    <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={() => dismiss(job.id)} aria-label={`Dismiss ${job.label}`}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>

                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div className={`h-full rounded-full transition-[width] ${job.status === "failed" ? "bg-red-500" : job.status === "succeeded" ? "bg-green-500" : "bg-primary"}`} style={{ width: `${progress}%` }} />
                </div>

                <div className="mt-1.5 flex items-center justify-between gap-2 text-muted-foreground">
                  <span>{progress}%</span>
                  <span className="flex items-center gap-1"><Clock3 className="h-3 w-3" />{formatElapsed(job.startedAt, now)}</span>
                </div>

                {job.status === "succeeded" && (
                  <div className="mt-2 text-green-700 dark:text-green-300">
                    {job.parsedCount} item(s) added{job.skippedCount ? `, ${job.skippedCount} skipped` : ""}
                  </div>
                )}
                {job.status === "failed" && (
                  <div className="mt-2 text-red-700 dark:text-red-300">{job.error || "Could not create the item list."}</div>
                )}
                {job.quoteId && (
                  <Button variant="ghost" size="sm" className="mt-1.5 h-7 px-1.5 text-xs" onClick={() => openQuote(job)}>
                    <ExternalLink className="h-3 w-3" />
                    Open enquiry
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

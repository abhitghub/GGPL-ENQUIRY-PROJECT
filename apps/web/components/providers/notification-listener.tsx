"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { toast } from "sonner";

import { API_BASE } from "@/lib/api";

// One work notification pushed by the API over SSE (see
// apps/api/app/services/notification_hub.py for the producer side).
export type WorkNotification = {
  id: string;
  kind: "workflow" | "enquiry_created" | "assignment" | "query";
  quote_id: string;
  customer: string;
  project_ref: string;
  stage: string;
  stage_label: string;
  title: string;
  message: string;
  by: string;
  at: string;
};

// Name of the window event re-broadcast for every incoming notification so any
// screen (e.g. the role dashboard) can refresh its data without its own stream.
export const WORK_NOTIFICATION_EVENT = "ggpl:work-notification";

// Mirrors PRICING_SCREEN_STEPS in role-dashboard-client.tsx: from pricing
// onward the work happens on the Quotations screen.
const PRICING_SCREEN_STEPS = new Set([
  "sent_for_pricing",
  "pricing_decision",
  "pricing_submitted",
  "quotation_generated",
  "quotation_sent_to_customer",
]);

function hrefFor(notification: WorkNotification): string {
  if (!notification.quote_id) return "/role-dashboard";
  return PRICING_SCREEN_STEPS.has(notification.stage)
    ? `/quotes/final?quote=${notification.quote_id}`
    : `/quotes?quote=${notification.quote_id}`;
}

/**
 * Keeps one Server-Sent Events connection open per tab and turns incoming
 * work notifications into: an in-app toast with an "Open" action, a browser
 * desktop notification when the tab is hidden, and a window event other
 * screens can listen to for live refresh. Mounted globally in AppProviders.
 */
export function NotificationListener() {
  const router = useRouter();
  const pathname = usePathname();
  // Dedupe across EventSource reconnects (the server may not know a toast was
  // already shown before the connection dropped mid-flight).
  const seen = React.useRef<Set<string>>(new Set());
  const disabled = pathname === "/login";

  React.useEffect(() => {
    if (disabled || typeof window === "undefined" || !("EventSource" in window)) return;

    // Ask once for desktop-notification permission so alerts still reach the
    // user when the portal tab is in the background.
    if ("Notification" in window && Notification.permission === "default") {
      try {
        void Notification.requestPermission();
      } catch {
        // Older browsers use the callback form; ignore.
      }
    }

    let source: EventSource | null = null;
    let closed = false;
    let retryTimer: number | undefined;

    const handle = (notification: WorkNotification) => {
      if (!notification?.id || seen.current.has(notification.id)) return;
      seen.current.add(notification.id);
      window.dispatchEvent(new CustomEvent(WORK_NOTIFICATION_EVENT, { detail: notification }));
      const href = hrefFor(notification);
      toast.info(notification.title, {
        id: notification.id,
        description: notification.message,
        duration: 12000,
        action: { label: "Open", onClick: () => router.push(href) },
      });
      if (document.hidden && "Notification" in window && Notification.permission === "granted") {
        try {
          const desktop = new Notification(notification.title, {
            body: notification.message,
            tag: notification.id,
          });
          desktop.onclick = () => {
            window.focus();
            router.push(href);
            desktop.close();
          };
        } catch {
          // Desktop notifications are best-effort; the toast already fired.
        }
      }
    };

    const connect = () => {
      if (closed) return;
      source = new EventSource(`${API_BASE}/api/v1/notifications/stream`, { withCredentials: true });
      source.addEventListener("notification", (event) => {
        try {
          handle(JSON.parse((event as MessageEvent).data) as WorkNotification);
        } catch {
          // Malformed frame — skip it rather than break the stream.
        }
      });
      source.onerror = () => {
        // EventSource retries transient drops itself; only when the browser
        // gives up entirely (e.g. after a 401) do we retry on our own timer.
        if (source && source.readyState === EventSource.CLOSED) {
          source.close();
          retryTimer = window.setTimeout(connect, 15000);
        }
      };
    };

    connect();
    return () => {
      closed = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      source?.close();
    };
  }, [disabled, router]);

  return null;
}
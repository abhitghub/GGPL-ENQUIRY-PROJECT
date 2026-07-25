"use client";

import * as React from "react";

import {
  UPDATES_SEEN_EVENT,
  WORK_NOTIFICATION_EVENT,
  updatesSeenAt,
} from "@/components/providers/notification-listener";
import { listWorkUpdates } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Unread counter for the sidebar "Updates" item: how many persisted work
 * notifications arrived after the user last opened the Updates page. Refreshes
 * on every live SSE notification and clears when the page marks itself seen.
 */
export function UpdatesBadge({ collapsed = false }: { collapsed?: boolean }) {
  const [count, setCount] = React.useState(0);

  React.useEffect(() => {
    let active = true;
    const refresh = () => {
      listWorkUpdates()
        .then(({ items }) => {
          if (!active) return;
          const seenAt = updatesSeenAt();
          setCount(items.filter((item) => Date.parse(item.at) > seenAt).length);
        })
        .catch(() => undefined);
    };
    refresh();
    window.addEventListener(WORK_NOTIFICATION_EVENT, refresh);
    window.addEventListener(UPDATES_SEEN_EVENT, refresh);
    return () => {
      active = false;
      window.removeEventListener(WORK_NOTIFICATION_EVENT, refresh);
      window.removeEventListener(UPDATES_SEEN_EVENT, refresh);
    };
  }, []);

  if (!count) return null;
  if (collapsed) {
    return <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-primary" aria-label={`${count} unread updates`} />;
  }
  return (
    <span
      className={cn(
        "ml-auto inline-flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-primary px-1.5",
        "text-[11px] font-semibold leading-none text-primary-foreground",
      )}
    >
      {count > 99 ? "99+" : count}
    </span>
  );
}
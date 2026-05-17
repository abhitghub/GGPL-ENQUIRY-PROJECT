"use client";

import * as React from "react";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";

import { GasketChatWidget } from "@/components/chat/gasket-chat-widget";
import { PostHogProvider } from "@/lib/posthog";

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <PostHogProvider>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
        {children}
        <GasketChatWidget />
        <Toaster richColors position="top-right" closeButton />
      </ThemeProvider>
    </PostHogProvider>
  );
}

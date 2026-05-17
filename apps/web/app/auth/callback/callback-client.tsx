"use client";

import { Loader2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { setLocalSession } from "@/lib/auth/local-session";
import { getSupabaseBrowserClient } from "@/lib/auth/supabase";

export function AuthCallbackClient() {
  const router = useRouter();
  const searchParams = useSearchParams();

  React.useEffect(() => {
    async function finishAuth() {
      const next = searchParams.get("next") || "/dashboard";
      const code = searchParams.get("code");
      const supabase = getSupabaseBrowserClient();

      try {
        if (supabase && code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code);
          if (error) {
            throw error;
          }
        }
        setLocalSession();
        router.replace(next);
        router.refresh();
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Authentication callback failed");
        router.replace("/login");
      }
    }

    finishAuth();
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Loader2 className="h-5 w-5 animate-spin text-primary" aria-label="Completing sign in" />
    </div>
  );
}

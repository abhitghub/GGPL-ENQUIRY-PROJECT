"use client";

import { LOCAL_AUTH_COOKIE } from "@/lib/auth/supabase";

export function setLocalSession() {
  document.cookie = `${LOCAL_AUTH_COOKIE}=local; path=/; max-age=604800; samesite=lax`;
}

export function clearLocalSession() {
  document.cookie = `${LOCAL_AUTH_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

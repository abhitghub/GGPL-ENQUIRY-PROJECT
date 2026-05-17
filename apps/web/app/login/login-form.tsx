"use client";

import { ArrowRight, Mail } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { setLocalSession } from "@/lib/auth/local-session";
import { getSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/auth/supabase";

type AuthMode = "signin" | "signup";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("redirect") || "/dashboard";
  const [mode, setMode] = React.useState<AuthMode>("signin");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const supabaseConfigured = hasSupabaseConfig();

  function authCallbackUrl() {
    const next = encodeURIComponent(redirectTo);
    return `${window.location.origin}/auth/callback?next=${next}`;
  }

  async function completeLocalAuth() {
    setLocalSession();
    toast.success(mode === "signin" ? "Signed in" : "Account ready");
    router.push(redirectTo);
    router.refresh();
  }

  async function handlePasswordAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      if (!supabase) {
        await completeLocalAuth();
        return;
      }

      const authCall =
        mode === "signin"
          ? supabase.auth.signInWithPassword({ email, password })
          : supabase.auth.signUp({
              email,
              password,
              options: { emailRedirectTo: authCallbackUrl() },
            });
      const { data, error } = await authCall;
      if (error) {
        throw error;
      }
      if (data.session) {
        setLocalSession();
      }
      toast.success(mode === "signin" ? "Signed in" : "Check your email to confirm the account");
      router.push(redirectTo);
      router.refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleMagicLink() {
    if (!email) {
      toast.error("Enter an email address first");
      return;
    }
    setLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      if (!supabase) {
        await completeLocalAuth();
        return;
      }
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: authCallbackUrl() },
      });
      if (error) {
        throw error;
      }
      toast.success("Magic link sent");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Magic link failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle() {
    setLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      if (!supabase) {
        await completeLocalAuth();
        return;
      }
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: authCallbackUrl() },
      });
      if (error) {
        throw error;
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Google sign in failed");
      setLoading(false);
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="text-sm font-medium text-primary">Goodrich Gasket Pvt. Ltd.</div>
        <CardTitle>Quote workspace sign in</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={mode} onValueChange={(value) => setMode(value as AuthMode)}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="signin">Sign in</TabsTrigger>
            <TabsTrigger value="signup">Sign up</TabsTrigger>
          </TabsList>
          <TabsContent value={mode}>
            <form onSubmit={handlePasswordAuth} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete={mode === "signin" ? "current-password" : "new-password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={6}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {mode === "signin" ? "Continue" : "Create account"}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </form>
          </TabsContent>
        </Tabs>

        <div className="mt-4 grid gap-2">
          <Button type="button" variant="outline" onClick={handleMagicLink} disabled={loading}>
            <Mail className="h-4 w-4" aria-hidden="true" />
            Send magic link
          </Button>
          <Button type="button" variant="secondary" onClick={handleGoogle} disabled={loading}>
            Continue with Google
          </Button>
        </div>

        <div className="mt-4 flex items-center justify-between text-sm">
          <a className="text-primary underline-offset-4 hover:underline" href="/reset-password">
            Reset password
          </a>
          {!supabaseConfigured ? <span className="text-xs text-muted-foreground">Local dev auth</span> : null}
        </div>
      </CardContent>
    </Card>
  );
}

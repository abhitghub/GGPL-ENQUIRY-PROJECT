"use client";

import * as React from "react";
import Link from "next/link";
import { BarChart3, Calculator, CheckCircle2, ChevronDown, FileCheck2, FileQuestion, FileSearch, FileText, Layers3, LayoutDashboard, Menu, PanelLeftClose, PanelLeftOpen, Plus, Search, Settings, Truck } from "lucide-react";

import { ThemeToggle } from "@/components/app-shell/theme-toggle";
import { UserMenu } from "@/components/app-shell/user-menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { AppRole, getCurrentAppUser, setCurrentAppUser, USERS_CHANGED_EVENT } from "@/lib/auth/users";
import { getAccessSettingsRemote, getCurrentAppUserRemote, searchQuotes, type Quote } from "@/lib/api";
import { ACCESS_SETTINGS_CHANGED_EVENT, AppCapability, canRole, getAccessSettings, normalizeAccessSettings, saveAccessSettings } from "@/lib/auth/access-control";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: AppRole[];
  capability?: AppCapability;
};

type NavSection = {
  title: string;
  items: NavItem[];
  collapsible?: boolean;
};

function quoteHref(quote: Quote) {
  if (quote.stage === "po") return `/purchase-orders?quote=${quote.id}`;
  return ["quote_prep", "repricing", "sent"].includes(quote.stage) ? `/quotes/final?quote=${quote.id}` : `/quotes?quote=${quote.id}`;
}

function QuoteSearch() {
  const [query, setQuery] = React.useState("");
  const [results, setResults] = React.useState<Quote[]>([]);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    const clean = query.trim();
    if (clean.length < 2) {
      setResults([]);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      setLoading(true);
      searchQuotes(clean)
        .then(setResults)
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  return (
    <div className="relative hidden w-80 xl:block">
      <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search customer, enquiry or quote" className="bg-card pl-8" />
      {query.trim().length >= 2 ? (
        <div className="absolute right-0 top-11 z-50 w-full rounded-md border bg-popover p-1 shadow-md">
          {loading ? <div className="px-2 py-2 text-xs text-muted-foreground">Searching...</div> : null}
          {!loading && !results.length ? <div className="px-2 py-2 text-xs text-muted-foreground">No matching assigned work.</div> : null}
          {results.map((quote) => (
            <Link key={quote.id} href={quoteHref(quote)} className="block rounded px-2 py-2 text-sm hover:bg-muted" onClick={() => setQuery("")}>
              <div className="font-medium">{quote.customer || quote.quote_no || "Untitled enquiry"}</div>
              <div className="truncate text-xs text-muted-foreground">{quote.quote_no || quote.project_ref || "No reference"}</div>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}

const navSections: NavSection[] = [
  {
    title: "Start",
    items: [
      { href: "/dashboard", label: "My work", icon: LayoutDashboard, capability: "view_dashboard" },
    ],
  },
  {
    title: "Work",
    items: [
      { href: "/quotes", label: "Enquiries", icon: FileText, capability: "view_enquiry" },
      { href: "/material-planning", label: "Material planning", icon: Layers3, capability: "view_material_planning" },
      { href: "/quotes/final", label: "Quotations", icon: FileCheck2, capability: "view_quotation" },
      { href: "/purchase-orders", label: "Orders", icon: CheckCircle2, capability: "view_purchase_orders" },
    ],
  },
  {
    title: "More",
    collapsible: true,
    items: [
      { href: "/vendor-enquiries", label: "Vendor enquiries", icon: Truck, capability: "view_material_planning" },
      { href: "/doc-assistant", label: "Document assistant", icon: FileQuestion, capability: "view_doc_assistant" },
      { href: "/history", label: "Reports", icon: FileSearch, capability: "view_history" },
      { href: "/tools/converter", label: "Unit converter", icon: Calculator },
    ],
  },
  {
    title: "Admin",
    items: [
      { href: "/settings", label: "Settings", icon: Settings, capability: "view_settings" },
    ],
  },
];

function SidebarNav({ activePath, collapsed = false }: { activePath: string; collapsed?: boolean }) {
  const [role, setRole] = React.useState<AppRole>(() => getCurrentAppUser().role);
  const [accessSettings, setAccessSettings] = React.useState(() => getAccessSettings());
  React.useEffect(() => {
    const refresh = () => {
      setRole(getCurrentAppUser().role);
      setAccessSettings(getAccessSettings());
    };
    refresh();
    getCurrentAppUserRemote()
      .then((user) => {
        setCurrentAppUser(user);
        setRole(user.role);
      })
      .catch(() => undefined);
    getAccessSettingsRemote()
      .then((settings) => {
        const normalized = normalizeAccessSettings(settings);
        saveAccessSettings(normalized);
        setAccessSettings(normalized);
      })
      .catch(() => setAccessSettings(getAccessSettings()));
    window.addEventListener(USERS_CHANGED_EVENT, refresh);
    window.addEventListener(ACCESS_SETTINGS_CHANGED_EVENT, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(USERS_CHANGED_EVENT, refresh);
      window.removeEventListener(ACCESS_SETTINGS_CHANGED_EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);
  const visibleSections = navSections
    .map((section) => ({ ...section, items: section.items.filter((item) => !item.capability || canRole(role, item.capability, accessSettings)) }))
    .filter((section) => section.items.length);
  const activeSection = visibleSections.find((section) => section.items.some((item) => item.href === activePath))?.title;
  const [openSections, setOpenSections] = React.useState<Record<string, boolean>>(() => ({ More: activeSection === "More" }));

  React.useEffect(() => {
    if (!activeSection) return;
    setOpenSections((current) => ({ ...current, [activeSection]: true }));
  }, [activeSection]);

  return (
    <nav className={cn("space-y-5", collapsed && "space-y-4")}>
      {visibleSections.map((section) => {
        const sectionOpen = collapsed || !section.collapsible || openSections[section.title];
        return (
        <div key={section.title} className="space-y-1">
          {!collapsed && section.collapsible ? (
            <button
              type="button"
              className="flex w-full items-center justify-between rounded-md px-3 py-1 text-left text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              aria-expanded={Boolean(sectionOpen)}
              onClick={() => setOpenSections((current) => ({ ...current, [section.title]: !current[section.title] }))}
            >
              {section.title}
              <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", !sectionOpen && "-rotate-90")} />
            </button>
          ) : !collapsed ? (
            <div className="px-3 text-xs font-medium text-muted-foreground">{section.title}</div>
          ) : null}
          {sectionOpen && section.items.map((item) => {
            const Icon = item.icon;
            const active = activePath === item.href;
            return (
              <Link
                key={`${section.title}-${item.href}-${item.label}`}
                href={item.href}
                className={cn(
                  "flex items-start gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  collapsed && "justify-center px-2",
                  active && "bg-muted text-foreground hover:bg-muted",
                )}
                title={collapsed ? item.label : undefined}
              >
                <Icon className="mt-0.5 h-4 w-4 shrink-0" />
                {!collapsed && <span className="min-w-0 truncate">{item.label}</span>}
              </Link>
            );
          })}
        </div>
      )})}
    </nav>
  );
}

export function AppShell({
  children,
  activePath,
  title,
  breadcrumb,
}: {
  children: React.ReactNode;
  activePath: string;
  title: string;
  breadcrumb: string;
}) {
  const [role, setRole] = React.useState<AppRole>(() => getCurrentAppUser().role);
  const [accessSettings, setAccessSettings] = React.useState(() => getAccessSettings());
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  React.useEffect(() => {
    const refresh = () => {
      setRole(getCurrentAppUser().role);
      setAccessSettings(getAccessSettings());
    };
    refresh();
    getCurrentAppUserRemote()
      .then((user) => {
        setCurrentAppUser(user);
        setRole(user.role);
      })
      .catch(() => undefined);
    getAccessSettingsRemote()
      .then((settings) => {
        const normalized = normalizeAccessSettings(settings);
        saveAccessSettings(normalized);
        setAccessSettings(normalized);
      })
      .catch(() => setAccessSettings(getAccessSettings()));
    window.addEventListener(USERS_CHANGED_EVENT, refresh);
    window.addEventListener(ACCESS_SETTINGS_CHANGED_EVENT, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(USERS_CHANGED_EVENT, refresh);
      window.removeEventListener(ACCESS_SETTINGS_CHANGED_EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);
  return (
    <div className="min-h-screen bg-background">
      <aside className={cn("fixed inset-y-0 left-0 hidden flex-col border-r bg-card lg:flex", sidebarCollapsed ? "w-16" : "w-64")}>
        <div className="flex h-16 items-center gap-3 border-b px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <BarChart3 className="h-5 w-5" />
          </div>
          {!sidebarCollapsed && (
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">GGPL Quote</div>
              <div className="truncate text-xs text-muted-foreground">Goodrich Gasket Pvt. Ltd.</div>
            </div>
          )}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <SidebarNav activePath={activePath} collapsed={sidebarCollapsed} />
        </div>
      </aside>

      <div className={cn(sidebarCollapsed ? "lg:pl-16" : "lg:pl-64")}>
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 px-4 md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="hidden lg:inline-flex"
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={() => setSidebarCollapsed((value) => !value)}
            >
              {sidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
            </Button>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="flex flex-col overflow-hidden">
                <SheetHeader>
                  <SheetTitle>GGPL Quote</SheetTitle>
                </SheetHeader>
                <div className="mt-6 min-h-0 flex-1 overflow-y-auto pr-2">
                  <SidebarNav activePath={activePath} />
                </div>
              </SheetContent>
            </Sheet>
            <div className="min-w-0">
              <div className="truncate text-xs font-medium text-muted-foreground">{breadcrumb}</div>
              <h1 className="truncate text-lg font-semibold tracking-normal">{title}</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <QuoteSearch />
            {canRole(role, "create_enquiry", accessSettings) && (
              <Button size="sm" asChild>
                <Link href="/quotes?new=1"><Plus className="h-4 w-4" /><span className="hidden sm:inline">New enquiry</span></Link>
              </Button>
            )}
            <ThemeToggle />
            <UserMenu />
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1600px] px-4 py-6 md:px-6">{children}</main>
      </div>
    </div>
  );
}

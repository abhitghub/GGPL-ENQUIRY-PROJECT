"use client";

import * as React from "react";
import { Bot, FileText, Loader2, MessageSquare, Send, Trash2, Upload, User, X } from "lucide-react";
import { toast } from "sonner";

import { askDocAssistant, clearDocAssistantSession, removeDocAssistantDocument, uploadDocAssistantSession } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageIntro } from "@/components/app-shell/page-intro";
import { Input } from "@/components/ui/input";

const quickQuestions = [
  "Summarise the document for quotation review",
  "Extract gasket line items and technical requirements",
  "List missing details, exceptions, and commercial risks",
  "Find customer, project, enquiry, and revision references",
];

type Message = { role: "user" | "assistant"; content: string };

function formatAnswer(text: string) {
  return text.split("\n").map((line, index) => (
    <React.Fragment key={index}>
      {line}
      {index < text.split("\n").length - 1 && <br />}
    </React.Fragment>
  ));
}

export function DocAssistantClient() {
  const [sessionId, setSessionId] = React.useState("");
  const [documents, setDocuments] = React.useState<string[]>([]);
  const [chat, setChat] = React.useState<Message[]>([]);
  const [question, setQuestion] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const chatEndRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ block: "end" });
  }, [chat, loading]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    const totalBytes = Array.from(files).reduce((sum, file) => sum + file.size, 0);
    if (totalBytes > 8_000_000) toast.warning("Large documents may take longer and may be truncated for context.");
    try {
      const session = await uploadDocAssistantSession(files);
      setSessionId(session.id);
      setDocuments(session.document_names);
      setChat([]);
      setQuestion("");
      toast.success(`${session.document_names.length} document(s) loaded`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!sessionId) {
      toast.error("Upload at least one document first");
      return;
    }
    if (!trimmed || loading) return;
    setLoading(true);
    setChat((prev) => [...prev, { role: "user", content: trimmed }]);
    setQuestion("");
    try {
      const response = await askDocAssistant(sessionId, trimmed);
      setChat((prev) => [...prev, { role: "assistant", content: response.answer }]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Assistant failed");
    } finally {
      setLoading(false);
    }
  }

  async function removeDocument(name: string) {
    if (!sessionId) return;
    try {
      const session = await removeDocAssistantDocument(sessionId, name);
      setDocuments(session.document_names);
      if (!session.document_names.length) {
        setSessionId("");
        setChat([]);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not remove document");
    }
  }

  async function resetAll() {
    if (sessionId) {
      try {
        await clearDocAssistantSession(sessionId);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Could not clear session");
      }
    }
    setSessionId("");
    setDocuments([]);
    setChat([]);
    setQuestion("");
  }

  return (
    <div className="space-y-3">
      <PageIntro title="Ask documents" description="Upload enquiry files, then ask for missing details, specifications, and quotation risks." />
      <div className="grid min-h-[calc(100vh-13rem)] gap-3 xl:grid-cols-[280px_minmax(0,1fr)]">
      <Card className="overflow-hidden">
        <CardHeader className="border-b px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2 text-base"><FileText className="h-4 w-4" />Documents</CardTitle>
            <Badge variant={sessionId ? "secondary" : "muted"}>{documents.length} loaded</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 p-3">
          <div className="rounded-md border border-dashed bg-muted/20 p-3">
            <Input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.xlsx,.xls,.xlsm,.csv,.txt"
              onChange={(event) => upload(event.target.files)}
              className="hidden"
            />
            <div className="mt-2 flex flex-wrap gap-2">
              <Button size="sm" onClick={() => fileInputRef.current?.click()}>
                <Upload className="h-4 w-4" />
                Add files
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setChat([])} disabled={!chat.length}>
                <Trash2 className="h-4 w-4" />
                Clear chat
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            {documents.map((name) => (
              <div key={name} className="flex items-center justify-between gap-2 rounded-md border bg-background px-3 py-2 text-sm">
                <div className="flex min-w-0 items-center gap-2">
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate">{name}</span>
                </div>
                <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={() => removeDocument(name)} aria-label={`Remove ${name}`}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            {!documents.length && (
              <div className="rounded-md border bg-background p-3 text-sm text-muted-foreground">Upload a PDF, Excel, Word, CSV, or text file.</div>
            )}
          </div>

          <details className="rounded-md border bg-background">
            <summary className="cursor-pointer px-3 py-2 text-sm font-medium">Quick prompts</summary>
            <div className="space-y-2 border-t p-2">
              {quickQuestions.map((item) => (
                <Button key={item} variant="secondary" className="h-auto w-full justify-start whitespace-normal text-left" onClick={() => ask(item)} disabled={!sessionId || loading}>
                  <Send className="h-4 w-4 shrink-0" />
                  {item}
                </Button>
              ))}
            </div>
          </details>

          <Button variant="secondary" size="sm" onClick={resetAll} disabled={!sessionId && !documents.length && !chat.length} className="w-full">
            <Trash2 className="h-4 w-4" />
            Reset session
          </Button>
        </CardContent>
      </Card>

      <Card className="flex min-h-0 flex-col overflow-hidden">
        <CardHeader className="border-b px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2 text-base"><Bot className="h-4 w-4" />Document Q&A</CardTitle>
            </div>
            <Badge variant={sessionId ? "secondary" : "outline"}>{sessionId ? "Ready" : "Upload first"}</Badge>
          </div>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col gap-3 p-3">
          <div className="min-h-0 flex-1 overflow-auto rounded-md border bg-background p-3">
            <div className="space-y-3">
              {chat.map((message, index) => (
                <div key={index} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  {message.role === "assistant" && (
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-muted">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}
                  <div className={`max-w-[84%] rounded-md border px-3 py-2 text-sm leading-6 ${message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted/50"}`}>
                    <div className="whitespace-pre-wrap">{formatAnswer(message.content)}</div>
                  </div>
                  {message.role === "user" && (
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border bg-primary text-primary-foreground">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Reading documents
                </div>
              )}
              {!chat.length && !loading && (
                <div className="flex h-[360px] items-center justify-center rounded-md border border-dashed bg-muted/20 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    Upload documents, then ask a question.
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </div>

          <div className="rounded-md border bg-card p-2">
            <textarea
              className="min-h-20 w-full resize-none rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  ask(question);
                }
              }}
              placeholder="Ask about missing details, risks, specifications, or customer requirements"
            />
            <div className="mt-2 flex justify-end">
              <Button size="sm" onClick={() => ask(question)} disabled={loading || !question.trim()}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Send
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      </div>
    </div>
  );
}

"use client";

import * as React from "react";
import { FileText, Send, Trash2, Upload, X } from "lucide-react";
import { toast } from "sonner";

import { askDocAssistant, clearDocAssistantSession, removeDocAssistantDocument, uploadDocAssistantSession } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const quickQuestions = [
  "Summarise this document",
  "List all gasket-related requirements",
  "What technical exceptions or risks should we clarify?",
  "Extract customer, project, and enquiry references",
];

type Message = { role: "user" | "assistant"; content: string };

export function DocAssistantClient() {
  const [sessionId, setSessionId] = React.useState("");
  const [documents, setDocuments] = React.useState<string[]>([]);
  const [chat, setChat] = React.useState<Message[]>([]);
  const [question, setQuestion] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    const totalBytes = Array.from(files).reduce((sum, file) => sum + file.size, 0);
    if (totalBytes > 8_000_000) toast.warning("Large documents may take longer and may be truncated for context.");
    try {
      const session = await uploadDocAssistantSession(files);
      setSessionId(session.id);
      setDocuments(session.document_names);
      setChat([]);
      toast.success(`${session.document_names.length} document(s) loaded`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed");
    }
  }

  async function ask(text: string) {
    if (!sessionId) {
      toast.error("Upload at least one document first");
      return;
    }
    if (!text.trim()) return;
    setLoading(true);
    setChat((prev) => [...prev, { role: "user", content: text }]);
    setQuestion("");
    try {
      const response = await askDocAssistant(sessionId, text);
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
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input type="file" multiple accept=".pdf,.docx,.xlsx,.xls,.xlsm,.csv,.txt" onChange={(event) => upload(event.target.files)} />
          <div className="space-y-2">
            {documents.map((name) => (
              <div key={name} className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
                <div className="flex min-w-0 items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <span className="truncate">{name}</span>
                </div>
                  <Button variant="ghost" size="icon" onClick={() => removeDocument(name)} aria-label={`Remove ${name}`}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            {!documents.length && <div className="rounded-md border p-3 text-sm text-muted-foreground">No document loaded.</div>}
          </div>
          <div className="grid gap-2">
            {quickQuestions.map((item) => (
              <Button key={item} variant="secondary" className="justify-start" onClick={() => ask(item)}>
                {item}
              </Button>
            ))}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setChat([])} className="flex-1">
              <Trash2 className="h-4 w-4" />
              Clear conversation
            </Button>
            <Button variant="destructive" onClick={resetAll} className="flex-1">
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Document Q&A</CardTitle>
          <Badge variant={sessionId ? "secondary" : "muted"}>{sessionId ? "Loaded" : "Waiting"}</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="min-h-[420px] rounded-md border bg-background p-4">
            <div className="space-y-3">
              {chat.map((message, index) => (
                <div key={index} className={`rounded-md px-3 py-2 text-sm ${message.role === "user" ? "ml-auto max-w-[80%] bg-primary text-primary-foreground" : "mr-auto max-w-[88%] bg-muted"}`}>
                  <div className="whitespace-pre-wrap">{message.content}</div>
                </div>
              ))}
              {!chat.length && <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">Upload documents and ask a question.</div>}
            </div>
          </div>
          <div className="grid gap-2 md:grid-cols-[1fr_auto]">
            <Input value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") ask(question); }} placeholder="Ask about the loaded documents" />
            <Button onClick={() => ask(question)} disabled={loading}>
              {loading ? <Upload className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Ask
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

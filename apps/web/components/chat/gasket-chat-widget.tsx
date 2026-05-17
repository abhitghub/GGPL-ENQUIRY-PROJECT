"use client";

import * as React from "react";
import { MessageCircle, Send, X } from "lucide-react";
import { toast } from "sonner";

import { chatCompletion } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Message = { role: "user" | "assistant"; content: string };

export function GasketChatWidget() {
  const [open, setOpen] = React.useState(false);
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  async function send() {
    const text = input.trim();
    if (!text) return;
    const userMessage: Message = { role: "user", content: text };
    const next: Message[] = [...messages, userMessage].slice(-20);
    setMessages(next);
    setInput("");
    setLoading(true);
    try {
      const response = await chatCompletion(next);
      const assistantMessage: Message = { role: "assistant", content: response.message.content };
      setMessages([...next, assistantMessage].slice(-20));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Button
        className="fixed bottom-5 right-5 z-40 h-12 w-12 rounded-full p-0 shadow-lg"
        onClick={() => setOpen(true)}
        aria-label="Open gasket chat"
      >
        <MessageCircle className="h-5 w-5" />
      </Button>
      {open && (
        <div className="fixed bottom-20 right-5 z-50 flex h-[520px] w-[min(380px,calc(100vw-2rem))] flex-col rounded-md border bg-card shadow-xl">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div>
              <div className="text-sm font-semibold">Gasket chat</div>
              <div className="text-xs text-muted-foreground">Last 20 messages</div>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close chat">
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex-1 space-y-3 overflow-auto p-4">
            {messages.map((message, index) => (
              <div key={index} className={`rounded-md px-3 py-2 text-sm ${message.role === "user" ? "ml-auto max-w-[82%] bg-primary text-primary-foreground" : "mr-auto max-w-[88%] bg-muted"}`}>
                {message.content}
              </div>
            ))}
            {!messages.length && <div className="pt-32 text-center text-sm text-muted-foreground">Ask a gasket-domain question.</div>}
          </div>
          <div className="grid grid-cols-[1fr_auto] gap-2 border-t p-3">
            <Input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") send(); }} placeholder="Ask about gaskets" />
            <Button onClick={send} disabled={loading}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

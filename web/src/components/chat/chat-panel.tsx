"use client";

import { useState, useTransition } from "react";
import { Loader2, Send, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { MessageItem, MessageList } from "@/components/chat/message-list";
import { askBusinessQuestion } from "@/actions/chat";

interface ChatPanelProps {
  businessId: string;
  initialMessages: MessageItem[];
}

export function ChatPanel({ businessId, initialMessages }: ChatPanelProps) {
  const [messages, setMessages] = useState<MessageItem[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isPending, startTransition] = useTransition();

  const handleSend = () => {
    const text = input.trim();
    if (!text || isPending) return;

    setInput("");
    const newMsg: MessageItem = { role: "user", content: text };
    setMessages((prev) => [...prev, newMsg]);

    startTransition(async () => {
      const res = await askBusinessQuestion(businessId, text);
      if (res.answer) {
        setMessages((prev) => [...prev, { role: "assistant", content: res.answer }]);
      } else if (res.error) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${res.error}` },
        ]);
      }
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="flex h-[480px] flex-col border-border/80 bg-card/60 backdrop-blur-sm">
      <CardHeader className="border-b border-border/60 pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="size-4" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold">Ask Your Business</CardTitle>
              <CardDescription className="text-xs">
                AI answers grounded in verified metrics only
              </CardDescription>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col justify-between overflow-hidden p-4">
        <div className="flex-1 overflow-y-auto pr-2">
          <MessageList messages={messages} />
          {isPending && (
            <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" />
              <span>Analyzing verified data...</span>
            </div>
          )}
        </div>

        <div className="mt-3 flex items-center gap-2 border-t border-border/60 pt-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about sales, trends, or products..."
            disabled={isPending}
            className="flex-1"
          />
          <Button onClick={handleSend} disabled={isPending || !input.trim()} size="icon">
            {isPending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

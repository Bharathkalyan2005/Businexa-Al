import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";

export interface MessageItem {
  id?: string;
  role: "user" | "assistant";
  content: string;
  createdAt?: Date | string;
}

interface MessageListProps {
  messages: MessageItem[];
}

export function MessageList({ messages }: MessageListProps) {
  if (!messages || messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center text-sm text-muted-foreground">
        <Bot className="mb-2 size-8 text-primary/40" />
        <p className="font-medium text-foreground">Ask your data anything</p>
        <p className="max-w-xs text-xs">
          e.g., &quot;What drove our sales this month?&quot; or &quot;Which product has the highest margin?&quot;
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 pr-1">
      {messages.map((msg, idx) => {
        const isUser = msg.role === "user";
        return (
          <div
            key={msg.id || idx}
            className={cn(
              "flex gap-3 text-sm",
              isUser ? "flex-row-reverse" : "flex-row"
            )}
          >
            <div
              className={cn(
                "flex size-7 shrink-0 items-center justify-center rounded-full text-xs",
                isUser
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-foreground border border-border"
              )}
            >
              {isUser ? <User className="size-3.5" /> : <Bot className="size-3.5" />}
            </div>
            <div
              className={cn(
                "max-w-[85%] rounded-2xl px-4 py-2.5 shadow-sm leading-relaxed",
                isUser
                  ? "bg-primary text-primary-foreground rounded-tr-none"
                  : "bg-muted/40 text-foreground border border-border/80 rounded-tl-none"
              )}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

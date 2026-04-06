import { useEffect, useRef, useState } from "react"
import { clearChatHistory, sendChatMessage } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Loader2, Send, Trash2, ChevronDown, ChevronRight, Wrench } from "lucide-react"
import { cn } from "@/lib/utils"

interface ToolCall {
  name: string
  result?: string
  status: "running" | "done"
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  toolCalls: ToolCall[]
  isError?: boolean
}

function ToolCallItem({ tool }: { tool: ToolCall }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-2 rounded-md border border-border/60 bg-muted/40 text-xs overflow-hidden">
      <button
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/60 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <Wrench className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className="font-mono font-medium flex-1 truncate">{tool.name}</span>
        {tool.status === "running" ? (
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
        ) : open ? (
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        )}
      </button>
      {open && tool.result && (
        <pre className="px-3 py-2 border-t border-border/60 text-xs text-muted-foreground overflow-x-auto whitespace-pre-wrap break-words max-h-48 overflow-y-auto">
          {tool.result}
        </pre>
      )}
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user"
  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "h-8 w-8 shrink-0 rounded-full flex items-center justify-center text-xs font-semibold select-none",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground border border-border"
        )}
      >
        {isUser ? "U" : "AI"}
      </div>
      <div className={cn("max-w-[75%] space-y-1", isUser ? "items-end" : "items-start")}>
        {msg.toolCalls.length > 0 && !isUser && (
          <div className="space-y-1">
            {msg.toolCalls.map((tool, i) => (
              <ToolCallItem key={i} tool={tool} />
            ))}
          </div>
        )}
        {(msg.content || (!msg.content && msg.toolCalls.length === 0)) && (
          <div
            className={cn(
              "rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words",
              isUser
                ? "bg-primary text-primary-foreground rounded-tr-sm"
                : msg.isError
                ? "bg-destructive/10 text-destructive border border-destructive/20 rounded-tl-sm"
                : "bg-muted text-foreground rounded-tl-sm"
            )}
          >
            {msg.content || <span className="opacity-50 italic">Thinking...</span>}
          </div>
        )}
      </div>
    </div>
  )
}

let _msgIdCounter = 0
function newId() {
  return `msg-${++_msgIdCounter}-${Date.now()}`
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const [clearing, setClearing] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || isStreaming) return

    const userMsg: Message = {
      id: newId(),
      role: "user",
      content: text,
      toolCalls: [],
    }
    const assistantMsgId = newId()
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      toolCalls: [],
    }

    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setInput("")
    setIsStreaming(true)

    try {
      const response = await sendChatMessage(text)
      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() ?? ""

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event: { type: string; content?: string; name?: string; result?: string }
          try {
            event = JSON.parse(raw)
          } catch {
            continue
          }

          if (event.type === "token" && event.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, content: m.content + event.content } : m
              )
            )
          } else if (event.type === "tool_start" && event.name) {
            const toolCall: ToolCall = { name: event.name, status: "running" }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, toolCalls: [...m.toolCalls, toolCall] }
                  : m
              )
            )
          } else if (event.type === "tool_end" && event.name) {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantMsgId) return m
                const updatedTools = m.toolCalls.map((t) =>
                  t.name === event.name && t.status === "running"
                    ? { ...t, status: "done" as const, result: event.result }
                    : t
                )
                return { ...m, toolCalls: updatedTools }
              })
            )
          } else if (event.type === "error" && event.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: event.content!, isError: true }
                  : m
              )
            )
          }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? { ...m, content: "Failed to connect to agent. Please try again.", isError: true }
            : m
        )
      )
    } finally {
      setIsStreaming(false)
      textareaRef.current?.focus()
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  async function handleClear() {
    if (isStreaming || clearing) return
    setClearing(true)
    try {
      await clearChatHistory()
      setMessages([])
    } finally {
      setClearing(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border shrink-0">
        <div>
          <h1 className="text-xl font-semibold">Chat</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            AI finance assistant — powered by your MCP tools
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClear}
          disabled={isStreaming || clearing || messages.length === 0}
          className="text-muted-foreground hover:text-destructive"
        >
          {clearing ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
          <span className="ml-1.5">Clear</span>
        </Button>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto py-6 space-y-6 pr-2">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground gap-3">
            <div className="text-4xl">💰</div>
            <p className="text-sm font-medium">Tanya apa saja tentang keuanganmu</p>
            <div className="flex flex-wrap gap-2 justify-center mt-2">
              {[
                "Berapa saldo saya?",
                "Tampilkan pengeluaran bulan ini",
                "Berapa ready to assign saya?",
                "Bantu saya mulai budgeting",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion)
                    textareaRef.current?.focus()
                  }}
                  className="text-xs px-3 py-1.5 rounded-full border border-border hover:bg-muted transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 pt-4 border-t border-border">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ketik pesan... (Enter untuk kirim, Shift+Enter untuk baris baru)"
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none rounded-xl border border-input bg-background px-4 py-3 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50 max-h-32 overflow-y-auto"
            style={{ minHeight: "48px" }}
            onInput={(e) => {
              const t = e.currentTarget
              t.style.height = "auto"
              t.style.height = `${Math.min(t.scrollHeight, 128)}px`
            }}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="h-12 w-12 rounded-xl shrink-0"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="text-[11px] text-muted-foreground text-center mt-2">
          Jawaban AI bisa salah. Selalu verifikasi angka penting.
        </p>
      </div>
    </div>
  )
}

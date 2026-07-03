"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Send, MessageSquare, Plus, Trash2, Brain } from "lucide-react";
import { chatApi, streamChat } from "@/lib/api";

interface Message { id: string; role: "user" | "assistant"; content: string; tokens_used?: number; }
interface Conversation { id: string; title: string; last_message?: string; message_count: number; }

const SUGGESTED = [
  "What caused our last production incident?",
  "Which deployment has the most rollbacks?",
  "What's the safe state if error rate spikes?",
  "Summarize all incidents from the past month",
];

// ─── MessageBubble ────────────────────────────────────────────────────────────
function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 mb-4 animate-message-in ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-7 h-7 rounded-lg shrink-0 flex items-center justify-center text-xs font-bold ${
          isUser ? "bg-[#6366f1]" : "bg-[#141422] border border-[#1e1e2e]"
        }`}
      >
        {isUser ? "U" : <Brain size={14} className="text-[#6366f1]" />}
      </div>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "chat-user rounded-tr-sm"
            : "chat-ai rounded-tl-sm"
        }`}
      >
        <div className="whitespace-pre-wrap text-slate-200">{msg.content}</div>
        {msg.tokens_used != null && msg.tokens_used > 0 && (
          <div className="text-[10px] text-slate-600 mt-1 animate-fade-up stagger-1">
            {msg.tokens_used} tokens
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="flex gap-3 mb-4 animate-message-in">
      <div className="w-7 h-7 rounded-lg bg-[#141422] border border-[#1e1e2e] flex items-center justify-center">
        <Brain size={14} className="text-[#6366f1] animate-spin" style={{ animationDuration: "3s" }} />
      </div>
      <div className="px-4 py-3 rounded-2xl rounded-tl-sm chat-ai">
        <div className="flex gap-1 items-center py-1">
          <span className="typing-dot w-2 h-2 rounded-full bg-[#6366f1]" />
          <span className="typing-dot w-2 h-2 rounded-full bg-[#6366f1]" />
          <span className="typing-dot w-2 h-2 rounded-full bg-[#6366f1]" />
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function ChatInterface() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId]   = useState<string | null>(null);
  const [messages, setMessages]           = useState<Message[]>([]);
  const [input, setInput]                 = useState("");
  const [streaming, setStreaming]         = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const bottomRef  = useRef<HTMLDivElement>(null);
  const inputRef   = useRef<HTMLTextAreaElement>(null);
  const sendBtnRef = useRef<HTMLButtonElement>(null);
  const inputWrapRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    try { setConversations(await chatApi.getConversations()); } catch {}
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const loadMessages = async (convId: string) => {
    setActiveConvId(convId);
    try {
      const msgs = await chatApi.getMessages(convId);
      setMessages(msgs);
    } catch {}
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || streaming) return;

    // Animate send button
    const btn = sendBtnRef.current;
    if (btn) {
      btn.classList.add("animate-scale-spring");
      setTimeout(() => btn.classList.remove("animate-scale-spring"), 400);
    }

    setInput("");
    setStreaming(true);
    setStreamingText("");

    // Optimistic user message
    const tmpId = "tmp-" + Date.now();
    setMessages(m => [...m, { id: tmpId, role: "user", content: text }]);

    let convId = activeConvId;
    let aiText = "";

    try {
      await streamChat(
        text,
        convId,
        (chunk, cid) => {
          if (cid && !convId) { convId = cid; setActiveConvId(cid); }
          aiText += chunk;
          setStreamingText(aiText);
        },
        (cid, tokens) => {
          if (cid) { convId = cid; setActiveConvId(cid); }
          setMessages(m => [
            ...m,
            { id: "ai-" + Date.now(), role: "assistant", content: aiText, tokens_used: tokens },
          ]);
          setStreamingText("");
          loadConversations();
        },
      );
    } catch {
      setMessages(m => [
        ...m,
        { id: "err-" + Date.now(), role: "assistant", content: "Error: Could not reach Quorum AI. Check your OPENAI_API_KEY." },
      ]);
    } finally {
      setStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const newConversation = () => {
    setActiveConvId(null); setMessages([]); setStreamingText("");
  };

  const deleteConversation = async (id: string) => {
    await chatApi.deleteConversation(id);
    if (activeConvId === id) newConversation();
    loadConversations();
  };

  return (
    <div className="h-full flex">
      {/* ── Sidebar ── */}
      <div
        className="w-56 shrink-0 border-r border-[#1e1e2e] flex flex-col animate-slide-up"
        style={{
          background: "linear-gradient(180deg, #0e0e18 0%, #0a0a14 100%)",
          backdropFilter: "blur(12px)",
        }}
      >
        {/* New chat button */}
        <div className="p-3">
          <button
            onClick={newConversation}
            className="
              btn-ripple
              w-full flex items-center gap-2 px-3 py-2 rounded-xl
              border border-[#1e1e2e] hover:border-[#6366f1]/40
              text-sm text-slate-400 hover:text-slate-200
              transition-all duration-200 group
            "
          >
            <Plus
              size={13}
              className="transition-transform duration-300 group-hover:rotate-90"
            />
            New chat
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-2">
          {conversations.length === 0 && (
            <div className="text-xs text-slate-600 text-center mt-6 px-2">
              No conversations yet
            </div>
          )}
          {conversations.map((c, idx) => {
            const isActive = activeConvId === c.id;
            const stagger = `stagger-${Math.min(idx + 1, 6)}` as const;
            return (
              <div
                key={c.id}
                className={`
                  group flex items-start gap-1 p-2 rounded-xl mb-0.5 cursor-pointer
                  transition-all duration-200 relative
                  animate-fade-up ${stagger}
                  hover:translate-x-0.5
                  ${isActive
                    ? "bg-[#6366f1]/15 border border-[#6366f1]/20"
                    : "hover:bg-[#141422] border border-transparent"
                  }
                `}
                onClick={() => loadMessages(c.id)}
              >
                {/* Active left border indicator */}
                {isActive && (
                  <div
                    className="absolute left-0 top-2 bottom-2 w-0.5 rounded-r-full bg-[#6366f1] animate-slide-up"
                    style={{ animationDuration: "200ms" }}
                  />
                )}
                <MessageSquare size={12} className="text-slate-500 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-slate-300 truncate">{c.title}</div>
                  <div className="text-[10px] text-slate-600">{c.message_count} messages</div>
                </div>
                {/* Delete button — slides in from right on group hover */}
                <button
                  onClick={e => { e.stopPropagation(); deleteConversation(c.id); }}
                  className="
                    opacity-0 translate-x-2 group-hover:opacity-100 group-hover:translate-x-0
                    transition-all duration-200 p-0.5
                    text-slate-600 hover:text-[#ef4444]
                    active:scale-90
                  "
                >
                  <Trash2 size={11} />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Main chat area ── */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Empty / welcome state */}
          {messages.length === 0 && !streaming && (
            <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
              <div className="w-14 h-14 rounded-2xl bg-[#6366f1]/15 border border-[#6366f1]/20 flex items-center justify-center animate-scale-spring">
                <Brain size={28} className="text-[#6366f1]" />
              </div>
              <div>
                <div className="text-lg font-bold text-white mb-2 animate-fade-up stagger-1">
                  Quorum AI
                </div>
                <div className="text-sm text-slate-500 max-w-sm animate-fade-up stagger-2">
                  Ask me anything about your production history. I have memory of every deployment, incident, and rollback.
                </div>
              </div>

              {/* Suggested queries */}
              <div className="grid grid-cols-2 gap-2 w-full max-w-lg">
                {SUGGESTED.map((q, i) => {
                  const stagger = `stagger-${Math.min(i + 1, 6)}` as const;
                  return (
                    <button
                      key={q}
                      onClick={() => { setInput(q); inputRef.current?.focus(); }}
                      className={`
                        card-hover animate-scale-spring ${stagger}
                        text-left text-xs px-3 py-2.5 rounded-xl
                        border border-[#1e1e2e] bg-[#0e0e18]
                        hover:border-[#6366f1]/40 hover:bg-[#141422]
                        text-slate-400 hover:text-slate-200
                        transition-all duration-200 leading-relaxed
                      `}
                    >
                      {q}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map(m => <MessageBubble key={m.id} msg={m} />)}

          {/* Streaming bubble */}
          {streamingText && (
            <div className="flex gap-3 mb-4 animate-message-in">
              <div className="w-7 h-7 rounded-lg bg-[#141422] border border-[#1e1e2e] flex items-center justify-center">
                <Brain
                  size={14}
                  className="text-[#6366f1]"
                  style={{ animation: "spin 3s linear infinite" }}
                />
              </div>
              <div className="max-w-[75%] rounded-2xl rounded-tl-sm px-4 py-3 text-sm chat-ai">
                <div className="whitespace-pre-wrap text-slate-200">{streamingText}</div>
                {/* Blinking cursor */}
                <span className="w-0.5 h-4 bg-[#6366f1] inline-block ml-0.5 animate-pulse rounded-sm" />
              </div>
            </div>
          )}

          {/* Three-dot typing indicator (before first chunk arrives) */}
          {streaming && !streamingText && <TypingIndicator />}

          <div ref={bottomRef} />
        </div>

        {/* ── Input area ── */}
        <div className="p-4 border-t border-[#1e1e2e]">
          <div
            ref={inputWrapRef}
            className="
              flex items-end gap-2
              bg-[#141422] border border-[#1e1e2e] rounded-2xl px-4 py-2
              focus-within:border-[#6366f1]/50 focus-within:ring-2 focus-within:ring-[#6366f1]/20
              focus-within:shadow-[0_0_16px_rgba(99,102,241,.08)]
              transition-all duration-300
            "
          >
            <textarea
              ref={inputRef}
              rows={1}
              className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-600 outline-none resize-none py-2 max-h-32"
              placeholder="Ask Quorum about your production history…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{ minHeight: "36px" }}
            />
            <button
              ref={sendBtnRef}
              onClick={handleSend}
              disabled={!input.trim() || streaming}
              className="
                w-8 h-8 rounded-xl bg-[#6366f1] hover:bg-[#4f46e5]
                flex items-center justify-center
                transition-all duration-200
                disabled:opacity-30 disabled:cursor-not-allowed
                shrink-0 mb-0.5
                hover:shadow-[0_0_12px_rgba(99,102,241,.4)]
                active:scale-95
              "
            >
              <Send size={14} className="text-white" />
            </button>
          </div>
          <div className="text-[10px] text-slate-700 text-center mt-2">
            Powered by Cognee graph-vector memory · Context persists across sessions
          </div>
        </div>
      </div>
    </div>
  );
}

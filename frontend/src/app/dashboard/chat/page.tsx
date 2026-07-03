"use client";
import { MessageSquare } from "lucide-react";
import ChatInterface from "@/components/ChatInterface";

export default function ChatPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="h-14 border-b border-[#1e1e2e] px-5 flex items-center gap-2 shrink-0">
        <MessageSquare size={15} className="text-[#6366f1]" />
        <span className="font-semibold text-white">AI Assistant</span>
        <span className="text-xs text-slate-600 ml-1">— Cognee memory · persistent context</span>
      </div>
      <div className="flex-1 overflow-hidden">
        <ChatInterface />
      </div>
    </div>
  );
}

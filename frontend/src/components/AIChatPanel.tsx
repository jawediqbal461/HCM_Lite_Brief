import { useState } from "react";
import api, { apiErrorMessage } from "../api/client";

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function AIChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSending(true);
    try {
      const res = await api.post("/ai/chat", { message: text });
      setMessages((m) => [...m, { role: "assistant", text: res.data.answer }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: apiErrorMessage(err) }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {open && (
        <div className="mb-3 w-80 h-96 bg-white rounded-lg shadow-xl border flex flex-col">
          <div className="px-3 py-2 border-b font-semibold bg-brand text-white rounded-t-lg flex justify-between items-center">
            <span>AI Assistant</span>
            <button onClick={() => setOpen(false)} className="text-white/80 hover:text-white">
              ✕
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 text-sm">
            {messages.length === 0 && (
              <div className="text-slate-400">Ask about attendance, leave, payroll or policy.</div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
                <div
                  className={`inline-block rounded px-2 py-1 max-w-[90%] ${
                    m.role === "user" ? "bg-brand text-white" : "bg-slate-100 text-slate-800"
                  }`}
                >
                  {m.text}
                </div>
                {m.role === "assistant" && <div className="text-[10px] text-slate-400 mt-0.5">AI-generated</div>}
              </div>
            ))}
            {sending && <div className="text-slate-400 text-xs">Thinking…</div>}
          </div>
          <div className="p-2 border-t flex gap-2">
            <input
              className="flex-1 border rounded px-2 py-1 text-sm"
              value={input}
              placeholder="Ask a question..."
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
            />
            <button className="bg-brand text-white rounded px-3 text-sm" onClick={send} disabled={sending}>
              Send
            </button>
          </div>
        </div>
      )}
      <button
        className="h-12 w-12 rounded-full bg-brand text-white shadow-lg flex items-center justify-center text-xl"
        onClick={() => setOpen((o) => !o)}
        title="AI Assistant"
      >
        AI
      </button>
    </div>
  );
}

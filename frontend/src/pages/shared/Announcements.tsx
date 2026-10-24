import { FormEvent, useEffect, useState } from "react";
import api from "../../api/client";
import { useAuth } from "../../context/AuthContext";

export default function Announcements() {
  const [items, setItems] = useState<any[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const { user } = useAuth();
  const canPost = user?.role === "admin" || user?.role === "hr";

  function load() {
    api.get("/announcements").then((r) => setItems(r.data));
  }
  useEffect(load, []);

  async function post(e: FormEvent) {
    e.preventDefault();
    await api.post("/announcements", { title, body });
    setTitle("");
    setBody("");
    load();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-brand-dark">Announcements</h1>
      {canPost && (
        <form onSubmit={post} className="bg-white rounded-lg shadow p-4 space-y-2">
          <input className="w-full border rounded px-2 py-1 text-sm" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <textarea className="w-full border rounded px-2 py-1 text-sm" placeholder="Message" value={body} onChange={(e) => setBody(e.target.value)} required />
          <button className="bg-brand text-white rounded px-4 py-1.5 text-sm">Post</button>
        </form>
      )}
      <div className="space-y-3">
        {items.map((a) => (
          <div key={a.id} className="bg-white rounded-lg shadow p-4">
            <div className="font-semibold">{a.title}</div>
            <div className="text-sm text-slate-600">{a.body}</div>
            <div className="text-xs text-slate-400 mt-1">{new Date(a.created_at).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import api from "../api/client";

export default function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<any[]>([]);

  function load() {
    api
      .get("/notifications")
      .then((r) => setItems(r.data))
      .catch(() => setItems([]));
  }
  useEffect(load, []);

  const unread = items.filter((n) => !n.read).length;

  async function markRead(id: number) {
    await api.post(`/notifications/${id}/read`);
    load();
  }

  async function markAllRead() {
    await Promise.all(items.filter((n) => !n.read).map((n) => api.post(`/notifications/${n.id}/read`)));
    load();
  }

  return (
    <div className="relative">
      <button
        className="relative rounded-full border bg-white w-9 h-9 flex items-center justify-center hover:bg-slate-50"
        onClick={() => {
          setOpen((o) => !o);
          if (!open) load();
        }}
        title="Notifications"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
      >
        <span aria-hidden>🔔</span>
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-600 text-white text-[10px] rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white border rounded-lg shadow-lg z-40">
          <div className="flex items-center justify-between px-3 py-2 border-b">
            <span className="font-semibold text-sm">Notifications</span>
            {unread > 0 && (
              <button className="text-xs text-brand underline" onClick={markAllRead}>
                Mark all read
              </button>
            )}
          </div>
          <ul className="max-h-72 overflow-y-auto text-sm">
            {items.map((n) => (
              <li key={n.id} className={`px-3 py-2 border-b last:border-0 ${n.read ? "text-slate-500" : "bg-brand/5"}`}>
                <div>{n.message}</div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-[11px] text-slate-400">{new Date(n.created_at).toLocaleString()}</span>
                  {!n.read && (
                    <button className="text-[11px] text-brand underline" onClick={() => markRead(n.id)}>
                      Mark read
                    </button>
                  )}
                </div>
              </li>
            ))}
            {items.length === 0 && <li className="px-3 py-6 text-center text-slate-400">Nothing yet.</li>}
          </ul>
        </div>
      )}
    </div>
  );
}

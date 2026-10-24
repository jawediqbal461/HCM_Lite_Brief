import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AIChatPanel from "./AIChatPanel";
import NotificationsBell from "./NotificationsBell";

interface NavItem {
  to: string;
  label: string;
}

export default function Layout({ title, nav }: { title: string; nav: NavItem[] }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-brand-dark text-white flex flex-col">
        <div className="p-4 text-lg font-bold border-b border-white/10">HCM Lite</div>
        <div className="px-4 py-2 text-xs uppercase tracking-wide text-white/50">{title}</div>
        <nav className="flex-1 px-2 space-y-1">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              className={({ isActive }) =>
                `block rounded px-3 py-2 text-sm ${isActive ? "bg-brand text-white" : "text-white/80 hover:bg-white/10"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-white/10 text-sm">
          <div className="mb-2 truncate">{user?.fullName}</div>
          <button
            className="w-full rounded bg-white/10 px-3 py-1.5 hover:bg-white/20"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-y-auto">
        <div className="flex justify-end mb-2">
          <NotificationsBell />
        </div>
        <Outlet />
      </main>
      <AIChatPanel />
    </div>
  );
}

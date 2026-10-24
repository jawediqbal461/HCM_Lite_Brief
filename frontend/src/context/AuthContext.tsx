import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import api from "../api/client";

export type Role = "admin" | "hr" | "employee";

interface AuthUser {
  role: Role;
  employeeId: number | null;
  fullName: string | null;
  mustChangePassword: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshMe() {
    const token = localStorage.getItem("hcm_token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await api.get("/auth/me");
      setUser({
        role: res.data.role,
        employeeId: res.data.employee_id,
        fullName: res.data.full_name,
        mustChangePassword: false,
      });
    } catch {
      localStorage.removeItem("hcm_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshMe();
  }, []);

  async function login(email: string, password: string) {
    const res = await api.post("/auth/login", { email, password });
    localStorage.setItem("hcm_token", res.data.access_token);
    setUser({
      role: res.data.role,
      employeeId: res.data.employee_id,
      fullName: res.data.full_name,
      mustChangePassword: res.data.must_change_password,
    });
  }

  function logout() {
    localStorage.removeItem("hcm_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

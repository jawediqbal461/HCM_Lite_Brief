import { Navigate, Outlet } from "react-router-dom";
import { Role, useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ allow }: { allow: Role[] }) {
  const { user, loading } = useAuth();

  if (loading) return <div className="p-8">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!allow.includes(user.role)) return <Navigate to={`/${user.role}`} replace />;

  return <Outlet />;
}

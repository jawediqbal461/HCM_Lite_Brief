import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import FirstRunSetup from "./pages/FirstRunSetup";
import ChangePassword from "./pages/ChangePassword";

import AdminDashboard from "./pages/admin/AdminDashboard";
import CompanySettings from "./pages/admin/CompanySettings";
import UserAccess from "./pages/admin/UserAccess";
import AuditLog from "./pages/admin/AuditLog";

import HRDashboard from "./pages/hr/HRDashboard";

import EmployeeDashboard from "./pages/employee/EmployeeDashboard";
import MyAttendance from "./pages/employee/MyAttendance";
import MyLeave from "./pages/employee/MyLeave";
import MyPayslips from "./pages/employee/MyPayslips";
import MyProfile from "./pages/employee/MyProfile";

import EmployeeDirectory from "./pages/shared/EmployeeDirectory";
import Employee360 from "./pages/shared/Employee360";
import AttendanceBoard from "./pages/shared/AttendanceBoard";
import LeaveRequests from "./pages/shared/LeaveRequests";
import Payroll from "./pages/shared/Payroll";
import Announcements from "./pages/shared/Announcements";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/first-run" element={<FirstRunSetup />} />
      <Route path="/change-password" element={<ChangePassword />} />

      <Route element={<ProtectedRoute allow={["admin"]} />}>
        <Route element={<Layout title="Admin" nav={adminNav} />}>
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/settings" element={<CompanySettings />} />
          <Route path="/admin/users" element={<UserAccess />} />
          <Route path="/admin/employees" element={<EmployeeDirectory canManage={false} detailBase="/admin/employees" />} />
          <Route path="/admin/employees/:id" element={<Employee360 backTo="/admin/employees" />} />
          <Route path="/admin/attendance" element={<AttendanceBoard canDecide={false} />} />
          <Route path="/admin/leave" element={<LeaveRequests canDecide={false} />} />
          <Route path="/admin/payroll" element={<Payroll />} />
          <Route path="/admin/audit" element={<AuditLog />} />
          <Route path="/admin/announcements" element={<Announcements />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allow={["hr"]} />}>
        <Route element={<Layout title="HR" nav={hrNav} />}>
          <Route path="/hr" element={<HRDashboard />} />
          <Route path="/hr/employees" element={<EmployeeDirectory canManage={true} detailBase="/hr/employees" />} />
          <Route path="/hr/employees/:id" element={<Employee360 backTo="/hr/employees" />} />
          <Route path="/hr/attendance" element={<AttendanceBoard canDecide={true} />} />
          <Route path="/hr/leave" element={<LeaveRequests canDecide={true} />} />
          <Route path="/hr/payroll" element={<Payroll />} />
          <Route path="/hr/announcements" element={<Announcements />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allow={["employee"]} />}>
        <Route element={<Layout title="Employee" nav={employeeNav} />}>
          <Route path="/employee" element={<EmployeeDashboard />} />
          <Route path="/employee/attendance" element={<MyAttendance />} />
          <Route path="/employee/leave" element={<MyLeave />} />
          <Route path="/employee/payslips" element={<MyPayslips />} />
          <Route path="/employee/profile" element={<MyProfile />} />
          <Route path="/employee/announcements" element={<Announcements />} />
        </Route>
      </Route>

      <Route path="/" element={<Landing />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

const adminNav = [
  { to: "/admin", label: "Dashboard" },
  { to: "/admin/settings", label: "Company setup" },
  { to: "/admin/users", label: "Users & access" },
  { to: "/admin/employees", label: "Employees" },
  { to: "/admin/attendance", label: "Attendance" },
  { to: "/admin/leave", label: "Leave records" },
  { to: "/admin/payroll", label: "Payroll" },
  { to: "/admin/audit", label: "Audit log" },
  { to: "/admin/announcements", label: "Announcements" },
];

const hrNav = [
  { to: "/hr", label: "Dashboard" },
  { to: "/hr/employees", label: "Employees" },
  { to: "/hr/attendance", label: "Attendance" },
  { to: "/hr/leave", label: "Leave approvals" },
  { to: "/hr/payroll", label: "Payroll" },
  { to: "/hr/announcements", label: "Announcements" },
];

const employeeNav = [
  { to: "/employee", label: "Dashboard" },
  { to: "/employee/attendance", label: "Attendance" },
  { to: "/employee/leave", label: "Leave" },
  { to: "/employee/payslips", label: "Payslips" },
  { to: "/employee/profile", label: "Profile" },
  { to: "/employee/announcements", label: "Announcements" },
];

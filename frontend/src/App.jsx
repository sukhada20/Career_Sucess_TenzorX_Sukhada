import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

import Landing from './pages/Landing';
import SignIn from './pages/SignIn';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import StudentProfile from './pages/StudentProfile';
import Heatmap from './pages/Heatmap';
import Reports from './pages/Reports';
import Admin from './pages/Admin';
import Institutes from './pages/Institutes';
import AgenticInsights from './pages/AgenticInsights';
import LoanApply from './pages/student/LoanApply';
import PreScreen from './pages/student/PreScreen';
import StudentDashboard from './pages/student/StudentDashboard';

import AppShell from './components/AppShell';
import ProtectedRoute from './components/ProtectedRoute';

const API_BASE = 'http://localhost:8001';
export { API_BASE };

function RoleHome() {
  // Reads localStorage directly so this fallback works without a hook ordering issue
  try {
    const raw = localStorage.getItem('placementiq_user');
    if (raw) {
      const u = JSON.parse(raw);
      if (u?.role === 'admin') return <Navigate to="/dashboard" replace />;
      if (u?.role === 'student') return <Navigate to="/me/dashboard" replace />;
    }
  } catch {}
  return <Navigate to="/" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/" element={<Landing />} />
        <Route path="/signin" element={<SignIn />} />

        {/* Admin / lender (protected, with sidebar shell) */}
        <Route element={<ProtectedRoute role="admin"><AppShell variant="admin" /></ProtectedRoute>}>
          <Route path="/dashboard"     element={<Dashboard />} />
          <Route path="/students"      element={<Portfolio />} />
          <Route path="/student/:id"   element={<StudentProfile />} />
          <Route path="/heatmap"       element={<Heatmap />} />
          <Route path="/reports"       element={<Reports />} />
          <Route path="/institutes"    element={<Institutes />} />
          <Route path="/agentic"       element={<AgenticInsights />} />
          <Route path="/admin"         element={<Admin />} />
        </Route>

        {/* Student / borrower (protected, with sidebar shell — student variant) */}
        <Route element={<ProtectedRoute role="student"><AppShell variant="student" /></ProtectedRoute>}>
          <Route path="/me/apply"      element={<LoanApply />} />
          <Route path="/me/prescreen"  element={<PreScreen />} />
          <Route path="/me/dashboard"  element={<StudentDashboard />} />
        </Route>

        {/* Catch-all → role-appropriate home */}
        <Route path="*" element={<RoleHome />} />
      </Routes>
    </BrowserRouter>
  );
}

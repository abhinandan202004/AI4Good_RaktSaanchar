import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { SubNavbar } from './components/SubNavbar';
import { LoginRegister } from './pages/LoginRegister';
import { PatientDashboard } from './pages/PatientDashboard';
import { DonorDashboard } from './pages/DonorDashboard';
import { BloodBankDashboard } from './pages/BloodBankDashboard';
import { CoordinatorDashboard } from './pages/CoordinatorDashboard';
import { ChatRoom } from './pages/ChatRoom';
import { Leaderboard } from './pages/Leaderboard';
import { ChatbotWidget } from './components/ChatbotWidget';

// Core Layout Wrapper for authenticated routes
const DashboardLayout: React.FC = () => {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="glass-panel p-8 flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-rose-500/20 border-t-rose-500"></div>
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400">Loading RaktaSanchaar...</span>
        </div>
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-transparent flex flex-col">
      <Navbar />
      <SubNavbar />
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
      <ChatbotWidget />
    </div>
  );
};

// Route Guard for specific roles
const RoleGuard: React.FC<{ allowedRoles: string[]; fallback: string }> = ({ allowedRoles, fallback }) => {
  const { user } = useAuth();
  
  if (!user) return <Navigate to="/login" replace />;
  
  if (allowedRoles.includes(user.role)) {
    return <Outlet />;
  }
  
  return <Navigate to={fallback} replace />;
};

// Main Routing Router
const AppRoutes: React.FC = () => {
  const { user, token } = useAuth();

  const getHomeRedirect = () => {
    if (!token || !user) return '/login';
    switch (user.role) {
      case 'patient': return '/patient';
      case 'donor': return '/donor';
      case 'blood_bank': return '/blood-bank';
      case 'coordinator':
      case 'admin': return '/coordinator';
      default: return '/login';
    }
  };

  return (
    <Routes>
      <Route path="/login" element={!token ? <LoginRegister /> : <Navigate to={getHomeRedirect()} replace />} />
      
      <Route element={<DashboardLayout />}>
        {/* Home Redirect to specific role dashboard */}
        <Route path="/" element={<Navigate to={getHomeRedirect()} replace />} />

        {/* Patient Only Routes */}
        <Route element={<RoleGuard allowedRoles={['patient']} fallback={getHomeRedirect()} />}>
          <Route path="/patient" element={<PatientDashboard />} />
        </Route>

        {/* Donor Only Routes */}
        <Route element={<RoleGuard allowedRoles={['donor']} fallback={getHomeRedirect()} />}>
          <Route path="/donor" element={<DonorDashboard />} />
        </Route>

        {/* Blood Bank Only Routes */}
        <Route element={<RoleGuard allowedRoles={['blood_bank']} fallback={getHomeRedirect()} />}>
          <Route path="/blood-bank" element={<BloodBankDashboard />} />
        </Route>

        {/* Coordinator / Admin Only Routes */}
        <Route element={<RoleGuard allowedRoles={['coordinator', 'admin']} fallback={getHomeRedirect()} />}>
          <Route path="/coordinator" element={<CoordinatorDashboard />} />
          <Route path="/map-view" element={<CoordinatorDashboard />} />
        </Route>

        {/* Shared Authenticated Routes */}
        <Route path="/chat" element={<ChatRoom />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
      </Route>

      <Route path="*" element={<Navigate to={getHomeRedirect()} replace />} />
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

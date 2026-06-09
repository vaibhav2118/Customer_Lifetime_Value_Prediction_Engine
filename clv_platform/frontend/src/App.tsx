import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LandingPage } from './pages/LandingPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { DashboardPage } from './pages/DashboardPage';
import { CohortPage } from './pages/CohortPage';
import { JourneyPage } from './pages/JourneyPage';
import { ForecastPage } from './pages/ForecastPage';
import { IntegrationsPage } from './pages/IntegrationsPage';
import { EnterprisePage } from './pages/EnterprisePage';

// Protected Route Guard
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/onboarding" replace />;
};

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Pages */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />

      {/* Authenticated Pages */}
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/cohorts" element={<ProtectedRoute><CohortPage /></ProtectedRoute>} />
      <Route path="/journey" element={<ProtectedRoute><JourneyPage /></ProtectedRoute>} />
      <Route path="/journeys-map" element={<ProtectedRoute><JourneyPage /></ProtectedRoute>} />
      <Route path="/forecasting" element={<ProtectedRoute><ForecastPage /></ProtectedRoute>} />
      <Route path="/integrations" element={<ProtectedRoute><IntegrationsPage /></ProtectedRoute>} />
      <Route path="/enterprise" element={<ProtectedRoute><EnterprisePage /></ProtectedRoute>} />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
};
export default App;

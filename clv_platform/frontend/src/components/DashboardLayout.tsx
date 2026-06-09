import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  BarChart3, User, Calendar, GitFork, TrendingUp, 
  Settings, LogOut, CheckSquare, ShieldCheck, Users, HelpCircle
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const DashboardLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const menuItems = [
    { name: "Executive Dashboard", path: "/dashboard", icon: BarChart3 },
    { name: "Customer Explorer", path: "/journey", icon: User },
    { name: "Cohort Analysis", path: "/cohorts", icon: Calendar },
    { name: "Journey Analytics", path: "/journeys-map", icon: GitFork },
    { name: "Revenue Forecasting", path: "/forecasting", icon: TrendingUp },
    { name: "Connectors & Integrations", path: "/integrations", icon: Settings },
    { name: "Enterprise Controls", path: "/enterprise", icon: ShieldCheck }
  ];

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 border-b md:border-b-0 md:border-r border-white/5 bg-slate-900/40 backdrop-blur-md p-6 flex flex-col justify-between">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3 mb-10">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-600 to-indigo-400 flex items-center justify-center">
              <BarChart3 className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              RetentionAI
            </span>
          </div>

          {/* Menus */}
          <nav className="space-y-1.5">
            {menuItems.map((item, idx) => {
              const Icon = item.icon;
              return (
                <NavLink 
                  key={idx}
                  to={item.path}
                  className={({ isActive }) => 
                    `flex items-center gap-3 text-xs font-semibold px-4 py-3 rounded-xl transition ${isActive ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/10' : 'text-slate-400 hover:text-white hover:bg-white/5'}`
                  }
                >
                  <Icon className="w-4 h-4" /> {item.name}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* User profile & Logout */}
        <div className="pt-6 border-t border-white/5 mt-8 md:mt-0">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center text-xs font-bold text-white uppercase">
              {user?.email[0] || 'U'}
            </div>
            <div className="text-left overflow-hidden">
              <span className="text-xs font-bold text-white block truncate">{user?.email || 'User Account'}</span>
              <span className="text-[10px] text-slate-500 block uppercase tracking-wider font-semibold">{user?.role || 'Guest'}</span>
            </div>
          </div>
          
          <button 
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-xs font-semibold text-white transition"
          >
            <LogOut className="w-3.5 h-3.5" /> Log Out
          </button>
        </div>
      </aside>

      {/* Main Panel wrapper */}
      <main className="flex-1 p-6 md:p-10 max-w-7xl mx-auto overflow-y-auto">
        {children}
      </main>
    </div>
  );
};

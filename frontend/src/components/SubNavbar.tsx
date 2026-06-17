import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Heart,
  Activity,
  Map,
  MessageSquare,
  Trophy,
  ShieldCheck
} from 'lucide-react';

export const SubNavbar: React.FC = () => {
  const { user } = useAuth();

  if (!user) return null;

  const getMenuItems = () => {
    const common = [
      { to: '/chat', label: 'Chat Rooms', icon: <MessageSquare className="w-3.5 h-3.5" /> },
    ];

    switch (user.role) {
      case 'patient':
        return [
          { to: '/patient', label: 'Patient Dashboard', icon: <Activity className="w-3.5 h-3.5" /> },
          ...common
        ];
      case 'donor':
        return [
          { to: '/donor', label: 'Donor Hub', icon: <Heart className="w-3.5 h-3.5" /> },
          { to: '/leaderboard', label: 'Leaderboard', icon: <Trophy className="w-3.5 h-3.5" /> },
          ...common
        ];
      case 'blood_bank':
        return [
          { to: '/blood-bank', label: 'Bank Inventory', icon: <ShieldCheck className="w-3.5 h-3.5" /> },
          ...common
        ];
      case 'coordinator':
      case 'admin':
        return [
          { to: '/coordinator', label: 'Coordinator Desk', icon: <LayoutDashboard className="w-3.5 h-3.5" /> },
          { to: '/map-view', label: 'System Map', icon: <Map className="w-3.5 h-3.5" /> },
          { to: '/leaderboard', label: 'Leaderboard', icon: <Trophy className="w-3.5 h-3.5" /> },
          ...common
        ];
      default:
        return common;
    }
  };

  const menuItems = getMenuItems();

  return (
    <div className="glass-panel mx-6 my-4 p-2 z-40 sticky top-[72px] shadow-sm max-w-[1600px] xl:mx-auto">
      <div className="mx-auto">
        <ul className="flex flex-wrap gap-2 md:gap-3 items-center">
          {menuItems.map((item) => (
            <li key={item.to} className="list-none">
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 py-2 px-4 rounded-full text-xs font-semibold transition-all duration-300 ${
                    isActive
                      ? 'bg-primary text-brand-dark dark:bg-brand-dark dark:text-brand-light shadow-sm scale-102'
                      : 'text-slate-500 hover:text-brand-dark dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100/60 dark:hover:bg-slate-900/30'
                  }`
                }
              >
                {item.icon}
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

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
    <div className="glass-nav border-b sticky top-[60px] z-40">
      <div className="max-w-[1600px] mx-auto px-6">
        <ul className="flex flex-wrap -mb-px text-xs font-bold text-slate-500 dark:text-slate-400 gap-6">
          {menuItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 py-3.5 px-0.5 border-b-2 transition-all duration-200 ${
                    isActive
                      ? 'border-rose-500 text-rose-500 dark:text-rose-400'
                      : 'border-transparent hover:text-slate-700 dark:hover:text-slate-200 hover:border-slate-350 dark:hover:border-slate-800'
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

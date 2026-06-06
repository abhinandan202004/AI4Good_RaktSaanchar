import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  HeartHandshake,
  Heart,
  Activity,
  Map,
  MessageSquare,
  Trophy,
  ShieldCheck,
  UserCheck
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();

  if (!user) return null;

  const getMenuItems = () => {
    const common = [
      { to: '/chat', label: 'Chat Rooms', icon: <MessageSquare className="w-5 h-5" /> },
    ];

    switch (user.role) {
      case 'patient':
        return [
          { to: '/patient', label: 'Patient Dashboard', icon: <Activity className="w-5 h-5" /> },
          ...common
        ];
      case 'donor':
        return [
          { to: '/donor', label: 'Donor Hub', icon: <Heart className="w-5 h-5" /> },
          { to: '/leaderboard', label: 'Leaderboard', icon: <Trophy className="w-5 h-5" /> },
          ...common
        ];
      case 'blood_bank':
        return [
          { to: '/blood-bank', label: 'Bank Inventory', icon: <ShieldCheck className="w-5 h-5" /> },
          ...common
        ];
      case 'coordinator':
      case 'admin':
        return [
          { to: '/coordinator', label: 'Coordinator Desk', icon: <LayoutDashboard className="w-5 h-5" /> },
          { to: '/map-view', label: 'System Map', icon: <Map className="w-5 h-5" /> },
          { to: '/leaderboard', label: 'Leaderboard', icon: <Trophy className="w-5 h-5" /> },
          ...common
        ];
      default:
        return common;
    }
  };

  const menuItems = getMenuItems();

  return (
    <div className="w-64 bg-base-100 border-r border-base-200 min-h-[calc(100vh-64px)] shadow-sm flex flex-col justify-between py-6">
      <ul className="menu menu-md w-full px-4 gap-1.5">
        <li className="menu-title px-4 text-xs font-bold uppercase tracking-wider text-base-content/40 mb-2">
          Navigation Desk
        </li>
        {menuItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3.5 px-4 py-3 rounded-xl font-semibold transition-all ${
                  isActive
                    ? 'bg-primary text-primary-content shadow-md shadow-primary/20 scale-[1.02]'
                    : 'text-base-content/70 hover:bg-base-200 hover:text-base-content'
                }`
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>

      {/* User profile small footer in sidebar */}
      <div className="px-6 pt-4 border-t border-base-200 mx-4">
        <div className="flex items-center gap-3">
          <div className="avatar placeholder">
            <div className="bg-primary text-primary-content rounded-xl w-10">
              <span className="text-lg uppercase font-extrabold">{user.full_name[0]}</span>
            </div>
          </div>
          <div className="overflow-hidden">
            <div className="font-bold text-sm truncate">{user.full_name}</div>
            <div className="text-xs text-base-content/40 font-semibold uppercase tracking-wider">{user.role}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

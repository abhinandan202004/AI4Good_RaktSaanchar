import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Bell, LogOut, Sun, Moon, Droplets, Code2, User as UserIcon } from 'lucide-react';
import api from '../services/api';
import { Notification } from '../types';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [theme, setTheme] = useState<string>(localStorage.getItem('theme') || 'emerald');
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const notifRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  // Sync theme with HTML attribute and Dark mode class
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'night') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Click outside to close dropdowns
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
      if (userRef.current && !userRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Poll notifications
  const fetchNotifications = async () => {
    if (!localStorage.getItem('token')) return;
    try {
      const resp = await api.get<Notification[]>('/notifications/');
      setNotifications(resp.data);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 5000);
    return () => clearInterval(interval);
  }, []);

  const markAllAsRead = async () => {
    try {
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const toggleTheme = () => {
    setTheme(prev => (prev === 'emerald' ? 'night' : 'emerald'));
  };

  const getRoleBadgeStyle = (role: string) => {
    switch (role) {
      case 'patient': return 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300';
      case 'donor': return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300';
      case 'blood_bank': return 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300';
      case 'coordinator': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
      default: return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
    }
  };

  return (
    <header className="glass-nav border-b sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
      {/* Brand */}
      <div className="flex items-center gap-2.5">
        <div className="p-2 bg-rose-500/10 dark:bg-rose-500/20 rounded-xl border border-rose-500/20">
          <Droplets className="text-rose-500 w-5.5 h-5.5 animate-pulse" />
        </div>
        <span className="text-lg font-black tracking-tight text-slate-800 dark:text-slate-100">
          Rakta<span className="text-rose-500">Sanchaar</span>
        </span>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-3.5">
        {/* Source Code */}
        <a 
          href="https://github.com/abhinandan202004/Rakt" 
          target="_blank" 
          rel="noopener noreferrer" 
          className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 dark:border-slate-800 hover:bg-slate-100/50 dark:hover:bg-slate-900/50 rounded-xl text-xs font-bold transition-all text-slate-600 dark:text-slate-300"
        >
          <Code2 className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Source code</span>
        </a>

        {/* Theme Toggle */}
        <button 
          onClick={toggleTheme} 
          className="p-2 border border-slate-200 dark:border-slate-800 hover:bg-slate-100/50 dark:hover:bg-slate-900/50 rounded-xl transition-all text-slate-600 dark:text-slate-300"
          title="Toggle Theme"
        >
          {theme === 'emerald' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4 text-amber-400" />}
        </button>

        {/* Notifications */}
        {user && (
          <div className="relative" ref={notifRef}>
            <button 
              onClick={() => setShowNotifications(!showNotifications)}
              className="p-2 border border-slate-200 dark:border-slate-800 hover:bg-slate-100/50 dark:hover:bg-slate-900/50 rounded-xl transition-all text-slate-600 dark:text-slate-300 relative"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[9px] font-bold text-white animate-bounce">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-3 w-80 glass-card p-4 z-50 border border-slate-200 dark:border-slate-800">
                <div className="flex justify-between items-center border-b border-slate-200/50 dark:border-slate-800/50 pb-2 mb-2">
                  <span className="font-bold text-sm text-slate-800 dark:text-slate-200">Notifications ({unreadCount})</span>
                  {unreadCount > 0 && (
                    <button onClick={markAllAsRead} className="text-xs text-rose-500 hover:underline font-semibold">
                      Mark all read
                    </button>
                  )}
                </div>
                <div className="max-h-60 overflow-y-auto flex flex-col gap-2 py-1">
                  {notifications.length === 0 ? (
                    <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500 font-medium">
                      No notifications yet
                    </div>
                  ) : (
                    notifications.map((notif) => (
                      <div
                        key={notif.id}
                        className={`p-2.5 rounded-xl border text-xs transition-all ${
                          notif.is_read
                            ? 'bg-slate-50/50 dark:bg-slate-900/30 border-slate-150 dark:border-slate-800/40 opacity-60'
                            : 'bg-rose-500/5 border-rose-500/15 dark:bg-rose-500/10 dark:border-rose-500/20 font-semibold'
                        }`}
                      >
                        <div className="text-[9px] text-rose-500 font-bold mb-0.5 uppercase tracking-wide">
                          {notif.type}
                        </div>
                        <div className="text-slate-800 dark:text-slate-100 leading-snug font-bold">{notif.title}</div>
                        <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 font-medium">{notif.body}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* User Dropdown */}
        {user && (
          <div className="relative flex items-center gap-3 pl-3 border-l border-slate-200 dark:border-slate-800" ref={userRef}>
            <div className="hidden md:flex flex-col text-right leading-none gap-0.5">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300">{user.full_name}</span>
              <span className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">
                {user.role.replace('_', ' ')}
              </span>
            </div>
            
            <button 
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center justify-center w-8.5 h-8.5 bg-rose-500/10 text-rose-500 hover:bg-rose-500/20 border border-rose-500/15 rounded-xl font-bold uppercase text-sm"
            >
              <span>{user.full_name[0]}</span>
            </button>

            {showUserMenu && (
              <div className="absolute right-0 top-10 mt-3 w-52 glass-card p-2 z-50 border border-slate-200 dark:border-slate-800">
                <div className="px-3 py-2 border-b border-slate-200/50 dark:border-slate-800/50 mb-1.5">
                  <div className="font-bold text-xs text-slate-800 dark:text-slate-200 truncate">{user.full_name}</div>
                  <div className="text-[10px] text-slate-400 dark:text-slate-500 truncate mt-0.5">{user.email}</div>
                  <span className={`inline-block mt-1.5 px-1.5 py-0.5 rounded-md text-[8px] font-bold uppercase ${getRoleBadgeStyle(user.role)}`}>
                    {user.role}
                  </span>
                </div>
                <button 
                  onClick={logout} 
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs font-bold text-rose-500 hover:bg-rose-500/5 rounded-xl transition-all"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Logout
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
};

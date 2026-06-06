import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, User as UserIcon, MapPin, Sparkles, LogIn, CheckCircle2 } from 'lucide-react';
import api from '../services/api';

export const LoginRegister: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<'patient' | 'donor' | 'blood_bank' | 'coordinator'>('patient');
  const [bloodGroup, setBloodGroup] = useState('');

  // Geolocation states for manual registration
  const [latitude, setLatitude] = useState<number | undefined>(undefined);
  const [longitude, setLongitude] = useState<number | undefined>(undefined);
  const [gettingLocation, setGettingLocation] = useState(false);
  const [locationError, setLocationError] = useState('');

  // General error state
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Request browser location
  const detectLocation = () => {
    setGettingLocation(true);
    setLocationError('');
    if (!navigator.geolocation) {
      setLocationError('Geolocation not supported by browser.');
      setGettingLocation(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude);
        setLongitude(pos.coords.longitude);
        setGettingLocation(false);
      },
      (err) => {
        setLocationError(`Error: ${err.message}. Please enter coordinates manually.`);
        setGettingLocation(false);
      }
    );
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      if (isRegister) {
        // 1. Register User
        const regResp = await api.post('/auth/register', {
          email,
          password,
          full_name: fullName,
          role,
          blood_group: (role === 'patient' || role === 'donor') ? bloodGroup : undefined,
        });

        // 2. Login User
        const loginResp = await api.post('/auth/login', { email, password });
        const { access_token, user: loggedUser } = loginResp.data;
        
        // Save token immediately in local storage before creating profiles
        localStorage.setItem('token', access_token);

        // 3. Create role-specific profiles
        if (role === 'patient') {
          await api.post('/patients/me', {
            blood_group_required: bloodGroup,
            units_required: 1,
            urgency: 'medium',
            city: 'Mumbai',
            state: 'Maharashtra',
            latitude: latitude || 19.0760,
            longitude: longitude || 72.8777,
          });
        } else if (role === 'donor') {
          await api.post('/donors/me', {
            blood_group: bloodGroup,
            age: 30,
            weight: 75,
            city: 'Mumbai',
            state: 'Maharashtra',
            latitude: latitude || 19.0760,
            longitude: longitude || 72.8777,
          });
        } else if (role === 'blood_bank') {
          await api.post('/blood-bank/profile', {
            hospital_name: `${fullName} Blood Bank`,
            contact_phone: '1234567890',
            address: 'Mumbai Central, Mumbai',
            latitude: latitude || 19.0760,
            longitude: longitude || 72.8777,
          });
        }

        await login(access_token, loggedUser);
        setSuccess('Account created and logged in!');
        setTimeout(() => navigate(getDashboardRoute(loggedUser.role)), 1000);
      } else {
        // Login Flow
        const loginResp = await api.post('/auth/login', { email, password });
        const { access_token, user: loggedUser } = loginResp.data;
        await login(access_token, loggedUser);
        setSuccess('Logged in successfully!');
        setTimeout(() => navigate(getDashboardRoute(loggedUser.role)), 1000);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getDashboardRoute = (uRole: string) => {
    switch (uRole) {
      case 'patient': return '/patient';
      case 'donor': return '/donor';
      case 'blood_bank': return '/blood-bank';
      case 'coordinator':
      case 'admin': return '/coordinator';
      default: return '/';
    }
  };

  // Developer Quick Logins definition
  const devUsers = [
    {
      title: 'Mumbai Patient (O+)',
      email: 'dev_patient@test.com',
      name: 'Mumbai Dev Patient',
      role: 'patient',
      profileData: {
        blood_group_required: 'O+',
        units_required: 1,
        urgency: 'medium',
        hospital_name: 'Mumbai Central Hospital',
        city: 'Mumbai',
        state: 'Maharashtra',
        latitude: 19.0760,
        longitude: 72.8777
      }
    },
    {
      title: 'Navi Mumbai Donor (O-, Near)',
      email: 'dev_donor_near@test.com',
      name: 'Navi Mumbai Dev Donor',
      role: 'donor',
      profileData: {
        blood_group: 'O-',
        age: 28,
        weight: 72,
        city: 'Navi Mumbai',
        state: 'Maharashtra',
        latitude: 19.0330,
        longitude: 73.0297
      }
    },
    {
      title: 'Pune Donor (O-, Far)',
      email: 'dev_donor_far@test.com',
      name: 'Pune Dev Donor',
      role: 'donor',
      profileData: {
        blood_group: 'O-',
        age: 32,
        weight: 80,
        city: 'Pune',
        state: 'Maharashtra',
        latitude: 18.5204,
        longitude: 73.8567
      }
    },
    {
      title: 'Mumbai Incompatible Donor (AB+)',
      email: 'dev_donor_inc@test.com',
      name: 'Mumbai Dev AB+ Donor',
      role: 'donor',
      profileData: {
        blood_group: 'AB+',
        age: 25,
        weight: 65,
        city: 'Mumbai',
        state: 'Maharashtra',
        latitude: 19.0760,
        longitude: 72.8777
      }
    },
    {
      title: 'Mumbai Blood Bank',
      email: 'dev_bank@test.com',
      name: 'Mumbai Dev Blood Bank',
      role: 'blood_bank',
      profileData: {
        hospital_name: 'Mumbai Central Blood Bank',
        contact_phone: '022-9876543',
        address: 'Mumbai Central, Mumbai, Maharashtra',
        latitude: 19.0760,
        longitude: 72.8777
      }
    },
    {
      title: 'System Coordinator',
      email: 'dev_coord@test.com',
      name: 'RaktaSanchaar Coordinator',
      role: 'coordinator',
      profileData: null
    }
  ];

  const triggerQuickLogin = async (devUser: typeof devUsers[0]) => {
    setError('');
    setSuccess('');
    setLoading(true);
    const pass = 'SecurePassword123';

    try {
      let loginToken = '';
      let loggedUser = null;

      // Try logging in
      try {
        const loginResp = await api.post('/auth/login', {
          email: devUser.email,
          password: pass
        });
        loginToken = loginResp.data.access_token;
        loggedUser = loginResp.data.user;
      } catch {
        // If login fails, register first
        await api.post('/auth/register', {
          email: devUser.email,
          password: pass,
          full_name: devUser.name,
          role: devUser.role,
          blood_group: devUser.profileData ? (devUser.profileData.blood_group_required || devUser.profileData.blood_group) : undefined,
        });
        const loginResp = await api.post('/auth/login', {
          email: devUser.email,
          password: pass
        });
        loginToken = loginResp.data.access_token;
        loggedUser = loginResp.data.user;

        // Save token in config headers for sub-requests
        localStorage.setItem('token', loginToken);

        // Seed profile
        if (devUser.role === 'patient' && devUser.profileData) {
          await api.post('/patients/me', devUser.profileData);
        } else if (devUser.role === 'donor' && devUser.profileData) {
          await api.post('/donors/me', devUser.profileData);
        } else if (devUser.role === 'blood_bank' && devUser.profileData) {
          await api.post('/blood-bank/profile', devUser.profileData);
        }
      }

      await login(loginToken, loggedUser);
      setSuccess(`Logged in as ${devUser.name}!`);
      setTimeout(() => navigate(getDashboardRoute(loggedUser.role)), 1000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Quick login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-60px)] flex items-center justify-center p-6 relative">
      
      <div className="max-w-6xl w-full grid grid-cols-1 md:grid-cols-12 gap-10 items-center">
        
        {/* Hero Section */}
        <div className="md:col-span-6 flex flex-col justify-center pr-6 py-8 md:sticky md:top-8 gap-5 animate-fade-in">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-500/10 dark:bg-rose-500/20 rounded-full text-xs font-black text-rose-500 uppercase tracking-widest w-fit border border-rose-500/10">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
            AI-Driven Blood Network
          </div>
          <h1 className="hero-heading-token">
            Next-gen dispatch, powered by <span className="hero-highlight-token">RaktSaanchar</span>
          </h1>
          <p className="hero-subtitle-token">
            A decentralized, real-time coordination platform connecting patients, donors, and blood banks. Powered by predictive XGBoost donor-ranking and automated Amazon SNS alerts.
          </p>

          {/* Quick Platform Stats */}
          <div className="grid grid-cols-3 gap-4 mt-4">
            <div className="glass-card p-4 border border-rose-500/10 bg-white/20 dark:bg-slate-900/10">
              <span className="block text-2xl font-black text-rose-500">98%</span>
              <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 tracking-wider">Match Rate</span>
            </div>
            <div className="glass-card p-4 border border-rose-500/10 bg-white/20 dark:bg-slate-900/10">
              <span className="block text-2xl font-black text-rose-500">&lt;10m</span>
              <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 tracking-wider">Response Time</span>
            </div>
            <div className="glass-card p-4 border border-rose-500/10 bg-white/20 dark:bg-slate-900/10">
              <span className="block text-2xl font-black text-rose-500">20+</span>
              <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 tracking-wider">Blood Banks</span>
            </div>
          </div>
        </div>

        {/* Right Stacked Column */}
        <div className="md:col-span-6 flex flex-col gap-6">
          
          {/* Main Authentication Card */}
          <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-8">
            <h2 className="text-2xl font-black text-slate-800 dark:text-slate-100 flex items-center gap-2">
              <Sparkles className="text-rose-500 w-6 h-6 animate-pulse" />
              {isRegister ? 'Create Account' : 'Welcome Back'}
            </h2>
            <p className="text-xs text-slate-400 dark:text-slate-500 font-bold mb-6 mt-1">
              {isRegister ? 'Join our life-saving donation network' : 'Log in to manage and accept blood requests'}
            </p>

            {error && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs p-3 rounded-xl font-bold mb-4">
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs p-3 rounded-xl font-bold mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-4.5 h-4.5" />
                <span>{success}</span>
              </div>
            )}

            <form onSubmit={handleAuth} className="flex flex-col gap-4">
              {isRegister && (
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    Full Name
                  </label>
                  <div className="relative">
                    <UserIcon className="absolute left-3.5 top-3 text-slate-400 w-4.5 h-4.5" />
                    <input
                      type="text"
                      placeholder="Jane Doe"
                      className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-slate-800 dark:text-slate-100"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required={isRegister}
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-3 text-slate-400 w-4.5 h-4.5" />
                  <input
                    type="email"
                    placeholder="email@example.com"
                    className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-slate-800 dark:text-slate-100"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-3 text-slate-400 w-4.5 h-4.5" />
                  <input
                    type="password"
                    placeholder="••••••••"
                    className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-slate-800 dark:text-slate-100"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>

              {isRegister && (
                <>
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                      Choose Role
                    </label>
                    <select
                      className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2.5 text-xs font-semibold text-slate-800 dark:text-slate-100"
                      value={role}
                      onChange={(e: any) => setRole(e.target.value)}
                    >
                      <option value="patient">Patient (Needs Blood)</option>
                      <option value="donor">Donor (Donates Blood)</option>
                      <option value="blood_bank">Blood Bank Desk</option>
                      <option value="coordinator">Coordinator Desk</option>
                    </select>
                  </div>

                  {(role === 'patient' || role === 'donor') && (
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                        Blood Group <span className="text-rose-500">*</span>
                      </label>
                      <select
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2.5 text-xs font-semibold text-slate-800 dark:text-slate-100"
                        value={bloodGroup}
                        onChange={(e) => setBloodGroup(e.target.value)}
                        required
                      >
                        <option value="">Select Blood Group</option>
                        <option value="A+">A+</option>
                        <option value="A-">A-</option>
                        <option value="B+">B+</option>
                        <option value="B-">B-</option>
                        <option value="AB+">AB+</option>
                        <option value="AB-">AB-</option>
                        <option value="O+">O+</option>
                        <option value="O-">O-</option>
                      </select>
                    </div>
                  )}

                  {role !== 'coordinator' && (
                    <div className="border border-slate-200/40 dark:border-slate-800/40 p-4.5 rounded-2xl bg-slate-100/30 dark:bg-slate-900/20">
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-xs font-extrabold flex items-center gap-1.5 text-slate-700 dark:text-slate-350">
                          <MapPin className="text-rose-500 w-4 h-4" />
                          Geolocation Coordinates
                        </span>
                        <button
                          type="button"
                          className="px-3 py-1 bg-rose-500 hover:bg-rose-600 text-white rounded-lg text-[10px] font-bold uppercase transition-all"
                          onClick={detectLocation}
                          disabled={gettingLocation}
                        >
                          {gettingLocation ? 'Detecting...' : 'Detect'}
                        </button>
                      </div>

                      {locationError && <p className="text-[10px] text-rose-500 font-bold mb-2">{locationError}</p>}

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <input
                            type="number"
                            step="any"
                            placeholder="Latitude"
                            className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-100"
                            value={latitude || ''}
                            onChange={(e) => setLatitude(parseFloat(e.target.value))}
                            required
                          />
                        </div>
                        <div>
                          <input
                            type="number"
                            step="any"
                            placeholder="Longitude"
                            className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-100"
                            value={longitude || ''}
                            onChange={(e) => setLongitude(parseFloat(e.target.value))}
                            required
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}

              <button 
                type="submit" 
                className="w-full bg-rose-500 hover:bg-rose-600 text-white font-bold py-2.5 px-4 rounded-xl shadow-md transition-all text-xs uppercase tracking-wider mt-2 flex items-center justify-center gap-1.5" 
                disabled={loading}
              >
                {loading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                {isRegister ? 'Sign Up' : 'Log In'}
              </button>
            </form>

            {/* Divider */}
            <div className="flex items-center justify-center my-6 gap-3 text-[10px] font-black uppercase tracking-wider text-slate-400">
              <span className="h-[1px] bg-slate-200/50 dark:bg-slate-800/50 flex-1"></span>
              <span>OR</span>
              <span className="h-[1px] bg-slate-200/50 dark:bg-slate-800/50 flex-1"></span>
            </div>

            <p className="text-center text-xs font-semibold text-slate-500 dark:text-slate-400">
              {isRegister ? 'Already have an account?' : "Don't have an account yet?"}{' '}
              <button
                type="button"
                className="text-rose-500 hover:underline font-bold"
                onClick={() => {
                  setIsRegister(!isRegister);
                  setError('');
                }}
              >
                {isRegister ? 'Log In here' : 'Sign Up here'}
              </button>
            </p>
          </div>

          {/* Developer Quick Login Panel */}
          <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6 h-fit">
            <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-1.5">
              <Sparkles className="text-rose-500 w-4.5 h-4.5 animate-pulse" />
              Dev Quick Login Desk
            </h3>
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold mb-4 mt-2 leading-normal">
              Click any profile below to immediately log in. The desk will auto-register and seed coordinate profiles in the database if they don't already exist.
            </p>

            <div className="flex flex-col gap-2.5">
              {devUsers.map((dev) => (
                <button
                  key={dev.email}
                  type="button"
                  onClick={() => triggerQuickLogin(dev)}
                  disabled={loading}
                  className="flex items-center justify-between w-full border border-slate-200/50 dark:border-slate-800/50 bg-white/40 dark:bg-slate-900/10 hover:bg-rose-500/5 hover:border-rose-500/35 rounded-xl px-3.5 py-2.5 text-left transition-all duration-250 disabled:opacity-50"
                >
                  <div className="flex flex-col gap-0.5 leading-tight">
                    <span className="text-xs text-slate-700 dark:text-slate-350 font-bold">{dev.title}</span>
                    <span className="text-slate-400 dark:text-slate-500 text-[10px] font-semibold">{dev.email}</span>
                  </div>
                  <LogIn className="w-4 h-4 text-slate-400" />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

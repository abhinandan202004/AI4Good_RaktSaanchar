import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, User as UserIcon, MapPin, Sparkles, LogIn, CheckCircle2, Phone, Droplet } from 'lucide-react';
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

  // Verification state
  const [showVerification, setShowVerification] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  const [phone, setPhone] = useState('');

  // Password Reset state
  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [showForgotPasswordOtp, setShowForgotPasswordOtp] = useState(false);
  const [resetPassword, setResetPassword] = useState('');
  const [resetOtp, setResetOtp] = useState('');

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
        // 1. Register User (unverified)
        await api.post('/auth/register', {
          email,
          phone: phone || undefined,
          password,
          full_name: fullName,
          role,
          blood_group: (role === 'patient' || role === 'donor') ? bloodGroup : undefined,
        });

        setSuccess('Registration initiated! Verification code sent.');
        setShowVerification(true);
      } else {
        // Login Flow
        const loginResp = await api.post('/auth/login', { email, password });
        const { access_token } = loginResp.data;
        localStorage.setItem('token', access_token);
        const meResp = await api.get('/auth/me');
        const loggedUser = meResp.data;
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

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      // 1. Verify OTP Code
      await api.post('/auth/verify', { email, code: verificationCode });
      setSuccess('Verification successful! Logging in...');

      // 2. Login User
      const loginResp = await api.post('/auth/login', { email, password });
      const { access_token } = loginResp.data;
      
      // Save token immediately in local storage before creating profiles
      localStorage.setItem('token', access_token);
      const meResp = await api.get('/auth/me');
      const loggedUser = meResp.data;

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
      setSuccess('Profile configured and logged in!');
      setTimeout(() => navigate(getDashboardRoute(loggedUser.role)), 1000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await api.post('/auth/resend-otp', { email });
      setSuccess('A new verification code has been sent to your email!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resend code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPasswordRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setSuccess('Verification OTP sent to your email!');
      setShowForgotPasswordOtp(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send reset code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await api.post('/auth/reset-password', {
        email,
        code: resetOtp,
        new_password: resetPassword,
      });
      setSuccess('Password updated successfully! You can now log in.');
      setIsForgotPassword(false);
      setShowForgotPasswordOtp(false);
      setResetPassword('');
      setResetOtp('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Password reset failed. Please try again.');
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
        localStorage.setItem('token', loginToken);
        const meResp = await api.get('/auth/me');
        loggedUser = meResp.data;
      } catch {
        // If login fails, register first
        await api.post('/auth/register', {
          email: devUser.email,
          password: pass,
          full_name: devUser.name,
          role: devUser.role,
          blood_group: devUser.profileData ? (devUser.profileData.blood_group_required || devUser.profileData.blood_group) : undefined,
        });
        // Mock verify immediately using the static '123456' code
        await api.post('/auth/verify', {
          email: devUser.email,
          code: '123456'
        });
        const loginResp = await api.post('/auth/login', {
          email: devUser.email,
          password: pass
        });
        loginToken = loginResp.data.access_token;
        localStorage.setItem('token', loginToken);
        const meResp = await api.get('/auth/me');
        loggedUser = meResp.data;

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
    <div className="min-h-[calc(100vh-140px)] flex items-center justify-center p-6 relative">
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
        
        {/* Left Mobile App Splash Reference Mockup */}
        <div className="lg:col-span-6 flex flex-col justify-center items-center py-6 px-4">
          <div className="w-[320px] h-[640px] rounded-[48px] border-[10px] border-[#10354A] dark:border-brand-dark/80 bg-gradient-to-b from-[#DDEFF7] to-[#ffffff] dark:from-[#0C141C] dark:to-[#131E29] shadow-2xl relative overflow-hidden flex flex-col justify-between p-6">
            
            {/* Status Bar */}
            <div className="flex justify-between items-center text-[10px] font-bold text-brand-dark dark:text-slate-400">
              <span>09:41</span>
              <div className="flex gap-1.5 items-center">
                <span>5G</span>
                <div className="w-4.5 h-2.5 border border-brand-dark dark:border-slate-400 rounded-sm p-0.5 flex items-center">
                  <div className="w-3 h-full bg-brand-dark dark:bg-slate-400 rounded-2xs"></div>
                </div>
              </div>
            </div>

            {/* Hand & Connection Illustration Mockup */}
            <div className="flex-1 flex flex-col justify-center items-center relative my-4">
              <div className="text-center">
                <span className="text-3xl font-black tracking-tight text-brand-dark dark:text-white flex items-center justify-center gap-1.5">
                  <Droplet className="text-[#FF5E5E] fill-[#FF5E5E]/20 w-8 h-8 animate-pulse" />
                  rakt
                </span>
                <span className="text-[10px] tracking-widest text-[#2C5E7A] dark:text-brand-default uppercase font-extrabold mt-0.5 block">
                  saanchar
                </span>
              </div>
              
              {/* Central Circle connectors */}
              <div className="mt-8 relative w-40 h-40 flex items-center justify-center">
                <div className="absolute w-36 h-36 rounded-full border border-brand-default/50 dark:border-brand-dark/30 animate-pulse"></div>
                <div className="absolute w-24 h-24 rounded-full bg-brand-light/40 dark:bg-brand-dark/20 flex items-center justify-center">
                  <div className="w-14 h-14 rounded-full bg-white dark:bg-brand-darkCard shadow-md flex items-center justify-center">
                    <HeartIcon className="w-7 h-7 text-[#FF5E5E] fill-[#FF5E5E]" />
                  </div>
                </div>
                {/* Simulated connection line */}
                <div className="absolute h-0.5 bg-[#FF5E5E]/40 w-44 rotate-30 animate-pulse"></div>
              </div>
            </div>

            {/* Bottom Card Mockup */}
            <div className="bg-white dark:bg-[#1C2836] p-4.5 rounded-[24px] shadow-lg border border-brand-default/30 dark:border-brand-dark/40 flex flex-col gap-3.5">
              <div className="flex gap-1">
                <div className="h-1 w-8 bg-[#10354A] dark:bg-brand-default rounded-full"></div>
                <div className="h-1 w-4 bg-brand-default/40 rounded-full"></div>
                <div className="h-1 w-2 bg-brand-default/40 rounded-full"></div>
              </div>

              <div>
                <h3 className="font-extrabold text-sm text-brand-dark dark:text-white">Welcome to RaktaSanchaar 👋</h3>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold mt-1 leading-normal">
                  Your ultimate digital partner to request, rank, and search for compatible blood donors in real time.
                </p>
              </div>

              <div className="flex flex-col gap-2 mt-1">
                <button
                  onClick={() => {
                    setIsRegister(false);
                    setShowVerification(false);
                  }}
                  className="w-full bg-[#DDEFF7] hover:bg-[#C7E5F4] text-[#10354A] font-bold py-2 rounded-xl text-[10px] uppercase tracking-wider transition-all"
                >
                  Login
                </button>
                <button
                  onClick={() => {
                    setIsRegister(true);
                    setShowVerification(false);
                  }}
                  className="w-full bg-[#10354A] hover:bg-[#192D3D] text-white font-bold py-2 rounded-xl text-[10px] uppercase tracking-wider transition-all"
                >
                  Create account
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Stacked Column for Interactive Authentication Forms */}
        <div className="lg:col-span-6 flex flex-col gap-6 w-full">
          
          {/* Main Authentication Card */}
          <div className="glass-panel border border-brand-default/30 dark:border-brand-dark/40 p-8 shadow-md">
            <h2 className="text-2xl font-black text-brand-dark dark:text-slate-100 flex items-center gap-2">
              <Sparkles className="text-brand-dark dark:text-brand-default w-6 h-6 animate-pulse" />
              {isForgotPassword ? 'Reset Password' : (isRegister ? 'Create Account' : 'Welcome Back')}
            </h2>
            <p className="text-xs text-slate-400 dark:text-slate-500 font-bold mb-6 mt-1">
              {isForgotPassword ? 'Reset your account password via email verification' : (isRegister ? 'Join our life-saving donation network' : 'Log in to manage and accept blood requests')}
            </p>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] text-xs p-3 rounded-xl font-bold mb-4">
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div className="bg-emerald-550/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs p-3 rounded-xl font-bold mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-4.5 h-4.5" />
                <span>{success}</span>
              </div>
            )}

            {showVerification ? (
              <form onSubmit={handleVerify} className="flex flex-col gap-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                    Enter 6-Digit Verification Code
                  </label>
                  <div className="relative">
                    <CheckCircle2 className="absolute left-3.5 top-3 text-[#2C5E7A] w-4.5 h-4.5" />
                    <input
                      type="text"
                      maxLength={6}
                      placeholder="XXXXXX"
                      className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-brand-dark dark:text-slate-100 font-mono tracking-widest text-center"
                      value={verificationCode}
                      onChange={(e) => setVerificationCode(e.target.value)}
                      required
                    />
                  </div>
                  <p className="text-[10px] text-slate-400 font-semibold mt-2">
                    We've sent a 6-digit verification code to your email.
                  </p>
                </div>

                <button 
                  type="submit" 
                  className="w-full btn-pill-primary text-xs uppercase tracking-wider mt-2" 
                  disabled={loading}
                >
                  {loading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                  Verify & Continue
                </button>

                <div className="flex items-center justify-between mt-4">
                  <button
                    type="button"
                    className="text-xs font-bold text-slate-500 hover:underline"
                    onClick={() => {
                      setShowVerification(false);
                      setError('');
                    }}
                  >
                    Back to Register
                  </button>

                  <button
                    type="button"
                    className="text-xs font-bold text-brand-dark dark:text-brand-default hover:underline disabled:opacity-50"
                    onClick={handleResendOtp}
                    disabled={loading}
                  >
                    Resend Code
                  </button>
                </div>
              </form>
            ) : isForgotPassword ? (
              showForgotPasswordOtp ? (
                // Step 2: Verification code & Reset new password
                <form onSubmit={handleResetPassword} className="flex flex-col gap-4">
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                      Reset Verification OTP
                    </label>
                    <div className="relative">
                      <CheckCircle2 className="absolute left-3.5 top-3 text-[#2C5E7A] w-4.5 h-4.5" />
                      <input
                        type="text"
                        maxLength={6}
                        placeholder="XXXXXX"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-brand-dark dark:text-slate-100 font-mono tracking-widest text-center"
                        value={resetOtp}
                        onChange={(e) => setResetOtp(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                      New Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-3 text-[#2C5E7A] w-4.5 h-4.5" />
                      <input
                        type="password"
                        placeholder="••••••••"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-brand-dark dark:text-slate-100"
                        value={resetPassword}
                        onChange={(e) => setResetPassword(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="w-full btn-pill-primary text-xs uppercase tracking-wider mt-2"
                    disabled={loading}
                  >
                    {loading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                    Update Password
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setShowForgotPasswordOtp(false);
                      setError('');
                      setSuccess('');
                    }}
                    className="text-xs font-semibold text-brand-dark dark:text-brand-default hover:underline text-center mt-2"
                  >
                    Back
                  </button>
                </form>
              ) : (
                // Step 1: Request OTP for password reset
                <form onSubmit={handleForgotPasswordRequest} className="flex flex-col gap-4">
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-3 text-[#2C5E7A] w-4.5 h-4.5" />
                      <input
                        type="email"
                        placeholder="email@example.com"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-brand-dark dark:text-slate-100"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="w-full btn-pill-primary text-xs uppercase tracking-wider mt-2"
                    disabled={loading}
                  >
                    {loading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                    Send Verification Code
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setIsForgotPassword(false);
                      setError('');
                      setSuccess('');
                    }}
                    className="text-xs font-semibold text-brand-dark dark:text-brand-default hover:underline text-center mt-2"
                  >
                    Back to Log In
                  </button>
                </form>
              )
            ) : (
              <form onSubmit={handleAuth} className="flex flex-col gap-4">
                {isRegister && (
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                      Full Name
                    </label>
                    <div className="relative">
                      <UserIcon className="absolute left-3.5 top-3 text-[#2C5E7A] w-4.5 h-4.5" />
                      <input
                        type="text"
                        placeholder="Jane Doe"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-brand-dark dark:text-slate-100"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        required={isRegister}
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-3 text-[#2C5E7A] w-4.5 h-4.5" />
                    <input
                      type="email"
                      placeholder="email@example.com"
                      className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-brand-dark dark:text-slate-100"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                {isRegister && (
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                      Phone Number (Optional)
                    </label>
                    <div className="relative">
                      <Phone className="absolute left-3.5 top-3 text-[#2C5E7A] w-4.5 h-4.5" />
                      <input
                        type="tel"
                        placeholder="+919876543210 (Optional)"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-brand-dark dark:text-slate-100"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-3 text-[#2C5E7A] w-4.5 h-4.5" />
                    <input
                      type="password"
                      placeholder="••••••••"
                      className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl pl-11 pr-3 py-2 text-sm transition-all text-brand-dark dark:text-slate-100"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>
                  {!isRegister && (
                    <div className="flex justify-end mt-1.5">
                      <button
                        type="button"
                        onClick={() => {
                          setIsForgotPassword(true);
                          setError('');
                          setSuccess('');
                        }}
                        className="text-xs font-semibold text-[#2C5E7A] dark:text-[#C7E5F4] hover:underline"
                      >
                        Forgot Password?
                      </button>
                    </div>
                  )}
                </div>

                {isRegister && (
                  <>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                        Choose Role
                      </label>
                      <select
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2.5 text-xs font-semibold text-brand-dark dark:text-slate-100"
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
                        <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">
                          Blood Group <span className="text-[#FF5E5E]">*</span>
                        </label>
                        <select
                          className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2.5 text-xs font-semibold text-brand-dark dark:text-slate-100"
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
                      <div className="border border-brand-default/40 dark:border-brand-dark/50 p-4.5 rounded-2xl bg-brand-light/20 dark:bg-brand-dark/10">
                        <div className="flex justify-between items-center mb-3">
                          <span className="text-xs font-extrabold flex items-center gap-1.5 text-brand-dark dark:text-slate-350">
                            <MapPin className="text-[#FF5E5E] w-4 h-4" />
                            Geolocation Coordinates
                          </span>
                          <button
                            type="button"
                            className="px-3 py-1 bg-brand-dark hover:bg-brand-dark/90 text-white dark:bg-brand-default dark:text-brand-dark rounded-lg text-[10px] font-bold uppercase transition-all"
                            onClick={detectLocation}
                            disabled={gettingLocation}
                          >
                            {gettingLocation ? 'Detecting...' : 'Detect'}
                          </button>
                        </div>

                        {locationError && <p className="text-[10px] text-[#FF5E5E] font-bold mb-2">{locationError}</p>}

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <input
                              type="number"
                              step="any"
                              placeholder="Latitude"
                              className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/55 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-lg px-2.5 py-1.5 text-xs text-brand-dark dark:text-slate-100"
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
                              className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/55 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-lg px-2.5 py-1.5 text-xs text-brand-dark dark:text-slate-100"
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
                  className="w-full btn-pill-primary text-xs uppercase tracking-wider mt-2" 
                  disabled={loading}
                >
                  {loading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                  {isRegister ? 'Sign Up' : 'Log In'}
                </button>
              </form>
            )}

            {/* Divider */}
            <div className="flex items-center justify-center my-6 gap-3 text-[10px] font-black uppercase tracking-wider text-slate-400">
              <span className="h-[1px] bg-[#C7E5F4]/30 dark:bg-brand-dark/30 flex-1"></span>
              <span>OR</span>
              <span className="h-[1px] bg-[#C7E5F4]/30 dark:bg-brand-dark/30 flex-1"></span>
            </div>

            <p className="text-center text-xs font-semibold text-slate-500 dark:text-slate-400">
              {isRegister ? 'Already have an account?' : "Don't have an account yet?"}{' '}
              <button
                type="button"
                className="text-brand-dark dark:text-brand-default hover:underline font-bold"
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
          <div className="glass-panel border border-brand-default/30 dark:border-brand-dark/40 p-6 shadow-sm">
            <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/20 dark:border-brand-dark/30 pb-3 flex items-center gap-1.5">
              <Sparkles className="text-brand-dark dark:text-brand-default w-4.5 h-4.5 animate-pulse" />
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
                  className="flex items-center justify-between w-full border border-brand-default/30 dark:border-brand-dark/40 bg-brand-light/20 dark:bg-brand-dark/10 hover:bg-brand-light/50 dark:hover:bg-brand-dark/20 rounded-xl px-3.5 py-2.5 text-left transition-all duration-250 disabled:opacity-50"
                >
                  <div className="flex flex-col gap-0.5 leading-tight">
                    <span className="text-xs text-brand-dark dark:text-brand-light font-extrabold">{dev.title}</span>
                    <span className="text-slate-450 dark:text-slate-500 text-[10px] font-bold">{dev.email}</span>
                  </div>
                  <LogIn className="w-4 h-4 text-brand-dark dark:text-brand-light" />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper components since standard Lucide Heart might clash or be missing
const HeartIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
  </svg>
);

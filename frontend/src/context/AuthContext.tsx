import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';
import { User, UserRole, PatientProfile, DonorProfile, BloodBankProfile } from '../types';

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  token: string | null;
  patientProfile: PatientProfile | null;
  donorProfile: DonorProfile | null;
  bloodBankProfile: BloodBankProfile | null;
  loading: boolean;
  login: (token: string, user: User) => Promise<void>;
  logout: () => void;
  refreshProfiles: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [role, setRole] = useState<UserRole | null>(null);
  const [patientProfile, setPatientProfile] = useState<PatientProfile | null>(null);
  const [donorProfile, setDonorProfile] = useState<DonorProfile | null>(null);
  const [bloodBankProfile, setBloodBankProfile] = useState<BloodBankProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshProfiles = async () => {
    if (!token) return;
    try {
      const uResp = await api.get<User>('/auth/me');
      setUser(uResp.data);
      setRole(uResp.data.role);

      if (uResp.data.role === 'patient') {
        try {
          const pResp = await api.get<PatientProfile>('/patients/me');
          setPatientProfile(pResp.data);
        } catch {
          setPatientProfile(null);
        }
      } else if (uResp.data.role === 'donor') {
        try {
          const dResp = await api.get<DonorProfile>('/donors/me');
          setDonorProfile(dResp.data);
        } catch {
          setDonorProfile(null);
        }
      } else if (uResp.data.role === 'blood_bank') {
        try {
          const bResp = await api.get<BloodBankProfile>('/blood-bank/profile');
          setBloodBankProfile(bResp.data);
        } catch {
          setBloodBankProfile(null);
        }
      }
    } catch (err) {
      console.error('Session validation failed:', err);
      logout();
    }
  };

  useEffect(() => {
    const initializeAuth = async () => {
      if (token) {
        await refreshProfiles();
      }
      setLoading(false);
    };
    initializeAuth();
  }, [token]);

  const login = async (newToken: string, loggedInUser: User) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    setUser(loggedInUser);
    setRole(loggedInUser.role);
    setLoading(true);
    // Refresh to fetch any linked profiles
    await refreshProfiles();
    setLoading(false);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setRole(null);
    setPatientProfile(null);
    setDonorProfile(null);
    setBloodBankProfile(null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      role,
      token,
      patientProfile,
      donorProfile,
      bloodBankProfile,
      loading,
      login,
      logout,
      refreshProfiles
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

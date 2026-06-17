import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Activity,
  Plus,
  Trash2,
  ShieldAlert,
  CheckCircle,
  Clock,
  HeartHandshake,
  Brain,
  Sparkles,
  History,
  Send,
  Droplet,
  Gauge,
  User as UserIcon,
  CalendarDays,
  MapPin,
  HelpCircle,
  Upload,
  FileText,
} from 'lucide-react';
import api from '../services/api';
import { BloodRequest, TransfusionPrediction } from '../types';

export const PatientDashboard: React.FC = () => {
  const { patientProfile, refreshProfiles, user } = useAuth();
  const [requests, setRequests] = useState<BloodRequest[]>([]);
  const [bloodGroup, setBloodGroup] = useState('O+');
  const [units, setUnits] = useState(1);
  const [urgency, setUrgency] = useState('medium');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<BloodRequest | null>(null);

  // Active Tab
  const [activeTab, setActiveTab] = useState<'requests' | 'predictor' | 'iron'>('requests');

  // Transfusion Predictor Fields
  const [predPatientId, setPredPatientId] = useState<number | ''>('');
  const [predAge, setPredAge] = useState<number | ''>('');
  const [predGender, setPredGender] = useState<'Male' | 'Female'>('Male');
  const [predWeight, setPredWeight] = useState<number | ''>('');
  const [predThalassemiaType, setPredThalassemiaType] = useState<'Major' | 'Intermedia'>('Major');
  const [predCurrentHb, setPredCurrentHb] = useState<number | ''>('');
  const [predTargetHb, setPredTargetHb] = useState<number | ''>('');
  const [predFerritin, setPredFerritin] = useState<number | ''>('');
  const [predDaysSinceTransfusion, setPredDaysSinceTransfusion] = useState<number | ''>('');
  const [predPrevUnits, setPredPrevUnits] = useState<number | ''>('');
  const [predAvgUnits, setPredAvgUnits] = useState<number | ''>('');
  const [predTransfusions12M, setPredTransfusions12M] = useState<number | ''>('');
  const [predSpleenStatus, setPredSpleenStatus] = useState<'Normal' | 'Enlarged' | 'Removed'>('Normal');
  const [predSymptomSeverity, setPredSymptomSeverity] = useState<'Mild' | 'Moderate' | 'Severe'>('Mild');
  const [predBloodGroup, setPredBloodGroup] = useState<string>('O+');

  // Prediction History & Results
  const [predictionHistory, setPredictionHistory] = useState<TransfusionPrediction[]>([]);
  const [predictionResult, setPredictionResult] = useState<{
    predicted_units_required: number;
    recommended_next_transfusion_in_days: number;
  } | null>(null);

  const [predError, setPredError] = useState('');
  const [predSuccess, setPredSuccess] = useState('');
  const [predLoading, setPredLoading] = useState(false);

  // Iron Overload states
  const [mriText, setMriText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [ironResult, setIronResult] = useState<any | null>(null);
  const [ironLoading, setIronLoading] = useState(false);
  const [ironError, setIronError] = useState('');
  const [ironSuccess, setIronSuccess] = useState('');

  const handleAnalyzeText = async (e: React.FormEvent) => {
    e.preventDefault();
    setIronError('');
    setIronSuccess('');
    setIronResult(null);
    if (!mriText.trim()) return setIronError('Please enter MRI report text to analyze.');

    setIronLoading(true);
    try {
      const resp = await api.post(`/iron-overload/analyze/text?text=${encodeURIComponent(mriText)}`);
      setIronResult(resp.data);
      setIronSuccess('Analysis completed successfully!');
    } catch (err: any) {
      setIronError(err.response?.data?.detail || 'Iron overload analysis failed. Please try again.');
    } finally {
      setIronLoading(false);
    }
  };

  const handleAnalyzeFile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIronError('');
    setIronSuccess('');
    setIronResult(null);
    if (!selectedFile) return setIronError('Please select a PDF or Image file.');

    setIronLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      let endpoint = '/iron-overload/analyze/pdf';
      if (selectedFile.type.startsWith('image/')) {
        endpoint = '/iron-overload/analyze/image';
      }

      const resp = await api.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setIronResult(resp.data);
      setIronSuccess('File report analyzed successfully!');
    } catch (err: any) {
      setIronError(err.response?.data?.detail || 'File analysis failed. Please try again.');
    } finally {
      setIronLoading(false);
    }
  };

  // Profile creation fields if missing
  const [hospitalName, setHospitalName] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [latitude, setLatitude] = useState<number | undefined>(undefined);
  const [longitude, setLongitude] = useState<number | undefined>(undefined);

  const fetchRequests = async () => {
    try {
      const resp = await api.get<BloodRequest[]>('/requests/mine');
      setRequests(resp.data);
      // Sync selected request updates if currently viewing one
      setSelectedRequest(prev => {
        if (!prev) return null;
        const updated = resp.data.find(r => r.id === prev.id);
        return updated || null;
      });
    } catch (err) {
      console.error('Failed to load requests:', err);
    }
  };

  const fetchPredictionHistory = async () => {
    try {
      const resp = await api.get<TransfusionPrediction[]>('/transfusion/history');
      setPredictionHistory(resp.data);
    } catch (err) {
      console.error('Failed to load transfusion history:', err);
    }
  };

  useEffect(() => {
    if (patientProfile) {
      fetchRequests();
      const interval = setInterval(fetchRequests, 5000);
      return () => clearInterval(interval);
    }
  }, [patientProfile]);

  useEffect(() => {
    if (patientProfile) {
      setPredPatientId(patientProfile.id);
      setPredBloodGroup(patientProfile.blood_group_required || 'O+');
      setBloodGroup(patientProfile.blood_group_required || 'O+');
    }
  }, [patientProfile]);

  useEffect(() => {
    if (activeTab === 'predictor') {
      fetchPredictionHistory();
    }
  }, [activeTab]);

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/patients/me', {
        blood_group_required: 'O+', // default
        units_required: 1,
        urgency: 'medium',
        hospital_name: hospitalName,
        city,
        state,
        latitude: latitude || 19.0760,
        longitude: longitude || 72.8777
      });
      await refreshProfiles();
      setSuccess('Patient profile created successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create patient profile.');
    } finally {
      setLoading(false);
    }
  };

  const submitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await api.post('/requests/', {
        blood_group: bloodGroup,
        units_required: units,
        urgency: urgency
      });
      setSuccess('Blood request created successfully!');
      fetchRequests();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit request.');
    } finally {
      setLoading(false);
    }
  };

  const triggerSos = async () => {
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const bg = patientProfile?.blood_group_required || bloodGroup || 'O+';
      await api.post('/requests/', {
        blood_group: bg,
        units_required: 1,
        urgency: 'critical'
      });
      setSuccess('Emergency SOS Broadcast created! SMS & push alerts dispatched.');
      fetchRequests();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit SOS request.');
    } finally {
      setLoading(false);
    }
  };

  const cancelRequest = async (reqId: number) => {
    if (!window.confirm('Are you sure you want to cancel this request?')) return;
    try {
      await api.patch(`/requests/${reqId}/cancel`);
      setSuccess('Request cancelled.');
      fetchRequests();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to cancel request.');
    }
  };

  const submitPrediction = async (e: React.FormEvent) => {
    e.preventDefault();
    setPredError('');
    setPredSuccess('');
    setPredictionResult(null);

    // Front-end range validation
    const age = Number(predAge);
    const weight = Number(predWeight);
    const currentHb = Number(predCurrentHb);
    const targetHb = Number(predTargetHb);
    const ferritin = Number(predFerritin);
    const daysSince = Number(predDaysSinceTransfusion);
    const prevUnits = Number(predPrevUnits);
    const avgUnits = Number(predAvgUnits);
    const transfusions12M = Number(predTransfusions12M);

    if (age < 2 || age > 50) return setPredError('Age must be between 2 and 50.');
    if (weight < 10 || weight > 90) return setPredError('Weight must be between 10 and 90 kg.');
    if (currentHb < 4.5 || currentHb > 11.5) return setPredError('Current Hb Level must be between 4.5 and 11.5 g/dL.');
    if (targetHb < 9.0 || targetHb > 11.0) return setPredError('Target Hb Level must be between 9.0 and 11.0 g/dL.');
    if (ferritin < 100 || ferritin > 5000) return setPredError('Ferritin Level must be between 100 and 5000 ng/mL.');
    if (daysSince < 5 || daysSince > 60) return setPredError('Days since last transfusion must be between 5 and 60 days.');
    if (prevUnits < 1 || prevUnits > 4) return setPredError('Previous units received must be between 1 and 4.');
    if (avgUnits < 1 || avgUnits > 4) return setPredError('Average units per transfusion must be between 1 and 4.');
    if (transfusions12M < 4 || transfusions12M > 24) return setPredError('Transfusions in last 12 months must be between 4 and 24.');

    setPredLoading(true);
    try {
      const payload = {
        age,
        gender: predGender,
        weight_kg: weight,
        thalassemia_type: predThalassemiaType,
        current_hb_level: currentHb,
        target_hb_level: targetHb,
        ferritin_level: ferritin,
        days_since_last_transfusion: daysSince,
        previous_units_received: prevUnits,
        average_units_per_transfusion: avgUnits,
        transfusions_last_12_months: transfusions12M,
        spleen_status: predSpleenStatus,
        symptom_severity: predSymptomSeverity,
        blood_group: predBloodGroup,
      };

      const resp = await api.post('/transfusion/predict', payload);
      setPredictionResult({
        predicted_units_required: resp.data.predicted_units_required,
        recommended_next_transfusion_in_days: resp.data.recommended_next_transfusion_in_days,
      });
      setPredSuccess('Prediction calculated and saved!');
      fetchPredictionHistory();
    } catch (err: any) {
      setPredError(err.response?.data?.detail || 'Model inference failed. Please try again.');
    } finally {
      setPredLoading(false);
    }
  };

  const getUrgencyBadge = (u: string) => {
    switch (u.toLowerCase()) {
      case 'low': 
        return 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/10';
      case 'medium': 
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/10';
      case 'high': 
        return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/10';
      case 'critical': 
        return 'bg-brand-accent text-white border border-transparent animate-pulse';
      default: 
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending': return <Clock className="w-4 h-4 text-slate-400" />;
      case 'matched': return <HeartHandshake className="w-4 h-4 text-amber-500" />;
      case 'accepted': return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'fulfilled': return <CheckCircle className="w-4 h-4 text-[#FF5E5E]" />;
      case 'escalated': return <ShieldAlert className="w-4 h-4 text-[#FF5E5E] animate-bounce" />;
      default: return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  if (!patientProfile) {
    return (
      <div className="max-w-lg mx-auto glass-panel p-8 mt-10 border border-brand-default/30 dark:border-brand-dark/40">
        <h2 className="text-xl font-black mb-1.5 flex items-center gap-2 text-brand-dark dark:text-slate-100">
          <Activity className="text-brand-dark dark:text-brand-default w-5.5 h-5.5" />
          Setup Patient Profile
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mb-6">
          Provide your hospital name and location coordinates to start requesting blood.
        </p>
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] text-xs p-3 rounded-xl font-bold mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleCreateProfile} className="flex flex-col gap-4">
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5 font-bold">Hospital Name</label>
            <input
              type="text"
              placeholder="e.g. Mumbai Central Hospital"
              className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
              value={hospitalName}
              onChange={(e) => setHospitalName(e.target.value)}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5 font-bold">City</label>
              <input
                type="text"
                placeholder="Mumbai"
                className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5 font-bold">State</label>
              <input
                type="text"
                placeholder="Maharashtra"
                className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
                value={state}
                onChange={(e) => setState(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5 font-bold">Latitude</label>
              <input
                type="number"
                step="any"
                placeholder="19.0760"
                className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
                value={latitude || ''}
                onChange={(e) => setLatitude(parseFloat(e.target.value))}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5 font-bold">Longitude</label>
              <input
                type="number"
                step="any"
                placeholder="72.8777"
                className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
                value={longitude || ''}
                onChange={(e) => setLongitude(parseFloat(e.target.value))}
                required
              />
            </div>
          </div>
          <button 
            type="submit" 
            className="w-full btn-pill-primary mt-4" 
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Profile'}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] mx-auto flex flex-col gap-6">
      
      {/* Mobile-App Styled Welcome Header Panel */}
      <div className="mx-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-transparent border-none py-2 max-w-[1600px] xl:mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-brand-light text-brand-dark border border-brand-default flex items-center justify-center font-black text-lg uppercase dark:bg-brand-dark dark:text-brand-light dark:border-brand-dark/80">
            {user?.full_name[0]}
          </div>
          <div>
            <span className="block text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Welcome back,</span>
            <h2 className="text-xl font-black text-brand-dark dark:text-white leading-tight mt-0.5">{user?.full_name}</h2>
          </div>
        </div>

        {/* Floating Switch Tabs */}
        <div className="bg-white/90 dark:bg-brand-darkCard p-1 rounded-full border border-brand-default/40 dark:border-brand-dark/40 shadow-sm flex gap-1.5">
          <button
            onClick={() => setActiveTab('requests')}
            className={`flex items-center gap-1.5 px-4.5 py-1.5 text-xs font-bold rounded-full transition-all duration-300 ${
              activeTab === 'requests' 
                ? 'bg-brand-dark text-white dark:bg-brand-default dark:text-brand-dark shadow-sm' 
                : 'text-slate-550 dark:text-slate-400 hover:bg-slate-100/50 dark:hover:bg-slate-900/30'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Requests & Status
          </button>
          <button
            onClick={() => setActiveTab('predictor')}
            className={`flex items-center gap-1.5 px-4.5 py-1.5 text-xs font-bold rounded-full transition-all duration-300 ${
              activeTab === 'predictor' 
                ? 'bg-brand-dark text-white dark:bg-brand-default dark:text-brand-dark shadow-sm' 
                : 'text-slate-550 dark:text-slate-400 hover:bg-slate-100/50 dark:hover:bg-slate-900/30'
            }`}
          >
            <Brain className="w-3.5 h-3.5" />
            AI Scheduler
          </button>
          <button
            onClick={() => setActiveTab('iron')}
            className={`flex items-center gap-1.5 px-4.5 py-1.5 text-xs font-bold rounded-full transition-all duration-300 ${
              activeTab === 'iron' 
                ? 'bg-brand-dark text-white dark:bg-brand-default dark:text-brand-dark shadow-sm' 
                : 'text-slate-550 dark:text-slate-400 hover:bg-slate-100/50 dark:hover:bg-slate-900/30'
            }`}
          >
            <Gauge className="w-3.5 h-3.5" />
            Iron Overload
          </button>
        </div>
      </div>

      {activeTab === 'requests' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* LEFT COLUMN: Qatra-style mobile widgets layout */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            
            {/* Current Location Widget */}
            <div className="glass-panel p-5 flex flex-col gap-3.5">
              <div className="flex justify-between items-center text-xs font-bold">
                <span className="text-slate-405 dark:text-slate-500 flex items-center gap-1">
                  <MapPin className="w-4 h-4 text-brand-dark dark:text-brand-default" />
                  Current location
                </span>
                <span className="text-[#2C5E7A] dark:text-[#C7E5F4] hover:underline cursor-pointer flex items-center gap-0.5">
                  Change &gt;
                </span>
              </div>
              <div className="font-extrabold text-sm text-brand-dark dark:text-slate-200 leading-snug">
                {patientProfile.hospital_name || 'Hospital Not Set'}, {patientProfile.city || 'City'}, {patientProfile.state}
              </div>
            </div>

            {/* Press for Help (SOS) pulse card */}
            <div className="glass-panel p-6 flex flex-col items-center justify-center text-center gap-4.5">
              <div>
                <h3 className="font-extrabold text-base text-brand-dark dark:text-white">Press For Help</h3>
                <p className="text-[10px] text-slate-450 dark:text-slate-500 font-bold mt-1 max-w-[220px] mx-auto leading-normal">
                  Press the button below to request immediate help and broadcast an emergency alert to matching donors.
                </p>
              </div>

              {/* SOS Circular Pulse Ring Trigger */}
              <div className="sos-button-container my-2">
                <div className="sos-pulse-ring"></div>
                <div className="sos-pulse-ring-2"></div>
                <button
                  type="button"
                  onClick={triggerSos}
                  disabled={loading}
                  className="sos-button outline-none"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-white/20 border-t-white"></div>
                  ) : (
                    <span>SOS</span>
                  )}
                </button>
              </div>

              <div className="text-[9px] text-[#2C5E7A] dark:text-brand-default uppercase font-bold tracking-widest bg-brand-light/30 dark:bg-brand-dark/20 px-3 py-1 rounded-full border border-brand-default/20">
                Blood Group Required: {patientProfile.blood_group_required}
              </div>
            </div>

            {/* Standard manual request form Card */}
            <div className="glass-panel p-6">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <Plus className="text-brand-dark dark:text-brand-default w-4.5 h-4.5" />
                Manual Request Form
              </h3>

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] text-xs p-2.5 rounded-xl font-bold mt-3">
                  {error}
                </div>
              )}
              {success && (
                <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs p-2.5 rounded-xl font-bold mt-3">
                  {success}
                </div>
              )}

              <form onSubmit={submitRequest} className="flex flex-col gap-3.5 mt-4">
                <div>
                  <label className="block text-[9px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1">Blood Group</label>
                  <div className="w-full bg-[#DDEFF7]/20 dark:bg-[#131E29]/40 border border-brand-default/30 dark:border-brand-dark/40 rounded-xl px-3.5 py-2.5 text-xs font-extrabold text-brand-dark dark:text-slate-100 flex items-center justify-between">
                    <span>{patientProfile.blood_group_required || bloodGroup}</span>
                    <span className="text-[10px] text-brand-dark dark:text-brand-default font-extrabold">
                      Auto-filled
                    </span>
                  </div>
                </div>

                <div>
                  <label className="block text-[9px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1">Units Required</label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-xs font-bold text-brand-dark dark:text-slate-100"
                    value={units}
                    onChange={(e) => setUnits(parseInt(e.target.value))}
                    required
                  />
                </div>

                <div>
                  <label className="block text-[9px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1">Urgency Level</label>
                  <select
                    className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2.5 text-xs font-bold text-brand-dark dark:text-slate-100"
                    value={urgency}
                    onChange={(e) => setUrgency(e.target.value)}
                  >
                    <option value="low">Low (Routine)</option>
                    <option value="medium">Medium (Standard)</option>
                    <option value="high">High (Urgent)</option>
                    <option value="critical">Critical (Immediate Broadcast)</option>
                  </select>
                </div>

                <button 
                  type="submit" 
                  className="w-full btn-pill-primary mt-2" 
                  disabled={loading}
                >
                  Submit Request
                </button>
              </form>
            </div>

          </div>

          {/* RIGHT COLUMN: Active Requests Status List & Matching candidate details */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            
            {/* Requests tracking list Card */}
            <div className="glass-panel p-6 h-fit">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <Activity className="text-brand-dark dark:text-brand-default w-4.5 h-4.5" />
                Active Requests Status
              </h3>

              <div className="overflow-x-auto mt-4">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-200/40 dark:border-slate-800/40">
                      <th className="pb-3.5 font-bold">Req ID</th>
                      <th className="pb-3.5 font-bold">Blood Group</th>
                      <th className="pb-3.5 font-bold">Units</th>
                      <th className="pb-3.5 font-bold">Urgency</th>
                      <th className="pb-3.5 font-bold">Status</th>
                      <th className="pb-3.5 font-bold">Assignment / Location</th>
                      <th className="pb-3.5 font-bold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100/50 dark:divide-slate-900/30 text-xs">
                    {requests.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="text-center py-10 text-slate-400 font-semibold">
                          You haven't submitted any requests yet. Use SOS or the manual form to create one.
                        </td>
                      </tr>
                    ) : (
                      requests.map((req) => (
                        <tr 
                          key={req.id} 
                          onClick={() => setSelectedRequest(req)}
                          className={`cursor-pointer transition-colors duration-150 border-b border-[#C7E5F4]/10 dark:border-slate-800/10 ${
                            selectedRequest?.id === req.id 
                              ? 'bg-brand-light/30 dark:bg-brand-dark/20' 
                              : 'hover:bg-slate-100/30 dark:hover:bg-slate-900/10'
                          }`}
                        >
                          <td className="py-4 font-extrabold text-slate-400">#{req.id}</td>
                          <td className="py-4">
                            <span className="inline-block bg-brand-dark text-white dark:bg-brand-default dark:text-brand-dark font-extrabold text-xs px-2.5 py-0.5 rounded-lg border border-transparent">
                              {req.blood_group}
                            </span>
                          </td>
                          <td className="py-4 font-black text-brand-dark dark:text-slate-350">{req.units_required}</td>
                          <td className="py-4">
                            <span className={`inline-block px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase ${getUrgencyBadge(req.urgency)}`}>
                              {req.urgency}
                            </span>
                          </td>
                          <td className="py-4">
                            <div className="flex items-center gap-1.5 font-bold uppercase text-[9px]">
                              {getStatusIcon(req.status)}
                              <span className="text-brand-dark dark:text-slate-300 font-black">{req.status}</span>
                            </div>
                          </td>
                          <td className="py-4 font-semibold text-[#2C5E7A] dark:text-slate-400 max-w-[150px] truncate">
                            {req.status === 'accepted' ? (
                              req.assigned_donor_id ? (
                                <span className="text-emerald-600 dark:text-emerald-450 flex items-center gap-1 font-bold">
                                  💚 Donor Assigned
                                </span>
                              ) : req.assigned_blood_bank_id ? (
                                <span className="text-brand-dark dark:text-brand-default flex items-center gap-1 font-bold">
                                  🏥 Blood Bank Claimed
                                </span>
                              ) : (
                                'Processing'
                              )
                            ) : req.status === 'matched' ? (
                              <span className="text-amber-600 font-bold">Matched, waiting donor...</span>
                            ) : (
                              'Search in progress'
                            )}
                          </td>
                          <td className="py-4 text-right">
                            {['pending', 'matched'].includes(req.status.toLowerCase()) && (
                              <button
                                onClick={() => cancelRequest(req.id)}
                                className="p-1.5 hover:bg-[#FF5E5E]/10 rounded-lg text-[#FF5E5E] transition-all inline-flex items-center"
                                title="Cancel Request"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* AI Match Board Section */}
            <div className="glass-panel p-6">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <Sparkles className="text-brand-dark dark:text-brand-default w-4.5 h-4.5 animate-pulse" />
                AI Match Board (Top 10 Anonymized Donors)
              </h3>
              
              {!selectedRequest ? (
                <div className="text-center py-12 text-slate-400 dark:text-slate-500 font-bold flex flex-col items-center gap-2">
                  <Activity className="w-8 h-8 text-brand-default dark:text-brand-dark/50 animate-pulse" />
                  <span>Select a request from the status list above to view real-time matched AI candidates.</span>
                </div>
              ) : (
                <div className="mt-4 flex flex-col gap-4">
                  <div className="flex flex-wrap justify-between items-center gap-4 bg-brand-light/20 dark:bg-brand-dark/10 p-3 rounded-2xl border border-brand-default/20">
                    <div className="flex items-center gap-2 text-xs font-black">
                      <span className="text-slate-405 dark:text-slate-500">Request:</span>
                      <span className="text-brand-dark dark:text-brand-default font-extrabold">#{selectedRequest.id}</span>
                      <span className="text-[#C7E5F4]/60">|</span>
                      <span className="text-slate-405 dark:text-slate-500">Required:</span>
                      <span className="inline-block bg-brand-dark text-white font-extrabold text-[10px] px-2 py-0.5 rounded-lg border border-transparent">
                        {selectedRequest.blood_group}
                      </span>
                      <span className="text-[#C7E5F4]/60">|</span>
                      <span className="text-slate-450">Urgency:</span>
                      <span className={`inline-block px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase ${getUrgencyBadge(selectedRequest.urgency)}`}>
                        {selectedRequest.urgency}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 font-semibold italic">
                      Compatibility-ranked candidates
                    </div>
                  </div>

                  {(!selectedRequest.top_donors || selectedRequest.top_donors.length === 0) ? (
                    <div className="text-center py-10 text-slate-400 font-bold">
                      No active compatible donors found within matching distance.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {selectedRequest.top_donors.slice(0, 10).map((donor, idx) => (
                        <div key={idx} className="glass-card border border-brand-default/30 dark:border-brand-dark/50 bg-[#F4F8FA]/20 dark:bg-brand-dark/10 p-4.5 flex flex-col gap-3">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                              <span className="flex items-center justify-center w-6 h-6 bg-brand-dark text-white text-[10px] font-black rounded-full shadow-sm dark:bg-brand-default dark:text-brand-dark">
                                #{idx + 1}
                              </span>
                              <span className="text-xs font-black text-brand-dark dark:text-slate-200">
                                Match Candidate
                              </span>
                            </div>
                            <span className="text-[10px] font-black bg-brand-light text-brand-dark dark:bg-brand-dark dark:text-brand-light px-2.5 py-0.5 rounded-lg border border-brand-default/20">
                              {donor.blood_group} Compatible
                            </span>
                          </div>

                          <div className="flex flex-col gap-1 mt-1">
                            <div className="flex justify-between text-[10px] font-bold text-slate-405 dark:text-slate-500">
                              <span>AI Compatibility Score</span>
                              <span className="text-[#2C5E7A] dark:text-brand-default">{(donor.match_probability * 100).toFixed(1)}%</span>
                            </div>
                            {/* Progress bar */}
                            <div className="w-full bg-[#C7E5F4]/30 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                              <div 
                                className="bg-gradient-to-r from-brand-dark to-brand-default h-full rounded-full dark:from-brand-default dark:to-brand-light" 
                                style={{ width: `${donor.match_probability * 100}%` }}
                              />
                            </div>
                          </div>

                          <div className="grid grid-cols-3 gap-2 text-center mt-1 border-t border-[#C7E5F4]/20 dark:border-brand-dark/30 pt-2.5">
                            <div>
                              <span className="block text-[11px] font-black text-[#10354A] dark:text-brand-light">
                                {donor.distance_km < 1 ? '<1' : donor.distance_km.toFixed(1)} km
                              </span>
                              <span className="text-[8px] uppercase font-bold text-slate-400 tracking-wider">Distance</span>
                            </div>
                            <div>
                              <span className="block text-[11px] font-black text-[#10354A] dark:text-brand-light">
                                {(donor.reliability_score * 100).toFixed(0)}%
                              </span>
                              <span className="text-[8px] uppercase font-bold text-slate-400 tracking-wider">Reliability</span>
                            </div>
                            <div>
                              <span className="block text-[11px] font-black text-[#10354A] dark:text-brand-light">
                                {donor.total_donations || 0}
                              </span>
                              <span className="text-[8px] uppercase font-bold text-slate-400 tracking-wider">Donations</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="text-[10px] text-slate-400 dark:text-slate-500 font-bold italic mt-2 border-t border-[#C7E5F4]/20 dark:border-brand-dark/30 pt-3 flex items-center gap-1">
                    🔒 Donor identity and direct contact information are kept strictly confidential until a matched candidate accepts the request.
                  </div>
                </div>
              )}
            </div>

          </div>

        </div>
      ) : activeTab === 'predictor' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Form Column */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            <div className="glass-panel p-6">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <Sparkles className="text-brand-dark dark:text-brand-default w-4.5 h-4.5 animate-pulse" />
                AI Transfusion Scheduler
              </h3>

              {predError && (
                <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] text-xs p-3 rounded-xl font-bold mt-3">
                  {predError}
                </div>
              )}
              {predSuccess && (
                <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs p-3 rounded-xl font-bold mt-3">
                  {predSuccess}
                </div>
              )}

              <form onSubmit={submitPrediction} className="flex flex-col gap-4 mt-4">
                
                {/* Grid 1: Basic Profile */}
                <div className="bg-brand-light/20 dark:bg-brand-dark/10 p-4.5 rounded-2xl border border-brand-default/20 dark:border-brand-dark/30">
                  <span className="text-[10px] font-black uppercase tracking-widest text-[#2C5E7A] dark:text-brand-default flex items-center gap-1.5 mb-3.5">
                    <UserIcon className="w-3.5 h-3.5" />
                    Demographics & Blood Profile
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Patient ID</label>
                      <input
                        type="number"
                        placeholder="e.g. 1"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predPatientId}
                        onChange={(e) => setPredPatientId(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Age (2 - 50)</label>
                      <input
                        type="number"
                        placeholder="e.g. 18"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predAge}
                        onChange={(e) => setPredAge(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Gender</label>
                      <select
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-xs font-semibold text-brand-dark dark:text-slate-100"
                        value={predGender}
                        onChange={(e: any) => setPredGender(e.target.value)}
                      >
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Weight (10 - 90 kg)</label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 55"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predWeight}
                        onChange={(e) => setPredWeight(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Blood Group</label>
                      <select
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-xs font-semibold text-brand-dark dark:text-slate-100"
                        value={predBloodGroup}
                        onChange={(e) => setPredBloodGroup(e.target.value)}
                      >
                        {['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-'].map(bg => (
                          <option key={bg} value={bg}>{bg}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Grid 2: Clinical Details */}
                <div className="bg-brand-light/20 dark:bg-brand-dark/10 p-4.5 rounded-2xl border border-brand-default/20 dark:border-brand-dark/30">
                  <span className="text-[10px] font-black uppercase tracking-widest text-[#2C5E7A] dark:text-brand-default flex items-center gap-1.5 mb-3.5">
                    <Gauge className="w-3.5 h-3.5" />
                    Clinical & Hemoglobin Levels
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Thalassemia Type</label>
                      <select
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-xs font-semibold text-brand-dark dark:text-slate-100"
                        value={predThalassemiaType}
                        onChange={(e: any) => setPredThalassemiaType(e.target.value)}
                      >
                        <option value="Major">Thalassemia Major</option>
                        <option value="Intermedia">Thalassemia Intermedia</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Current Hb (4.5 - 11.5 g/dL)</label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 7.2"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predCurrentHb}
                        onChange={(e) => setPredCurrentHb(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Target Hb (9.0 - 11.0 g/dL)</label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 10.0"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predTargetHb}
                        onChange={(e) => setPredTargetHb(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Ferritin (100 - 5000 ng/mL)</label>
                      <input
                        type="number"
                        placeholder="e.g. 800"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predFerritin}
                        onChange={(e) => setPredFerritin(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Grid 3: Transfusion History */}
                <div className="bg-brand-light/20 dark:bg-brand-dark/10 p-4.5 rounded-2xl border border-brand-default/20 dark:border-brand-dark/30">
                  <span className="text-[10px] font-black uppercase tracking-widest text-[#2C5E7A] dark:text-brand-default flex items-center gap-1.5 mb-3.5">
                    <CalendarDays className="w-3.5 h-3.5" />
                    Transfusion History
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Days Since Last (5 - 60)</label>
                      <input
                        type="number"
                        placeholder="e.g. 21"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predDaysSinceTransfusion}
                        onChange={(e) => setPredDaysSinceTransfusion(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Previous Units (1 - 4)</label>
                      <input
                        type="number"
                        placeholder="e.g. 2"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predPrevUnits}
                        onChange={(e) => setPredPrevUnits(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Average Units (1.0 - 4.0)</label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 2.0"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predAvgUnits}
                        onChange={(e) => setPredAvgUnits(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Transfusions Last 12M (4 - 24)</label>
                      <input
                        type="number"
                        placeholder="e.g. 12"
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-1.5 text-xs text-brand-dark dark:text-slate-100 font-bold"
                        value={predTransfusions12M}
                        onChange={(e) => setPredTransfusions12M(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Grid 4: Symptom & Spleen Details */}
                <div className="bg-brand-light/20 dark:bg-brand-dark/10 p-4.5 rounded-2xl border border-brand-default/20 dark:border-brand-dark/30">
                  <span className="text-[10px] font-black uppercase tracking-widest text-[#2C5E7A] dark:text-brand-default flex items-center gap-1.5 mb-3.5">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Symptoms & Spleen Condition
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Spleen Status</label>
                      <select
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-xs font-semibold text-brand-dark dark:text-slate-100"
                        value={predSpleenStatus}
                        onChange={(e: any) => setPredSpleenStatus(e.target.value)}
                      >
                        <option value="Normal">Normal</option>
                        <option value="Enlarged">Enlarged</option>
                        <option value="Removed">Removed (Splenectomy)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Symptom Severity</label>
                      <select
                        className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-xs font-semibold text-brand-dark dark:text-slate-100"
                        value={predSymptomSeverity}
                        onChange={(e: any) => setPredSymptomSeverity(e.target.value)}
                      >
                        <option value="Mild">Mild</option>
                        <option value="Moderate">Moderate</option>
                        <option value="Severe">Severe</option>
                      </select>
                    </div>
                  </div>
                </div>

                <button 
                  type="submit" 
                  className="btn-pill-primary w-fit text-xs uppercase tracking-wider flex items-center justify-center gap-1.5" 
                  disabled={predLoading}
                >
                  {predLoading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                  <Send className="w-3.5 h-3.5" />
                  Predict Requirement
                </button>

              </form>
            </div>

            {/* Prediction History Table */}
            <div className="glass-panel p-6">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <History className="text-slate-400 w-4.5 h-4.5" />
                Transfusion Prediction History
              </h3>
              <div className="overflow-x-auto mt-4">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-200/40 dark:border-slate-800/40">
                      <th className="pb-3 font-bold">Date</th>
                      <th className="pb-3 font-bold">Hb Profile</th>
                      <th className="pb-3 font-bold">Severity</th>
                      <th className="pb-3 font-bold">Predicted Units</th>
                      <th className="pb-3 font-bold">Recommendation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100/50 dark:divide-slate-900/30 text-xs">
                    {predictionHistory.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="text-center py-8 text-slate-400 font-semibold">
                          No prediction history found.
                        </td>
                      </tr>
                    ) : (
                      predictionHistory.map((historyItem) => (
                        <tr key={historyItem.id} className="hover:bg-slate-100/10 dark:hover:bg-slate-900/10 transition-colors">
                          <td className="py-3.5 text-slate-500 dark:text-slate-400 font-semibold">{new Date(historyItem.created_at).toLocaleDateString()}</td>
                          <td className="py-3.5 font-extrabold text-brand-dark dark:text-slate-350">
                            {historyItem.current_hb_level} ➔ {historyItem.target_hb_level} g/dL
                          </td>
                          <td className="py-3.5">
                            <span className="inline-block bg-[#DDEFF7]/40 dark:bg-brand-dark/25 text-[10px] font-bold px-2 py-0.5 rounded-md border border-brand-default/20 text-brand-dark dark:text-slate-300">
                              {historyItem.symptom_severity}
                            </span>
                          </td>
                          <td className="py-3.5 font-black text-brand-dark dark:text-brand-default">
                            {historyItem.predicted_units_required} Unit(s)
                          </td>
                          <td className="py-3.5 font-bold text-brand-dark dark:text-brand-default">
                            In {historyItem.recommended_next_transfusion_in_days} Days
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          {/* Predictor Result Column */}
          <div className="lg:col-span-4 h-fit flex flex-col gap-6">
            <div className="glass-panel p-6 sticky top-6">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <Brain className="text-brand-dark dark:text-brand-default w-4.5 h-4.5 animate-pulse" />
                Model Output Result
              </h3>

              {predictionResult ? (
                <div className="flex flex-col items-center gap-5 mt-5">
                  
                  {/* Units Block */}
                  <div className="flex flex-col items-center p-5 bg-brand-light/20 border border-brand-default/40 w-full rounded-2xl relative overflow-hidden dark:bg-brand-dark/20 dark:border-brand-dark/30">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-brand-default/10 rounded-full filter blur-xl"></div>
                    <Droplet className="w-10 h-10 text-brand-dark fill-brand-dark/30 animate-bounce mb-2 dark:text-brand-default dark:fill-brand-default/20" />
                    <span className="text-2xl font-black text-brand-dark dark:text-brand-default">
                      {predictionResult.predicted_units_required} Unit(s)
                    </span>
                    <span className="text-[9px] uppercase font-bold text-slate-400 mt-1">
                      PRBC Volume Needed
                    </span>
                  </div>

                  {/* Timeline Block */}
                  <div className="flex flex-col items-center p-5 bg-brand-light/20 border border-brand-default/40 w-full rounded-2xl relative overflow-hidden dark:bg-brand-dark/20 dark:border-brand-dark/30">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-brand-default/10 rounded-full filter blur-xl"></div>
                    <Clock className="w-10 h-10 text-brand-dark animate-pulse mb-2 dark:text-brand-default" />
                    <span className="text-2xl font-black text-brand-dark dark:text-brand-default">
                      {predictionResult.recommended_next_transfusion_in_days} Days
                    </span>
                    <span className="text-[9px] uppercase font-bold text-slate-400 mt-1">
                      Recommended Next Schedule
                    </span>
                  </div>

                  {/* Description Alert */}
                  <div className="bg-brand-light/20 border border-brand-default/40 text-xs leading-normal p-4 font-semibold text-brand-dark dark:bg-brand-dark/15 dark:border-brand-dark/30 dark:text-slate-350 rounded-2xl">
                    <span>
                      Based on target Hb level and clinical conditions, our AI recommends administering{' '}
                      <strong className="text-brand-dark dark:text-brand-default font-extrabold">{predictionResult.predicted_units_required} Unit(s)</strong> of compatible{' '}
                      <strong className="text-brand-dark dark:text-brand-default font-extrabold">{predBloodGroup}</strong> blood, with the next transfusion scheduled in{' '}
                      <strong className="text-brand-dark dark:text-brand-default font-extrabold">{predictionResult.recommended_next_transfusion_in_days} Days</strong>.
                    </span>
                  </div>

                </div>
              ) : (
                <div className="flex flex-col items-center text-center py-16 px-4">
                  <Brain className="w-14 h-14 text-brand-default/50 dark:text-brand-dark/50 mb-3.5 animate-pulse" />
                  <h4 className="text-xs font-bold text-slate-500 dark:text-slate-400">Ready for Prediction</h4>
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 max-w-[200px] leading-normal font-semibold">
                    Please enter the clinical parameters on the left and click predict.
                  </p>
                </div>
              )}

            </div>
          </div>

        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Input Panel */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            
            {/* MRI Text Report Form */}
            <div className="glass-panel p-6">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <FileText className="text-brand-dark dark:text-brand-default w-4.5 h-4.5" />
                MRI Report Text Analysis
              </h3>
              <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold mt-2 leading-relaxed">
                Paste the text contents of your MRI Iron Assessment or cardiac/liver T2* report to automatically extract biomarkers and analyze risk progression.
              </p>

              <form onSubmit={handleAnalyzeText} className="flex flex-col gap-4 mt-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">
                    MRI Report Text
                  </label>
                  <textarea
                    placeholder="Example:
MRI Iron Assessment:
Heart T2*: 14.5 ms
Liver T2*: 5.2 ms
Liver Iron Concentration: 8.3 mg/g
Ferritin: 2500"
                    rows={6}
                    className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3.5 py-2.5 text-xs text-brand-dark dark:text-slate-100 font-semibold leading-normal"
                    value={mriText}
                    onChange={(e) => setMriText(e.target.value)}
                  />
                </div>

                <button
                  type="submit"
                  className="btn-pill-primary w-fit text-xs uppercase tracking-wider px-5 py-2.5 font-bold"
                  disabled={ironLoading}
                >
                  {ironLoading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                  Analyze Report Text
                </button>
              </form>
            </div>

            {/* MRI File Upload Form */}
            <div className="glass-panel p-6">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <Upload className="text-brand-dark dark:text-brand-default w-4.5 h-4.5" />
                Upload MRI Report File
              </h3>
              <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold mt-2 leading-relaxed">
                Select and upload an MRI report file (PDF format or scanned report image) for automated extraction and risk prediction.
              </p>

              <form onSubmit={handleAnalyzeFile} className="flex flex-col gap-4 mt-4">
                <div className="border-2 border-dashed border-brand-default/60 dark:border-brand-dark/40 rounded-2xl p-6 flex flex-col items-center justify-center bg-brand-light/10 dark:bg-brand-dark/5 text-center transition-all hover:bg-brand-light/20 dark:hover:bg-brand-dark/10 relative">
                  <Upload className="w-8 h-8 text-brand-default dark:text-brand-dark mb-2.5" />
                  <span className="text-xs font-bold text-brand-dark dark:text-slate-200">
                    {selectedFile ? selectedFile.name : 'Select MRI PDF or Image'}
                  </span>
                  <span className="text-[9px] text-slate-400 font-semibold mt-1">
                    PDF, PNG, JPG files up to 10MB
                  </span>
                  <input
                    type="file"
                    accept=".pdf,image/*"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                  />
                </div>

                <button
                  type="submit"
                  className="btn-pill-primary w-fit text-xs uppercase tracking-wider px-5 py-2.5 font-bold"
                  disabled={ironLoading}
                >
                  {ironLoading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                  Upload and Analyze File
                </button>
              </form>
            </div>

          </div>

          {/* Right Column: Output Results */}
          <div className="lg:col-span-4 h-fit flex flex-col gap-6">
            <div className="glass-panel p-6 sticky top-6">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/15 dark:border-brand-dark/20 pb-3 flex items-center gap-2">
                <Brain className="text-brand-dark dark:text-brand-default w-4.5 h-4.5 animate-pulse" />
                Iron Overload Analysis
              </h3>

              {ironError && (
                <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] text-xs p-3 rounded-xl font-bold mt-4 leading-normal">
                  {ironError}
                </div>
              )}
              {ironSuccess && (
                <div className="bg-emerald-550/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs p-3 rounded-xl font-bold mt-4 leading-normal">
                  {ironSuccess}
                </div>
              )}

              {ironLoading ? (
                <div className="flex flex-col items-center justify-center py-16 px-4 text-center gap-3">
                  <div className="w-10 h-10 border-4 border-brand-default border-t-brand-dark rounded-full animate-spin dark:border-brand-dark/40 dark:border-t-brand-light"></div>
                  <h4 className="text-xs font-bold text-slate-500 dark:text-slate-400">Processing MRI Report...</h4>
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 leading-normal max-w-[180px] font-semibold">
                    Extracting T2* values, calculating risk scores, and generating recommendations.
                  </p>
                </div>
              ) : ironResult ? (
                <div className="flex flex-col gap-5 mt-5">
                  
                  {/* Current Risk Badge */}
                  <div className="flex flex-col items-center p-4 bg-brand-light/20 border border-brand-default/40 w-full rounded-2xl text-center dark:bg-brand-dark/20 dark:border-brand-dark/30">
                    <span className="text-[9px] uppercase font-bold text-slate-400 mb-1">
                      Current Overload Risk
                    </span>
                    <span className={`inline-block text-xs font-black px-3.5 py-1 rounded-full uppercase tracking-wider mt-1 border ${
                      ironResult.current_risk.toLowerCase() === 'high' || ironResult.current_risk.toLowerCase() === 'critical'
                        ? 'bg-brand-accent/10 border-brand-accent text-[#FF5E5E]'
                        : 'bg-emerald-550/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                    }`}>
                      {ironResult.current_risk}
                    </span>
                  </div>

                  {/* Risk Score */}
                  <div className="flex flex-col p-4.5 bg-brand-light/20 border border-brand-default/40 w-full rounded-2xl dark:bg-brand-dark/20 dark:border-brand-dark/30 gap-2">
                    <div className="flex justify-between items-center text-[10px] uppercase font-bold text-slate-400">
                      <span>Iron Overload Score</span>
                      <span className="text-brand-dark dark:text-brand-default font-extrabold text-xs">
                        {Math.round(ironResult.risk_score * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-200/50 dark:bg-slate-900/40 rounded-full h-2 overflow-hidden border border-slate-300/10">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          ironResult.risk_score > 0.6 ? 'bg-[#FF5E5E]' : 'bg-brand-default'
                        }`}
                        style={{ width: `${ironResult.risk_score * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* Days until high risk */}
                  {ironResult.days_until_high_risk > 0 && (
                    <div className="flex flex-col items-center p-4 bg-brand-light/20 border border-brand-default/40 w-full rounded-2xl text-center dark:bg-brand-dark/20 dark:border-brand-dark/30">
                      <CalendarDays className="w-8 h-8 text-brand-dark mb-1.5 dark:text-brand-default" />
                      <span className="text-xl font-black text-brand-dark dark:text-brand-default">
                        {ironResult.days_until_high_risk} Days
                      </span>
                      <span className="text-[9px] uppercase font-bold text-slate-400 mt-1">
                        Est. Until High Risk Phase
                      </span>
                    </div>
                  )}

                  {/* Explanation text */}
                  <div className="bg-brand-light/20 border border-brand-default/40 text-[11px] leading-relaxed p-4 font-semibold text-brand-dark dark:bg-brand-dark/15 dark:border-brand-dark/30 dark:text-slate-350 rounded-2xl">
                    <div className="font-bold text-[10px] uppercase text-slate-400 tracking-wider mb-1">Clinical Assessment</div>
                    <span>{ironResult.explanation}</span>
                  </div>

                  {/* Extracted Biomarkers */}
                  <div className="flex flex-col gap-2">
                    <div className="font-bold text-[10px] uppercase text-slate-400 tracking-wider mb-1 px-1">Extracted Biomarkers</div>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(ironResult.extracted_values).map(([key, val]) => (
                        <div key={key} className="bg-white dark:bg-brand-darkCard border border-brand-default/20 dark:border-brand-dark/30 p-2.5 rounded-xl flex flex-col leading-tight">
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide truncate" title={key.replace(/_/g, ' ')}>
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs font-black text-brand-dark dark:text-brand-default mt-1">
                            {val === null || val === undefined ? 'N/A' : String(val)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              ) : (
                <div className="flex flex-col items-center text-center py-16 px-4">
                  <Gauge className="w-14 h-14 text-brand-default/50 dark:text-brand-dark/50 mb-3.5 animate-pulse" />
                  <h4 className="text-xs font-bold text-slate-500 dark:text-slate-400">Ready for Analysis</h4>
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 max-w-[200px] leading-normal font-semibold">
                    Paste MRI report text or upload a report file on the left to start the analysis.
                  </p>
                </div>
              )}

            </div>
          </div>

        </div>
      )}

    </div>
  );
};

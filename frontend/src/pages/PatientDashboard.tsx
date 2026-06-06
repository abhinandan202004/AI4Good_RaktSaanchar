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
} from 'lucide-react';
import api from '../services/api';
import { BloodRequest, TransfusionPrediction } from '../types';

export const PatientDashboard: React.FC = () => {
  const { patientProfile, refreshProfiles } = useAuth();
  const [requests, setRequests] = useState<BloodRequest[]>([]);
  const [bloodGroup, setBloodGroup] = useState('O+');
  const [units, setUnits] = useState(1);
  const [urgency, setUrgency] = useState('medium');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Active Tab
  const [activeTab, setActiveTab] = useState<'requests' | 'predictor'>('requests');

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
        return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/10';
      case 'critical': 
        return 'bg-red-500 text-white border border-red-650 animate-pulse';
      default: 
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending': return <Clock className="w-4 h-4 text-slate-400" />;
      case 'matched': return <HeartHandshake className="w-4 h-4 text-amber-500" />;
      case 'accepted': return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'fulfilled': return <CheckCircle className="w-4 h-4 text-rose-500" />;
      case 'escalated': return <ShieldAlert className="w-4 h-4 text-red-500 animate-bounce" />;
      default: return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  if (!patientProfile) {
    return (
      <div className="max-w-lg mx-auto glass-panel p-8 mt-10 border border-slate-200/50 dark:border-slate-800/40">
        <h2 className="text-xl font-black mb-1.5 flex items-center gap-2 text-slate-800 dark:text-slate-100">
          <Activity className="text-rose-500 w-5.5 h-5.5" />
          Setup Patient Profile
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mb-6">
          Provide your hospital name and location coordinates to start requesting blood.
        </p>
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs p-3 rounded-xl font-bold mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleCreateProfile} className="flex flex-col gap-4">
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Hospital Name</label>
            <input
              type="text"
              placeholder="e.g. Mumbai Central Hospital"
              className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm transition-all text-slate-800 dark:text-slate-100"
              value={hospitalName}
              onChange={(e) => setHospitalName(e.target.value)}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">City</label>
              <input
                type="text"
                placeholder="Mumbai"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm transition-all text-slate-800 dark:text-slate-100"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">State</label>
              <input
                type="text"
                placeholder="Maharashtra"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm transition-all text-slate-800 dark:text-slate-100"
                value={state}
                onChange={(e) => setState(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Latitude</label>
              <input
                type="number"
                step="any"
                placeholder="19.0760"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm transition-all text-slate-800 dark:text-slate-100"
                value={latitude || ''}
                onChange={(e) => setLatitude(parseFloat(e.target.value))}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Longitude</label>
              <input
                type="number"
                step="any"
                placeholder="72.8777"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm transition-all text-slate-800 dark:text-slate-100"
                value={longitude || ''}
                onChange={(e) => setLongitude(parseFloat(e.target.value))}
                required
              />
            </div>
          </div>
          <button 
            type="submit" 
            className="w-full bg-rose-500 hover:bg-rose-650 text-white font-bold py-2.5 px-4 rounded-xl shadow-md hover:shadow-lg transition-all text-xs uppercase tracking-wider mt-4" 
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
      
      {/* Tabs */}
      <div className="flex justify-center">
        <div className="bg-white/40 dark:bg-slate-900/35 border border-slate-200 dark:border-slate-800/40 p-1.5 rounded-2xl shadow-sm flex gap-2">
          <button
            onClick={() => setActiveTab('requests')}
            className={`flex items-center gap-1.5 px-5 py-2 text-xs font-bold rounded-xl transition-all duration-200 ${
              activeTab === 'requests' 
                ? 'bg-rose-500 text-white shadow-sm' 
                : 'text-slate-500 dark:text-slate-400 hover:bg-white/20 dark:hover:bg-slate-800/20'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            Requests & Status
          </button>
          <button
            onClick={() => setActiveTab('predictor')}
            className={`flex items-center gap-1.5 px-5 py-2 text-xs font-bold rounded-xl transition-all duration-200 ${
              activeTab === 'predictor' 
                ? 'bg-rose-500 text-white shadow-sm' 
                : 'text-slate-500 dark:text-slate-400 hover:bg-white/20 dark:hover:bg-slate-800/20'
            }`}
          >
            <Brain className="w-3.5 h-3.5" />
            AI Transfusion Predictor
          </button>
        </div>
      </div>

      {activeTab === 'requests' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Request blood form Card */}
          <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 lg:col-span-4 h-fit p-6">
            <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-2">
              <Plus className="text-rose-500 w-4.5 h-4.5" />
              Request Blood Unit
            </h3>

            {error && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs p-2.5 rounded-xl font-bold mt-3">
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
                <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Blood Group</label>
                <div className="w-full bg-slate-100/50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-extrabold text-slate-800 dark:text-slate-100 flex items-center justify-between">
                  <span>{patientProfile?.blood_group_required || bloodGroup}</span>
                  <span className="text-[10px] text-rose-500 dark:text-rose-450 font-bold bg-rose-500/10 dark:bg-rose-500/20 px-2 py-0.5 rounded-lg border border-rose-500/10">
                    Auto-fetched from Profile
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Units Required</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-xs font-bold text-slate-800 dark:text-slate-100"
                  value={units}
                  onChange={(e) => setUnits(parseInt(e.target.value))}
                  required
                />
              </div>

              <div>
                <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Urgency Level</label>
                <select
                  className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2.5 text-xs font-bold text-slate-800 dark:text-slate-100"
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
                className="w-full bg-rose-500 hover:bg-rose-600 text-white font-bold py-2.5 px-4 rounded-xl shadow-md transition-all text-xs uppercase tracking-wider mt-3" 
                disabled={loading}
              >
                Submit Request
              </button>
            </form>
          </div>

          {/* Requests tracking list Card */}
          <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 lg:col-span-8 p-6">
            <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-2">
              <Activity className="text-rose-500 w-4.5 h-4.5" />
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
                        You haven't submitted any requests yet.
                      </td>
                    </tr>
                  ) : (
                    requests.map((req) => (
                      <tr key={req.id} className="hover:bg-slate-100/10 dark:hover:bg-slate-900/10 transition-colors">
                        <td className="py-4 font-bold text-slate-400">#{req.id}</td>
                        <td className="py-4">
                          <span className="inline-block bg-slate-800 text-white dark:bg-slate-800 font-extrabold text-xs px-2.5 py-0.5 rounded-lg border border-slate-700">
                            {req.blood_group}
                          </span>
                        </td>
                        <td className="py-4 font-bold text-slate-700 dark:text-slate-300">{req.units_required}</td>
                        <td className="py-4">
                          <span className={`inline-block px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase ${getUrgencyBadge(req.urgency)}`}>
                            {req.urgency}
                          </span>
                        </td>
                        <td className="py-4">
                          <div className="flex items-center gap-1.5 font-bold uppercase text-[9px]">
                            {getStatusIcon(req.status)}
                            <span className="text-slate-600 dark:text-slate-300">{req.status}</span>
                          </div>
                        </td>
                        <td className="py-4 font-semibold text-slate-500 dark:text-slate-400 max-w-[150px] truncate">
                          {req.status === 'accepted' ? (
                            req.assigned_donor_id ? (
                              <span className="text-emerald-500 dark:text-emerald-400 flex items-center gap-1">
                                💚 Donor Assigned
                              </span>
                            ) : req.assigned_blood_bank_id ? (
                              <span className="text-rose-500 dark:text-rose-450 flex items-center gap-1">
                                🏥 Blood Bank Claimed
                              </span>
                            ) : (
                              'Processing'
                            )
                          ) : req.status === 'matched' ? (
                            <span className="text-amber-500 font-bold">Matched, waiting donor...</span>
                          ) : (
                            'Search in progress'
                          )}
                        </td>
                        <td className="py-4 text-right">
                          {['pending', 'matched'].includes(req.status.toLowerCase()) && (
                            <button
                              onClick={() => cancelRequest(req.id)}
                              className="p-1.5 hover:bg-rose-500/10 rounded-lg text-rose-500 transition-all inline-flex items-center"
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

        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Form Column */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
              <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-2">
                <Sparkles className="text-rose-500 w-4.5 h-4.5 animate-pulse" />
                AI Transfusion Requirement Predictor
              </h3>

              {predError && (
                <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs p-3 rounded-xl font-bold mt-3">
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
                <div className="bg-slate-100/50 dark:bg-slate-900/20 p-4.5 rounded-2xl border border-slate-200/40 dark:border-slate-800/40">
                  <span className="text-[10px] font-black uppercase tracking-widest text-rose-500 flex items-center gap-1.5 mb-3.5">
                    <UserIcon className="w-3.5 h-3.5" />
                    Demographics & Blood Profile
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Patient ID</label>
                      <input
                        type="number"
                        placeholder="e.g. 1"
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
                        value={predAge}
                        onChange={(e) => setPredAge(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Gender</label>
                      <select
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
                        value={predWeight}
                        onChange={(e) => setPredWeight(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Blood Group</label>
                      <select
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100"
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
                <div className="bg-slate-100/50 dark:bg-slate-900/20 p-4.5 rounded-2xl border border-slate-200/40 dark:border-slate-800/40">
                  <span className="text-[10px] font-black uppercase tracking-widest text-rose-500 flex items-center gap-1.5 mb-3.5">
                    <Gauge className="w-3.5 h-3.5" />
                    Clinical & Hemoglobin Levels
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Thalassemia Type</label>
                      <select
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
                        value={predFerritin}
                        onChange={(e) => setPredFerritin(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Grid 3: Transfusion History */}
                <div className="bg-slate-100/50 dark:bg-slate-900/20 p-4.5 rounded-2xl border border-slate-200/40 dark:border-slate-800/40">
                  <span className="text-[10px] font-black uppercase tracking-widest text-rose-500 flex items-center gap-1.5 mb-3.5">
                    <CalendarDays className="w-3.5 h-3.5" />
                    Transfusion History
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Days Since Last (5 - 60)</label>
                      <input
                        type="number"
                        placeholder="e.g. 21"
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-100"
                        value={predTransfusions12M}
                        onChange={(e) => setPredTransfusions12M(e.target.value === '' ? '' : Number(e.target.value))}
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Grid 4: Symptom & Spleen Details */}
                <div className="bg-slate-100/50 dark:bg-slate-900/20 p-4.5 rounded-2xl border border-slate-200/40 dark:border-slate-800/40">
                  <span className="text-[10px] font-black uppercase tracking-widest text-rose-500 flex items-center gap-1.5 mb-3.5">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Symptoms & Spleen Condition
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Spleen Status</label>
                      <select
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100"
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
                        className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100"
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
                  className="bg-rose-500 hover:bg-rose-600 text-white font-bold py-2.5 px-4 rounded-xl shadow-md transition-all text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 disabled:opacity-50" 
                  disabled={predLoading}
                >
                  {predLoading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                  <Send className="w-3.5 h-3.5" />
                  Predict Requirement
                </button>

              </form>
            </div>

            {/* Prediction History Table */}
            <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
              <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-2">
                <History className="text-slate-450 w-4.5 h-4.5" />
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
                          <td className="py-3.5 text-slate-500 dark:text-slate-400">{new Date(historyItem.created_at).toLocaleDateString()}</td>
                          <td className="py-3.5 font-bold text-slate-700 dark:text-slate-300">
                            {historyItem.current_hb_level} ➔ {historyItem.target_hb_level} g/dL
                          </td>
                          <td className="py-3.5">
                            <span className="inline-block bg-slate-100/80 dark:bg-slate-800 text-[10px] font-bold px-2 py-0.5 rounded-md border border-slate-200/50 dark:border-slate-700/50 text-slate-600 dark:text-slate-300">
                              {historyItem.symptom_severity}
                            </span>
                          </td>
                          <td className="py-3.5 font-black text-rose-500 dark:text-rose-400">
                            {historyItem.predicted_units_required} Unit(s)
                          </td>
                          <td className="py-3.5 font-bold text-rose-500 dark:text-rose-400">
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
            <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6 sticky top-6">
              <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-2">
                <Brain className="text-rose-500 w-4.5 h-4.5 animate-pulse" />
                Model Output Result
              </h3>

              {predictionResult ? (
                <div className="flex flex-col items-center gap-5 mt-5">
                  
                  {/* Units Block */}
                  <div className="flex flex-col items-center p-5 bg-rose-500/5 border border-rose-500/10 w-full rounded-2xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-rose-500/5 rounded-full filter blur-xl"></div>
                    <Droplet className="w-10 h-10 text-rose-500 fill-rose-500 animate-bounce mb-2" />
                    <span className="text-2xl font-black text-rose-500">
                      {predictionResult.predicted_units_required} Unit(s)
                    </span>
                    <span className="text-[9px] uppercase font-bold text-slate-400 mt-1">
                      PRBC Volume Needed
                    </span>
                  </div>

                  {/* Timeline Block */}
                  <div className="flex flex-col items-center p-5 bg-rose-500/5 border border-rose-500/10 w-full rounded-2xl relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-rose-500/5 rounded-full filter blur-xl"></div>
                    <Clock className="w-10 h-10 text-rose-500 animate-pulse mb-2" />
                    <span className="text-2xl font-black text-rose-500">
                      {predictionResult.recommended_next_transfusion_in_days} Days
                    </span>
                    <span className="text-[9px] uppercase font-bold text-slate-400 mt-1">
                      Recommended Next Schedule
                    </span>
                  </div>

                  {/* Description Alert */}
                  <div className="bg-rose-500/5 border border-rose-500/10 text-xs leading-normal p-4 font-semibold text-slate-600 dark:text-slate-350 rounded-2xl">
                    <span>
                      Based on target Hb level and clinical conditions, our AI recommends administering{' '}
                      <strong className="text-rose-500">{predictionResult.predicted_units_required} Unit(s)</strong> of compatible{' '}
                      <strong className="text-rose-500">{predBloodGroup}</strong> blood, with the next transfusion scheduled in{' '}
                      <strong className="text-rose-500">{predictionResult.recommended_next_transfusion_in_days} Days</strong>.
                    </span>
                  </div>

                </div>
              ) : (
                <div className="flex flex-col items-center text-center py-16 px-4">
                  <Brain className="w-14 h-14 text-slate-300 dark:text-slate-700 mb-3.5" />
                  <h4 className="text-xs font-bold text-slate-500 dark:text-slate-400">Ready for Prediction</h4>
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 max-w-[200px] leading-normal font-semibold">
                    Please enter the clinical parameters on the left and click predict.
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

import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { redIcon, greenIcon, blueIcon } from '../utils/leaflet-setup';
import api from '../services/api';
import { DonorProfile, BloodRequest, ValidationReport } from '../types';
import { Heart as HeartIcon, CheckCircle2, ShieldAlert as ShieldIcon, Award as AwardIcon, MapPin as MapIcon, Download as DownloadIcon, User as UserIcon } from 'lucide-react';

export const DonorDashboard: React.FC = () => {
  const { donorProfile, refreshProfiles, user } = useAuth();
  const [activeUrgent, setActiveUrgent] = useState<BloodRequest[]>([]);
  const [reports, setReports] = useState<ValidationReport[]>([]);
  const [toggling, setToggling] = useState(false);
  const [hasActiveAssignment, setHasActiveAssignment] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const latestReport = reports.length > 0 ? reports[0] : null;
  const isFlagged = latestReport && latestReport.status === 'rejected' && !donorProfile?.is_available;

  const isOnCooldown = (() => {
    if (!donorProfile?.last_donated_at) return false;
    const lastDonated = new Date(donorProfile.last_donated_at);
    const ninetyDaysAgo = new Date();
    ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
    return lastDonated > ninetyDaysAgo;
  })();

  const [latVal, setLatVal] = useState<number | undefined>(undefined);
  const [lonVal, setLonVal] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (donorProfile) {
      setLatVal(donorProfile.latitude);
      setLonVal(donorProfile.longitude);
    }
  }, [donorProfile]);

  const saveLocation = async () => {
    if (latVal === undefined || lonVal === undefined) return;
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await api.patch('/donors/me', {
        latitude: latVal,
        longitude: lonVal
      });
      await refreshProfiles();
      setSuccess('Location updated successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update location.');
    } finally {
      setLoading(false);
    }
  };

  const teleportTo = async (lat?: number, lon?: number) => {
    if (lat === undefined || lon === undefined) return;
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await api.patch('/donors/me', {
        latitude: lat,
        longitude: lon,
        city: 'Teleported'
      });
      await refreshProfiles();
      setSuccess('Teleported successfully to request coordinates!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Teleport failed.');
    } finally {
      setLoading(false);
    }
  };

  // Profile setup fields if missing
  const [bloodGroup, setBloodGroup] = useState('O-');
  const [age, setAge] = useState(25);
  const [weight, setWeight] = useState(70);
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [latitude, setLatitude] = useState<number | undefined>(undefined);
  const [longitude, setLongitude] = useState<number | undefined>(undefined);

  const fetchData = async () => {
    try {
      const reqResp = await api.get<{ items: BloodRequest[] }>('/requests/');
      const urgentPending = reqResp.data.items.filter(
        r => r.status === 'pending' && ['high', 'critical'].includes(r.urgency.toLowerCase())
      );
      setActiveUrgent(urgentPending);
      
      const hasAssignment = reqResp.data.items.some(
        (r: BloodRequest) => r.status === 'accepted' && r.assigned_donor_id === donorProfile?.id
      );
      setHasActiveAssignment(hasAssignment);

      // Fetch validation reports
      const repResp = await api.get<ValidationReport[]>('/donors/me/validation-reports');
      setReports(repResp.data);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  };

  useEffect(() => {
    if (donorProfile) {
      fetchData();
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [donorProfile]);

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/donors/me', {
        blood_group: bloodGroup,
        age,
        weight,
        city,
        state,
        latitude: latitude || 19.0330,
        longitude: longitude || 73.0297
      });
      await refreshProfiles();
      setSuccess('Donor profile created successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create donor profile.');
    } finally {
      setLoading(false);
    }
  };

  const toggleAvailability = async () => {
    if (toggling) return;
    setToggling(true);
    setError('');
    setSuccess('');
    try {
      await api.patch('/donors/me/availability');
      await refreshProfiles();
      setSuccess('Availability updated successfully.');
    } catch (err: any) {
      setError('Failed to update availability.');
    } finally {
      setToggling(false);
    }
  };

  const acceptRequest = async (reqId: number) => {
    if (isFlagged) {
      setError('Accept block: Your profile is temporarily deactivated due to a health flag.');
      return;
    }
    if (isOnCooldown) {
      setError('Accept block: You are currently on a standard 3-month recovery cooldown.');
      return;
    }
    if (hasActiveAssignment) {
      setError('Accept block: You are already assigned to an active request. Please fulfill it first.');
      return;
    }
    if (!window.confirm('Do you want to accept this urgent request? (Once accepted, you commit to donate).')) return;
    setError('');
    setSuccess('');
    try {
      await api.patch(`/requests/${reqId}/accept-open`);
      setSuccess('Request accepted successfully! Go to active chat to coordinate.');
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to accept request (perhaps you are out of range or blood group is incompatible).');
    }
  };

  const downloadReportPdf = async (reportId: number, filename: string) => {
    try {
      setError('');
      const resp = await api.get(`/blood-bank/validation-reports/${reportId}/pdf`, {
        responseType: 'blob'
      });
      const file = new Blob([resp.data], { type: 'application/pdf' });
      const fileURL = URL.createObjectURL(file);
      const link = document.createElement('a');
      link.href = fileURL;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: any) {
      setError('PDF download blocked: Unauthorized access.');
    }
  };

  // Helper distance function for coordinate markers display
  const getDistance = (lat1?: number, lon1?: number, lat2?: number, lon2?: number) => {
    if (lat1 === undefined || lon1 === undefined || lat2 === undefined || lon2 === undefined) return null;
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  if (!donorProfile) {
    return (
      <div className="max-w-lg mx-auto glass-panel p-8 mt-10 border border-brand-default/30 dark:border-brand-dark/40">
        <h2 className="text-xl font-black mb-1.5 flex items-center gap-2 text-brand-dark dark:text-slate-100">
          <HeartIcon className="text-brand-dark dark:text-brand-default w-5.5 h-5.5" />
          Setup Donor Profile
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mb-6">
          Register your age, weight, and blood group to start matching with patients.
        </p>
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] text-xs p-3 rounded-xl font-bold mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleCreateProfile} className="flex flex-col gap-4">
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">Blood Group</label>
            <select
              className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
              value={bloodGroup}
              onChange={(e) => setBloodGroup(e.target.value)}
            >
              {['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'].map(bg => (
                <option key={bg} value={bg}>{bg}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">Age</label>
              <input
                type="number"
                min={18}
                max={65}
                className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
                value={age}
                onChange={(e) => setAge(parseInt(e.target.value))}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">Weight (kg)</label>
              <input
                type="number"
                min={45}
                className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
                value={weight}
                onChange={(e) => setWeight(parseFloat(e.target.value))}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">City</label>
              <input
                type="text"
                placeholder="Navi Mumbai"
                className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">State</label>
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
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">Latitude</label>
              <input
                type="number"
                step="any"
                placeholder="19.0330"
                className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/40 dark:border-brand-dark/50 focus:border-brand-dark focus:ring-1 focus:ring-brand-dark outline-none rounded-xl px-3 py-2 text-sm text-brand-dark dark:text-slate-100"
                value={latitude || ''}
                onChange={(e) => setLatitude(parseFloat(e.target.value))}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4] mb-1.5">Longitude</label>
              <input
                type="number"
                step="any"
                placeholder="73.0297"
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
            Save Profile
          </button>
        </form>
      </div>
    );
  }

  // Calculate distance for pending urgent alerts
  const enrichedAlerts = activeUrgent.map(req => {
    const dist = getDistance(
      donorProfile.latitude,
      donorProfile.longitude,
      req.patient?.latitude,
      req.patient?.longitude
    );
    return { ...req, distance_km: dist };
  }).filter(req => req.distance_km === null || req.distance_km <= 100.0); // Within 100 Km radius

  return (
    <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6 p-6">
      
      {/* Floating Header */}
      <div className="lg:col-span-12 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-transparent py-2 border-b border-brand-default/20 dark:border-brand-dark/20 mb-2">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-brand-light text-brand-dark border border-brand-default flex items-center justify-center font-black text-lg uppercase dark:bg-brand-dark dark:text-brand-light">
            {user?.full_name[0]}
          </div>
          <div>
            <span className="block text-[11px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Welcome back,</span>
            <h2 className="text-xl font-black text-brand-dark dark:text-white leading-tight mt-0.5">{user?.full_name}</h2>
          </div>
        </div>
        <div className="text-right flex items-center gap-2">
          <span className="inline-block bg-brand-dark text-white font-extrabold text-xs px-3 py-1 rounded-full dark:bg-brand-default dark:text-brand-dark border border-transparent">
            Blood Group: {donorProfile.blood_group}
          </span>
        </div>
      </div>

      {/* LEFT COLUMN: Sidebar cards (Availability, Stats, Badges) */}
      <div className="flex flex-col gap-6 lg:col-span-4">
        
        {/* Availability Toggle card */}
        <div className={`glass-panel p-6 flex flex-row justify-between items-center transition-all duration-300 ${donorProfile.is_available ? 'bg-emerald-50/50 border-emerald-500/30 dark:bg-emerald-950/15 dark:border-emerald-500/20' : 'border-brand-default/35 dark:border-brand-dark/40'}`}>
          <div>
            <h3 className="font-extrabold text-sm flex items-center gap-1.5 text-brand-dark dark:text-slate-200">
              <HeartIcon className="text-brand-dark dark:text-brand-default w-4.5 h-4.5 fill-brand-dark/20" />
              Donor Status
            </h3>
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold mt-1 leading-normal">
              {donorProfile.is_available ? 'Active & visible for dispatch' : 'Offline'}
            </p>
          </div>
          <button
            onClick={toggleAvailability}
            className={`w-10 h-10 flex items-center justify-center rounded-xl border transition-all ${
              donorProfile.is_available 
                ? 'bg-emerald-500 text-white border-transparent shadow-md hover:bg-emerald-600' 
                : 'bg-white dark:bg-brand-darkBg border-brand-default/40 dark:border-brand-dark/40 text-slate-400'
            }`}
            title="Toggle Availability"
            disabled={toggling}
          >
            <CheckCircle2 className="w-5 h-5" />
          </button>
        </div>

        {/* Stats card */}
        <div className="glass-panel p-6">
          <h3 className="text-[10px] font-black border-b border-brand-default/20 dark:border-brand-dark/20 pb-3 uppercase tracking-wider text-slate-400">
            Donor Performance Stats
          </h3>
          <div className="flex flex-col gap-4.5 mt-4 text-xs font-semibold">
            <div className="flex justify-between items-center">
              <span className="text-slate-500 dark:text-slate-400">Reliability Score</span>
              <span className="font-black text-brand-dark dark:text-brand-default text-base">{(donorProfile.reliability_score * 100).toFixed(0)}%</span>
            </div>
            <div className="h-[1px] bg-brand-default/20 dark:bg-brand-dark/20"></div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500 dark:text-slate-400">Response Rate</span>
              <span className="font-black text-brand-dark dark:text-brand-default text-base">{(donorProfile.response_rate * 100).toFixed(0)}%</span>
            </div>
            <div className="h-[1px] bg-brand-default/20 dark:bg-brand-dark/20"></div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500 dark:text-slate-400">Completed Donations</span>
              <span className="font-black text-brand-dark dark:text-brand-default text-base">{donorProfile.total_donations}</span>
            </div>
            <div className="h-[1px] bg-brand-default/20 dark:bg-brand-dark/20"></div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500 dark:text-slate-400">Donation Points</span>
              <span className="font-black text-[#2C5E7A] dark:text-brand-default text-base">{donorProfile.points || 0} pts</span>
            </div>
          </div>
        </div>

        {/* Gamification/Badges card */}
        <div className="glass-panel p-6">
          <h3 className="text-sm font-extrabold border-b border-brand-default/20 dark:border-brand-dark/20 pb-3 flex items-center gap-1.5 text-brand-dark dark:text-slate-100">
            <AwardIcon className="text-amber-500 w-4.5 h-4.5" />
            Achievements Badges
          </h3>
          {donorProfile.total_donations === 0 ? (
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold py-6 text-center leading-normal">
              Complete your first blood donation to start earning achievement badges!
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div className="flex flex-col items-center p-3 border border-brand-default/20 dark:border-brand-dark/30 rounded-xl bg-brand-light/10 dark:bg-brand-dark/10">
                <span className="text-2xl">🩸</span>
                <span className="font-bold text-[10px] mt-1 text-center text-slate-600 dark:text-slate-350">First Donation</span>
              </div>
              {donorProfile.total_donations >= 5 && (
                <div className="flex flex-col items-center p-3 border border-brand-default/20 dark:border-brand-dark/30 rounded-xl bg-brand-light/10 dark:bg-brand-dark/10">
                  <span className="text-2xl">🏆</span>
                  <span className="font-bold text-[10px] mt-1 text-center text-slate-600 dark:text-slate-350">Lifesaver</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Dev Location Desk */}
        <div className="glass-panel border border-brand-default/30 bg-brand-light/10 p-6 dark:bg-brand-dark/5 dark:border-brand-dark/40">
          <h3 className="text-sm font-extrabold border-b border-brand-default/20 pb-3 flex items-center gap-1.5 text-brand-dark dark:text-brand-default">
            <MapIcon className="w-4.5 h-4.5 animate-bounce" />
            Dev Location Desk
          </h3>
          <p className="text-[10px] text-slate-405 dark:text-slate-500 font-bold mb-3 mt-1.5 leading-normal">
            Update coordinates to simulate distance checks.
          </p>
          <div className="flex flex-col gap-2.5 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Latitude</label>
                <input
                  type="number"
                  step="any"
                  className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/45 dark:border-brand-dark/50 focus:border-brand-dark outline-none rounded-lg px-2.5 py-1.5 text-[11px] font-bold text-brand-dark dark:text-slate-100"
                  value={latVal ?? ''}
                  onChange={(e) => setLatVal(parseFloat(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Longitude</label>
                <input
                  type="number"
                  step="any"
                  className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/45 dark:border-brand-dark/50 focus:border-brand-dark outline-none rounded-lg px-2.5 py-1.5 text-[11px] font-bold text-brand-dark dark:text-slate-100"
                  value={lonVal ?? ''}
                  onChange={(e) => setLonVal(parseFloat(e.target.value))}
                />
              </div>
            </div>
            
            <button
              type="button"
              onClick={saveLocation}
              className="bg-brand-dark hover:bg-brand-dark/90 text-white font-bold py-1.5 rounded-lg transition-all text-[10px] uppercase tracking-wider mt-2.5 dark:bg-brand-default dark:text-brand-dark"
              disabled={loading}
            >
              Save Location
            </button>

            {(() => {
              const teleportTarget = activeUrgent.find(r => r.patient?.latitude !== undefined && r.patient?.longitude !== undefined);
              if (teleportTarget) {
                return (
                  <button
                    type="button"
                    onClick={() => teleportTo(teleportTarget.patient?.latitude, teleportTarget.patient?.longitude)}
                    className="border border-brand-default/40 bg-white/50 hover:bg-brand-light text-brand-dark font-bold py-1.5 rounded-lg transition-all text-[9px] uppercase tracking-wider mt-1 dark:bg-brand-dark dark:text-brand-light dark:border-brand-dark/30"
                    disabled={loading}
                  >
                    Teleport to #{teleportTarget.id} ({teleportTarget.patient?.city})
                  </button>
                );
              }
              return null;
            })()}
          </div>
        </div>

      </div>

      {/* RIGHT COLUMN: Main Panel Content (Map, Urgent Alerts, Reports) */}
      <div className="flex flex-col gap-6 lg:col-span-8">
        
        {isFlagged && latestReport && (
          <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] p-5 rounded-2xl flex items-start gap-3 shadow-sm">
            <ShieldIcon className="w-6 h-6 text-[#FF5E5E] shrink-0 mt-0.5" />
            <div className="flex flex-col gap-1 text-xs">
              <strong className="font-black text-sm text-[#FF5E5E]">⚠️ Account Deactivated: Lab Health Flag Alert</strong>
              <p className="font-bold leading-normal mt-0.5">
                Your profile availability has been paused because your latest blood unit validation report was flagged by the lab.
              </p>
              <div className="mt-3 p-3.5 bg-white/40 dark:bg-slate-900/40 rounded-xl border border-red-500/15">
                <div className="font-bold text-slate-700 dark:text-slate-350">Category: <span className="font-black text-[#FF5E5E]">{latestReport.issue_category}</span></div>
                <div className="font-semibold mt-1 text-slate-650 dark:text-slate-400">Feedback Notes: {latestReport.feedback_notes || 'No notes provided.'}</div>
                {latestReport.improvement_recommendations && (
                  <div className="font-semibold mt-1.5 text-emerald-600 dark:text-emerald-400 font-bold">Recommendation: {latestReport.improvement_recommendations}</div>
                )}
              </div>
            </div>
          </div>
        )}

        {isOnCooldown && (
          <div className="bg-emerald-50/60 border border-emerald-500/20 text-emerald-700 p-5 rounded-2xl flex items-start gap-3 shadow-sm dark:bg-emerald-950/10 dark:text-emerald-400">
            <CheckCircle2 className="w-6 h-6 text-emerald-500 shrink-0 mt-0.5" />
            <div className="flex flex-col gap-1 text-xs font-semibold">
              <strong className="font-black text-sm text-emerald-700 dark:text-emerald-350">⏳ Rest & Recovery Cooldown Active</strong>
              <p className="leading-normal mt-0.5">
                Thank you for your recent blood donation! To protect your health, you are on a standard 3-month (90 days) recovery cooldown. You will automatically become matchable again once this period expires.
              </p>
              <div className="mt-2 text-[10px] uppercase tracking-wider font-bold text-emerald-600/80">
                Last Donated: {new Date(donorProfile.last_donated_at!).toLocaleDateString()}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] text-xs p-3 rounded-xl font-bold">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs p-3 rounded-xl font-bold">
            {success}
          </div>
        )}

        {/* Leaflet Radius Map & Urgent Requests Card */}
        <div className="glass-panel overflow-hidden border-brand-default/35">
          <div className="p-6 pb-0">
            <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 flex items-center gap-1.5">
              <ShieldIcon className="text-brand-dark dark:text-brand-default w-4.5 h-4.5 animate-pulse" />
              100 Km Radius Urgent Radar Map
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
              Live broadcast alerts within 100 Km. Click marker or accept directly below.
            </p>
          </div>

          <div className="h-80 w-full mt-4 border-y border-brand-default/20 dark:border-brand-dark/20 z-10">
            {donorProfile.latitude && donorProfile.longitude ? (
              <MapContainer
                center={[donorProfile.latitude, donorProfile.longitude]}
                zoom={9}
                style={{ height: '100%', width: '100%' }}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                
                {/* Donor Marker */}
                <Marker position={[donorProfile.latitude, donorProfile.longitude]} icon={greenIcon}>
                  <Popup><span className="font-bold text-xs">You (Donor)</span></Popup>
                </Marker>

                {/* Patient Markers */}
                {enrichedAlerts.map(req => {
                  if (req.patient?.latitude && req.patient?.longitude) {
                    return (
                      <Marker key={req.id} position={[req.patient.latitude, req.patient.longitude]} icon={redIcon}>
                        <Popup>
                          <div className="p-2 flex flex-col gap-1 text-xs max-w-[200px] leading-normal font-semibold">
                            <div className="font-black text-[#FF5E5E] uppercase">🚨 Urgent Needed ({req.blood_group})</div>
                            <div className="h-[1px] bg-slate-150 my-1"></div>
                            <div className="text-slate-505">Hospital: <strong className="text-slate-705">{req.patient.hospital_name}</strong></div>
                            <div className="text-slate-505">Distance: <strong className="text-slate-705">{req.distance_km?.toFixed(1)} km</strong></div>
                            {isFlagged ? (
                              <div className="text-[#FF5E5E] font-bold text-center mt-2.5 text-[10px] uppercase tracking-wider">Deactivated (Health Flag)</div>
                            ) : isOnCooldown ? (
                              <div className="text-emerald-500 font-bold text-center mt-2.5 text-[10px] uppercase tracking-wider">Resting (Cooldown)</div>
                            ) : hasActiveAssignment ? (
                              <div className="text-amber-500 font-bold text-center mt-2.5 text-[10px] uppercase tracking-wider">Active Assignment</div>
                            ) : (
                              <button
                                onClick={() => acceptRequest(req.id)}
                                className="bg-brand-dark text-white font-extrabold rounded-lg mt-3.5 py-1.5 w-full text-[10px] uppercase tracking-wider transition-all dark:bg-brand-default dark:text-brand-dark"
                              >
                                Accept Donation
                              </button>
                            )}
                          </div>
                        </Popup>
                      </Marker>
                    );
                  }
                  return null;
                })}
              </MapContainer>
            ) : (
              <div className="flex items-center justify-center h-full bg-slate-100/30 text-xs text-slate-400 font-bold">
                Coordinates missing for Map display
              </div>
            )}
          </div>

          <div className="p-6">
            <h4 className="text-[10px] font-black uppercase tracking-wider text-slate-400 border-b border-brand-default/20 dark:border-brand-dark/20 pb-2.5 mb-3.5">
              Broadcast Alert Queue
            </h4>
            <div className="flex flex-col gap-3">
              {isFlagged ? (
                <div className="text-center py-6 text-xs text-[#FF5E5E] font-bold">
                  ⚠️ Your matching alerts radar is paused while your profile is deactivated.
                </div>
              ) : isOnCooldown ? (
                <div className="text-center py-6 text-xs text-emerald-500 font-bold">
                  ⏳ Matching radar is resting during your 3-month recovery cooldown.
                </div>
              ) : hasActiveAssignment ? (
                <div className="text-center py-6 text-xs text-amber-500 font-bold">
                  🚕 You currently have an active donation assignment. Please fulfill it before accepting new requests.
                </div>
              ) : enrichedAlerts.length === 0 ? (
                <div className="text-center py-6 text-xs text-slate-450 dark:text-slate-500 font-semibold">
                  No active urgent alerts within 100 Km radius.
                </div>
              ) : (
                enrichedAlerts.map(req => (
                  <div key={req.id} className="flex justify-between items-center p-4 border border-[#FF5E5E]/15 bg-[#FF5E5E]/5 rounded-2xl">
                    <div className="flex flex-col gap-0.5 leading-tight">
                      <span className="font-extrabold text-[#FF5E5E] flex items-center gap-1 text-sm">
                        🚨 {req.blood_group} Requested
                      </span>
                      <span className="text-xs text-slate-650 dark:text-slate-350 font-bold mt-1">
                        Hospital: {req.patient?.hospital_name || 'Local Hospital'}
                      </span>
                      <span className="text-[10px] text-slate-405 dark:text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1 mt-1">
                        <MapIcon className="w-3.5 h-3.5 text-[#FF5E5E]" />
                        {req.distance_km?.toFixed(1)} km away
                      </span>
                    </div>
                    <button
                      onClick={() => acceptRequest(req.id)}
                      disabled={isFlagged || isOnCooldown || hasActiveAssignment}
                      className="bg-brand-dark text-white dark:bg-brand-default dark:text-brand-dark hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed font-extrabold rounded-xl py-2 px-4 shadow-sm text-[10px] uppercase tracking-wider transition-all"
                    >
                      Accept
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Validation Reports Card */}
        <div className="glass-panel p-6">
          <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-100 border-b border-brand-default/20 dark:border-brand-dark/20 pb-3">
            Validation & Lab Health Reports
          </h3>
          
          <div className="overflow-x-auto mt-4">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-200/40 dark:border-slate-800/40">
                  <th className="pb-3.5 font-bold">Report ID</th>
                  <th className="pb-3.5 font-bold">Hemoglobin</th>
                  <th className="pb-3.5 font-bold">Vitals (BP/Pulse)</th>
                  <th className="pb-3.5 font-bold">Status</th>
                  <th className="pb-3.5 font-bold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/50 dark:divide-slate-900/30 text-xs">
                {reports.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-6 text-slate-400 dark:text-slate-500 font-semibold">
                      No lab reports registered yet.
                    </td>
                  </tr>
                ) : (
                  reports.map(rep => (
                    <tr key={rep.id} className="hover:bg-slate-100/10 dark:hover:bg-slate-900/10 transition-colors">
                      <td className="py-4 font-bold text-slate-400">#{rep.id}</td>
                      <td className="py-4 font-black text-brand-dark dark:text-brand-default">{rep.hemoglobin_g_dl} g/dL</td>
                      <td className="py-4 text-slate-500 dark:text-slate-450 font-bold">
                        {rep.systolic_bp}/{rep.diastolic_bp} mmHg, {rep.pulse_bpm} bpm
                      </td>
                      <td className="py-4">
                        <span className={`inline-block px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase ${
                          rep.status === 'approved' 
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-450 border border-emerald-500/10' 
                            : 'bg-red-500/10 text-[#FF5E5E] border border-red-500/10'
                        }`}>
                          {rep.status}
                        </span>
                      </td>
                      <td className="py-4 text-right">
                        <button
                          onClick={() => downloadReportPdf(rep.id, `report_${rep.id}.pdf`)}
                          className="bg-brand-dark hover:bg-brand-dark/95 text-white py-1.5 px-3.5 rounded-xl font-bold flex items-center gap-1.5 transition-all text-[10px] ml-auto dark:bg-brand-default dark:text-brand-dark"
                        >
                          <DownloadIcon className="w-3.5 h-3.5" />
                          PDF
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

    </div>
  );
};

import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { redIcon, greenIcon, blueIcon } from '../utils/leaflet-setup';
import api from '../services/api';
import { DonorProfile, BloodRequest, ValidationReport } from '../types';
import { Heart as HeartIcon, CheckCircle2, ShieldAlert as ShieldIcon, Award as AwardIcon, MapPin as MapIcon, Download as DownloadIcon } from 'lucide-react';

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
        (r: BloodRequest) => r.status === 'accepted' && r.assigned_donor_id === donorProfile.id
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
    if (!window.confirm('Do you want to accept this urgent request? (Like Uber - once accepted, you commit to donate).')) return;
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
      <div className="max-w-lg mx-auto glass-panel p-8 mt-10 border border-slate-200/50 dark:border-slate-800/40">
        <h2 className="text-xl font-black mb-1.5 flex items-center gap-2 text-slate-800 dark:text-slate-100">
          <HeartIcon className="text-rose-500 w-5.5 h-5.5" />
          Setup Donor Profile
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mb-6">
          Register your age, weight, and blood group to start matching with patients.
        </p>
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs p-3 rounded-xl font-bold mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleCreateProfile} className="flex flex-col gap-4">
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5 font-bold">Blood Group</label>
            <select
              className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
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
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5 font-bold">Age</label>
              <input
                type="number"
                min={18}
                max={65}
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                value={age}
                onChange={(e) => setAge(parseInt(e.target.value))}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5 font-bold">Weight (kg)</label>
              <input
                type="number"
                min={45}
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                value={weight}
                onChange={(e) => setWeight(parseFloat(e.target.value))}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5 font-bold">City</label>
              <input
                type="text"
                placeholder="Navi Mumbai"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5 font-bold">State</label>
              <input
                type="text"
                placeholder="Maharashtra"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                value={state}
                onChange={(e) => setState(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5 font-bold">Latitude</label>
              <input
                type="number"
                step="any"
                placeholder="19.0330"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                value={latitude || ''}
                onChange={(e) => setLatitude(parseFloat(e.target.value))}
                required
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5 font-bold">Longitude</label>
              <input
                type="number"
                step="any"
                placeholder="73.0297"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                value={longitude || ''}
                onChange={(e) => setLongitude(parseFloat(e.target.value))}
                required
              />
            </div>
          </div>
          <button 
            type="submit" 
            className="w-full bg-rose-500 hover:bg-rose-600 text-white font-bold py-2.5 px-4 rounded-xl shadow-md transition-all text-xs uppercase tracking-wider mt-4" 
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
    <div className="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      {/* Sidebar cards (Availability, Stats, Badges) */}
      <div className="flex flex-col gap-6 lg:col-span-4">
        
        {/* Availability Toggle card */}
        <div className={`glass-panel border p-6 flex flex-row justify-between items-center transition-all duration-300 ${donorProfile.is_available ? 'bg-emerald-500/5 border-emerald-500/20' : 'border-slate-200/50 dark:border-slate-800/40'}`}>
          <div>
            <h3 className="font-extrabold text-sm flex items-center gap-1.5 text-slate-800 dark:text-slate-200">
              <HeartIcon className="text-rose-500 w-4.5 h-4.5 fill-rose-500" />
              Donor Status
            </h3>
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold mt-1 leading-normal">
              {donorProfile.is_available ? 'You are active & visible for requests' : 'You are currently offline'}
            </p>
          </div>
          <button
            onClick={toggleAvailability}
            className={`w-10 h-10 flex items-center justify-center rounded-xl border transition-all ${
              donorProfile.is_available 
                ? 'bg-emerald-500 text-white border-transparent shadow-md hover:bg-emerald-600' 
                : 'bg-white/40 dark:bg-slate-900/10 border-slate-200 dark:border-slate-850 text-slate-400'
            }`}
            title="Toggle Availability"
            disabled={toggling}
          >
            <CheckCircle2 className="w-5 h-5" />
          </button>
        </div>

        {/* Stats card */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
          <h3 className="text-[10px] font-black border-b border-slate-200/40 dark:border-slate-800/40 pb-3 uppercase tracking-wider text-slate-400">
            Your Stats
          </h3>
          <div className="flex flex-col gap-4.5 mt-4 text-xs font-semibold">
            <div className="flex justify-between items-center">
              <span className="text-slate-500 dark:text-slate-400">Reliability Score</span>
              <span className="font-black text-rose-500 text-base">{(donorProfile.reliability_score * 100).toFixed(0)}%</span>
            </div>
            <div className="h-[1px] bg-slate-200/50 dark:bg-slate-800/30"></div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500 dark:text-slate-400">Response Rate</span>
              <span className="font-black text-rose-500 text-base">{(donorProfile.response_rate * 100).toFixed(0)}%</span>
            </div>
            <div className="h-[1px] bg-slate-200/50 dark:bg-slate-800/30"></div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500 dark:text-slate-400">Completed Donations</span>
              <span className="font-black text-rose-500 text-base">{donorProfile.total_donations}</span>
            </div>
            <div className="h-[1px] bg-slate-200/50 dark:bg-slate-800/30"></div>
            <div className="flex justify-between items-center">
              <span className="text-slate-500 dark:text-slate-400">Donation Points</span>
              <span className="font-black text-rose-500 text-base">{donorProfile.points || 0} pts</span>
            </div>
          </div>
        </div>

        {/* Gamification/Badges card */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
          <h3 className="text-sm font-extrabold border-b border-slate-200/40 dark:border-slate-800/40 pb-3 flex items-center gap-1.5 text-slate-800 dark:text-slate-100">
            <AwardIcon className="text-amber-500 w-4.5 h-4.5" />
            Achievements
          </h3>
          {donorProfile.total_donations === 0 ? (
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold py-6 text-center leading-normal">
              Complete your first blood donation to start earning achievement badges!
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div className="flex flex-col items-center p-3 border border-slate-200/30 dark:border-slate-800/30 rounded-xl bg-slate-100/30 dark:bg-slate-900/10">
                <span className="text-2xl">🩸</span>
                <span className="font-bold text-[10px] mt-1 text-center text-slate-600 dark:text-slate-350">First Donation</span>
              </div>
              {donorProfile.total_donations >= 5 && (
                <div className="flex flex-col items-center p-3 border border-slate-200/30 dark:border-slate-800/30 rounded-xl bg-slate-100/30 dark:bg-slate-900/10">
                  <span className="text-2xl">🏆</span>
                  <span className="font-bold text-[10px] mt-1 text-center text-slate-600 dark:text-slate-350">Lifesaver</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Dev Location Desk */}
        <div className="glass-panel border border-rose-500/10 bg-rose-500/5 p-6">
          <h3 className="text-sm font-extrabold border-b border-rose-500/10 pb-3 flex items-center gap-1.5 text-rose-500 dark:text-rose-400">
            <MapIcon className="w-4.5 h-4.5 animate-bounce" />
            Dev Location Desk
          </h3>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold mb-3 mt-1.5 leading-normal">
            Update coordinates to simulate distance checks.
          </p>
          <div className="flex flex-col gap-2.5 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Latitude</label>
                <input
                  type="number"
                  step="any"
                  className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200/60 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-[11px] font-bold text-slate-800 dark:text-slate-100"
                  value={latVal ?? ''}
                  onChange={(e) => setLatVal(parseFloat(e.target.value))}
                />
              </div>
              <div>
                <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">Longitude</label>
                <input
                  type="number"
                  step="any"
                  className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200/60 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-[11px] font-bold text-slate-800 dark:text-slate-100"
                  value={lonVal ?? ''}
                  onChange={(e) => setLonVal(parseFloat(e.target.value))}
                />
              </div>
            </div>
            
            <button
              type="button"
              onClick={saveLocation}
              className="bg-rose-500 hover:bg-rose-600 text-white font-bold py-1.5 rounded-lg transition-all text-[10px] uppercase tracking-wider mt-2.5"
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
                    className="border border-rose-500/25 bg-rose-500/5 hover:bg-rose-500/10 text-rose-500 dark:text-rose-450 font-bold py-1.5 rounded-lg transition-all text-[9px] uppercase tracking-wider mt-1"
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

      {/* Main Panel Content (Map, Urgent Alerts, Reports) */}
      <div className="flex flex-col gap-6 lg:col-span-8">
        {isFlagged && latestReport && (
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-450 p-5 rounded-2xl flex items-start gap-3 shadow-sm">
            <ShieldIcon className="w-6 h-6 text-rose-500 shrink-0 mt-0.5" />
            <div className="flex flex-col gap-1 text-xs">
              <strong className="font-black text-sm text-rose-700 dark:text-rose-400">⚠️ Account Deactivated: Lab Health Flag Alert</strong>
              <p className="font-bold leading-normal mt-0.5">
                Your profile availability has been paused because your latest blood unit validation report was flagged by the lab.
              </p>
              <div className="mt-3 p-3.5 bg-white/40 dark:bg-slate-900/40 rounded-xl border border-rose-500/15">
                <div className="font-bold text-slate-700 dark:text-slate-300">Category: <span className="font-black text-rose-500">{latestReport.issue_category}</span></div>
                <div className="font-semibold mt-1 text-slate-600 dark:text-slate-350">Feedback Notes: {latestReport.feedback_notes || 'No notes provided.'}</div>
                {latestReport.improvement_recommendations && (
                  <div className="font-semibold mt-1.5 text-emerald-600 dark:text-emerald-400">Recommendation: {latestReport.improvement_recommendations}</div>
                )}
              </div>
            </div>
          </div>
        )}

        {isOnCooldown && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 p-5 rounded-2xl flex items-start gap-3 shadow-sm">
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
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs p-3 rounded-xl font-bold">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs p-3 rounded-xl font-bold">
            {success}
          </div>
        )}

        {/* Leaflet Radius Map & Urgent Requests Card */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 overflow-hidden">
          <div className="p-6 pb-0">
            <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
              <ShieldIcon className="text-rose-500 w-4.5 h-4.5 animate-pulse" />
              100 Km Radius Urgent Radar
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-1">
              Live broadcast alerts within 100 Km. Click marker or accept directly below.
            </p>
          </div>

          <div className="h-80 w-full mt-4 border-y border-slate-200/50 dark:border-slate-800/40 z-10">
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
                          <div className="p-2 flex flex-col gap-1 text-xs max-w-[200px]">
                            <div className="font-black text-rose-500 uppercase">🚨 Critical Need ({req.blood_group})</div>
                            <div className="h-[1px] bg-slate-100 my-1"></div>
                            <div className="text-slate-500 font-medium">Hospital: <strong className="text-slate-700">{req.patient.hospital_name}</strong></div>
                            <div className="text-slate-500 font-medium">Distance: <strong className="text-slate-700">{req.distance_km?.toFixed(1)} km</strong></div>
                            {isFlagged ? (
                              <div className="text-rose-500 font-bold text-center mt-2.5 text-[10px] uppercase tracking-wider">Deactivated (Health Flag)</div>
                            ) : isOnCooldown ? (
                              <div className="text-emerald-500 font-bold text-center mt-2.5 text-[10px] uppercase tracking-wider">Resting (Cooldown)</div>
                            ) : hasActiveAssignment ? (
                              <div className="text-amber-500 font-bold text-center mt-2.5 text-[10px] uppercase tracking-wider">Active Assignment</div>
                            ) : (
                              <button
                                onClick={() => acceptRequest(req.id)}
                                className="bg-rose-500 hover:bg-rose-650 text-white font-extrabold rounded-lg mt-3.5 py-1.5 w-full text-[10px] uppercase tracking-wider transition-all"
                              >
                                Accept Direct Donation
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
            <h4 className="text-[10px] font-black uppercase tracking-wider text-slate-400 border-b border-slate-200/40 dark:border-slate-800/40 pb-2.5 mb-3.5">
              Broadcast Alert Queue
            </h4>
            <div className="flex flex-col gap-3">
              {isFlagged ? (
                <div className="text-center py-6 text-xs text-rose-500 font-bold">
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
                <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500 font-bold">
                  No active urgent alerts within 100 Km radius.
                </div>
              ) : (
                enrichedAlerts.map(req => (
                  <div key={req.id} className="flex justify-between items-center p-4 border border-rose-500/15 bg-rose-500/5 rounded-2xl">
                    <div className="flex flex-col gap-0.5 leading-tight">
                      <span className="font-extrabold text-rose-500 flex items-center gap-1 text-sm">
                        🚨 {req.blood_group} Requested
                      </span>
                      <span className="text-xs text-slate-600 dark:text-slate-350 font-bold mt-1">
                        Hospital: {req.patient?.hospital_name || 'Local Hospital'}
                      </span>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1 mt-1">
                        <MapIcon className="w-3.5 h-3.5 text-rose-500" />
                        {req.distance_km?.toFixed(1)} km away
                      </span>
                    </div>
                    <button
                      onClick={() => acceptRequest(req.id)}
                      className="bg-rose-500 hover:bg-rose-650 text-white font-extrabold rounded-xl py-2 px-4 shadow-md text-[10px] uppercase tracking-wider transition-all"
                    >
                      Accept (Uber-Style)
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Validation Reports Card */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
          <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100 border-b border-slate-200/50 dark:border-slate-800/50 pb-3">
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
                    <td colSpan={5} className="text-center py-6 text-slate-400 dark:text-slate-500 font-bold">
                      No lab reports registered yet.
                    </td>
                  </tr>
                ) : (
                  reports.map(rep => (
                    <tr key={rep.id} className="hover:bg-slate-100/10 dark:hover:bg-slate-900/10 transition-colors">
                      <td className="py-4 font-bold text-slate-400">#{rep.id}</td>
                      <td className="py-4 font-bold text-slate-700 dark:text-slate-300">{rep.hemoglobin_g_dl} g/dL</td>
                      <td className="py-4 text-slate-500 dark:text-slate-400 font-semibold">
                        {rep.systolic_bp}/{rep.diastolic_bp} mmHg, {rep.pulse_bpm} bpm
                      </td>
                      <td className="py-4">
                        <span className={`inline-block px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase ${
                          rep.status === 'approved' 
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/10' 
                            : 'bg-rose-500/10 text-rose-600 dark:text-rose-450 border border-rose-500/10'
                        }`}>
                          {rep.status}
                        </span>
                      </td>
                      <td className="py-4 text-right">
                        <button
                          onClick={() => downloadReportPdf(rep.id, `report_${rep.id}.pdf`)}
                          className="bg-rose-500 hover:bg-rose-600 text-white py-1 px-3 rounded-lg font-bold flex items-center gap-1.5 transition-all text-[10px] ml-auto"
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

import React, { useEffect, useState } from 'react';
import { 
  LayoutDashboard, 
  Users, 
  HeartHandshake, 
  Map as MapIcon, 
  Sparkles, 
  AlertCircle, 
  CheckCircle, 
  Navigation,
  TrendingUp,
  TrendingDown,
  Layers,
  Heart,
  Calendar,
  MessageSquare
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { redIcon, greenIcon, blueIcon } from '../utils/leaflet-setup';
import api from '../services/api';
import { BloodRequest } from '../types';

interface MapFeature {
  type: string;
  geometry: {
    type: string;
    coordinates: [number, number];
  };
  properties: {
    type: 'donor' | 'patient' | 'blood_bank';
    name: string;
    blood_group: string;
    urgency?: string;
    units_required?: number;
    status?: string;
    hospital_name?: string;
    address?: string;
    donor_id?: number;
    request_id?: number;
    blood_bank_id?: number;
  };
}

interface RankedDonor {
  donor_id: number;
  user_id: number;
  blood_group: string;
  city: string;
  is_available: boolean;
  reliability_score: number;
  response_rate: number;
  total_donations: number;
  blood_group_match: boolean;
  distance_km: number;
  engagement_score: number;
  match_probability: number;
}

export const CoordinatorDashboard: React.FC = () => {
  const [requests, setRequests] = useState<BloodRequest[]>([]);
  const [mapFeatures, setMapFeatures] = useState<MapFeature[]>([]);
  const [selectedRequest, setSelectedRequest] = useState<BloodRequest | null>(null);
  
  // ML Ranking states
  const [rankedDonors, setRankedDonors] = useState<RankedDonor[]>([]);
  const [matchingNote, setMatchingNote] = useState('Recommended matching based on AI compatibility model.');
  const [rankingLoading, setRankingLoading] = useState(false);

  // General action states
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    try {
      const reqResp = await api.get<any>('/requests/');
      setRequests(reqResp.data.items || []);

      const mapResp = await api.get('/ml/map-data');
      if (mapResp.data && mapResp.data.features) {
        setMapFeatures(mapResp.data.features);
      }
    } catch (err) {
      console.error('Failed to load coordinator data:', err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 6000);
    return () => clearInterval(interval);
  }, []);

  const runMlRanker = async (req: BloodRequest) => {
    setSelectedRequest(req);
    setRankedDonors([]);
    setRankingLoading(true);
    setError('');
    try {
      const resp = await api.post<RankedDonor[]>('/ml/rank-donors', {
        request_id: req.id,
        limit: 20
      });
      setRankedDonors(resp.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch ML donor rankings.');
    } finally {
      setRankingLoading(false);
    }
  };

  const manualAssign = async (donorId: number) => {
    if (!selectedRequest) return;
    if (!window.confirm('Do you want to manually assign this donor to the blood request?')) return;
    
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await api.post(`/requests/${selectedRequest.id}/assign`, {
        donor_id: donorId,
        note: matchingNote
      });
      setSuccess('Donor assigned successfully. Notifications sent to both parties.');
      setSelectedRequest(null);
      setRankedDonors([]);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Manual assignment failed.');
    } finally {
      setLoading(false);
    }
  };

  const escalateRequest = async (reqId: number) => {
    if (!window.confirm('Do you want to escalate this request? This will flag it and alert system administrators.')) return;
    setError('');
    setSuccess('');
    try {
      await api.patch(`/requests/${reqId}/escalate`, {
        note: 'Urgent escalation requested by coordinator desk.'
      });
      setSuccess('Request escalated successfully.');
      fetchData();
    } catch {
      setError('Escalation failed.');
    }
  };

  const getProbabilityColor = (prob: number) => {
    if (prob >= 0.85) return 'text-emerald-500 bg-emerald-500';
    if (prob >= 0.60) return 'text-amber-500 bg-amber-500';
    return 'text-[#FF5E5E] bg-[#FF5E5E]';
  };

  const getUrgencyBadge = (u: string) => {
    switch (u.toLowerCase()) {
      case 'low': 
        return 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/10';
      case 'medium': 
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/10';
      case 'high': 
        return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/15';
      case 'critical': 
        return 'bg-brand-accent text-white border border-transparent animate-pulse';
      default: 
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-405';
    }
  };

  // Mock static stats inspired by the Tabler dashboard mockup
  const stats = [
    {
      title: 'Active Requests',
      value: requests.filter(r => r.status === 'pending' || r.status === 'matched').length,
      trend: '+6%',
      isUp: true,
      desc: 'Pending matching',
      icon: <Layers className="w-5 h-5 text-brand-dark dark:text-brand-default" />
    },
    {
      title: 'Matched Today',
      value: requests.filter(r => r.status === 'accepted' || r.status === 'fulfilled').length,
      trend: '-3%',
      isUp: false,
      desc: 'Completed dispatches',
      icon: <HeartHandshake className="w-5 h-5 text-brand-dark dark:text-brand-default" />
    },
    {
      title: 'Active Donors',
      value: mapFeatures.filter(f => f.properties.type === 'donor').length || 4,
      trend: '+9%',
      isUp: true,
      desc: 'Online in system',
      icon: <Users className="w-5 h-5 text-brand-dark dark:text-brand-default" />
    },
    {
      title: 'Blood Banks',
      value: mapFeatures.filter(f => f.properties.type === 'blood_bank').length || 1,
      trend: '+3%',
      isUp: true,
      desc: 'Locations mapped',
      icon: <MapIcon className="w-5 h-5 text-brand-dark dark:text-brand-default" />
    }
  ];

  return (
    <div className="max-w-[1600px] mx-auto flex flex-col gap-6 p-6">
      
      {/* Title Header */}
      <div className="flex justify-between items-center border-b border-brand-default/20 dark:border-brand-dark/20 pb-4">
        <div>
          <h2 className="text-xl font-black text-brand-dark dark:text-slate-100">Coordinator Dashboard</h2>
          <p className="text-xs text-slate-450 dark:text-slate-500 font-semibold mt-0.5">Real-time system overview & dispatcher desk</p>
        </div>
      </div>

      {/* Alert boxes */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-[#FF5E5E] text-xs p-3 rounded-xl font-bold shadow-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs p-3 rounded-xl font-bold shadow-sm">
          {success}
        </div>
      )}

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, idx) => (
          <div key={idx} className="glass-panel p-5 flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <div className="flex flex-col">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">{stat.title}</span>
                <span className="text-2xl font-black text-brand-dark dark:text-white mt-2">{stat.value}</span>
              </div>
              <div className="p-2.5 bg-brand-light dark:bg-brand-dark/30 text-brand-dark dark:text-brand-default rounded-xl border border-brand-default/20">
                {stat.icon}
              </div>
            </div>
            <div className="flex items-center gap-1.5 mt-4 text-[10px] font-bold">
              <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md ${
                stat.isUp 
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-450' 
                  : 'bg-red-500/10 text-[#FF5E5E]'
              }`}>
                {stat.isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {stat.trend}
              </span>
              <span className="text-slate-400 dark:text-slate-500 font-semibold">{stat.desc}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Workspace layout */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        
        {/* LEFT AREA: System Requests & Development/Matching Activity */}
        <div className="flex flex-col gap-6 xl:col-span-6">
          
          {/* Requests Desk */}
          <div className="glass-panel overflow-hidden">
            <div className="p-5 border-b border-brand-default/20 dark:border-brand-dark/20">
              <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-200 flex items-center gap-2">
                <Layers className="text-[#2C5E7A] dark:text-brand-default w-4.5 h-4.5" />
                Active Blood Requests
              </h3>
            </div>
            
            <div className="overflow-x-auto max-h-[350px] overflow-y-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-brand-default/20 dark:border-brand-dark/20 bg-[#F4F8FA] dark:bg-brand-dark/10">
                    <th className="py-3 px-4 font-bold">ID</th>
                    <th className="py-3 px-4 font-bold">Blood Group</th>
                    <th className="py-3 px-4 font-bold">Urgency</th>
                    <th className="py-3 px-4 font-bold">Status</th>
                    <th className="py-3 px-4 font-bold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100/50 dark:divide-slate-900/30 text-xs">
                  {requests.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-6 text-slate-400 dark:text-slate-500 font-bold">
                        No active requests found.
                      </td>
                    </tr>
                  ) : (
                    requests.map(req => (
                      <tr key={req.id} className="hover:bg-slate-100/10 dark:hover:bg-slate-900/10 transition-colors">
                        <td className="py-3 px-4 font-extrabold text-xs text-slate-400">#{req.id}</td>
                        <td className="py-3 px-4">
                          <span className="inline-block bg-brand-dark text-white font-extrabold text-xs px-2.5 py-0.5 rounded-lg border border-transparent dark:bg-brand-default dark:text-brand-dark">{req.blood_group}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-block px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase ${getUrgencyBadge(req.urgency)}`}>
                            {req.urgency}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-[10px] font-black uppercase tracking-wider text-[#2C5E7A] dark:text-[#C7E5F4]">{req.status}</td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex gap-2 justify-end text-[10px] font-bold uppercase">
                            {req.status === 'pending' && (
                              <button
                                onClick={() => runMlRanker(req)}
                                className="bg-brand-dark text-white hover:opacity-90 py-1.5 px-3 rounded-xl flex items-center gap-1 transition-all dark:bg-brand-default dark:text-brand-dark"
                              >
                                <Sparkles className="w-3 h-3" />
                                AI Match
                              </button>
                            )}
                            {['pending', 'matched'].includes(req.status.toLowerCase()) && (
                              <button
                                onClick={() => escalateRequest(req.id)}
                                className="p-1.5 hover:bg-[#FF5E5E]/10 rounded-xl text-[#FF5E5E] transition-all inline-flex items-center"
                                title="Escalate Request"
                              >
                                <AlertCircle className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Activity Chart card */}
          <div className="glass-panel p-5">
            <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-200 mb-4 flex items-center gap-2">
              <Calendar className="text-brand-dark dark:text-brand-default w-4.5 h-4.5" />
              Platform Dispatch Activity
            </h3>
            
            {/* Inline SVG Chart showing line activity */}
            <div className="w-full bg-[#DDEFF7]/20 dark:bg-brand-dark/10 rounded-xl p-2 border border-brand-default/20 dark:border-brand-dark/20 relative">
              <svg viewBox="0 0 500 120" className="w-full h-32 text-brand-dark dark:text-brand-default">
                <defs>
                  <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="rgb(16, 53, 74)" stopOpacity="0.25"/>
                    <stop offset="100%" stopColor="rgb(16, 53, 74)" stopOpacity="0"/>
                  </linearGradient>
                </defs>
                {/* Grid Lines */}
                <line x1="0" y1="30" x2="500" y2="30" stroke="rgba(0,0,0,0.02)" strokeWidth="1" />
                <line x1="0" y1="60" x2="500" y2="60" stroke="rgba(0,0,0,0.02)" strokeWidth="1" />
                <line x1="0" y1="90" x2="500" y2="90" stroke="rgba(0,0,0,0.02)" strokeWidth="1" />
                
                {/* SVG Line path */}
                <path
                  d="M 0 95 Q 50 110 100 80 T 200 45 T 300 75 T 400 30 T 500 20"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
                {/* SVG Area fill */}
                <path
                  d="M 0 95 Q 50 110 100 80 T 200 45 T 300 75 T 400 30 T 500 20 L 500 120 L 0 120 Z"
                  fill="url(#chartGrad)"
                />
              </svg>
            </div>

            {/* List of recent activities */}
            <div className="flex flex-col gap-3.5 mt-6 border-t border-brand-default/20 dark:border-brand-dark/20 pt-4">
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">Activity Logs</span>
              
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-brand-light text-brand-dark font-extrabold border border-brand-default/30 dark:bg-brand-dark dark:text-brand-light dark:border-brand-dark/40">
                    MP
                  </div>
                  <div className="flex flex-col leading-tight">
                    <span className="font-bold text-brand-dark dark:text-slate-200">Mumbai Patient (O+) Request created</span>
                    <span className="text-[10px] text-slate-450 dark:text-slate-500 font-bold">Hospital dispatch pending</span>
                  </div>
                </div>
                <span className="text-slate-400 dark:text-slate-500 text-[10px] font-bold">Just now</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-brand-light text-brand-dark font-extrabold border border-brand-default/30 dark:bg-brand-dark dark:text-brand-light dark:border-brand-dark/40">
                    MB
                  </div>
                  <div className="flex flex-col leading-tight">
                    <span className="font-bold text-brand-dark dark:text-slate-200">Mumbai Blood Bank claimed Request #76</span>
                    <span className="text-[10px] text-slate-405 dark:text-slate-500 font-bold">Direct stock dispatch</span>
                  </div>
                </div>
                <span className="text-slate-400 dark:text-slate-500 text-[10px] font-bold">2 hrs ago</span>
              </div>
            </div>

          </div>

        </div>

        {/* RIGHT AREA: Interactive Map or AI Dispatch Center */}
        <div className="flex flex-col gap-6 xl:col-span-6">
          
          {selectedRequest ? (
            /* AI Matching Center */
            <div className="glass-panel border-brand-default/50 bg-[#DDEFF7]/20 dark:bg-brand-dark/10 p-6">
              <div className="flex justify-between items-center border-b border-brand-default/25 pb-3">
                <h3 className="text-base font-extrabold text-brand-dark dark:text-brand-default flex items-center gap-1.5">
                  <Sparkles className="w-5 h-5 animate-pulse" />
                  Manual AI Matcher Desk (Request #{selectedRequest.id})
                </h3>
                <button
                  onClick={() => setSelectedRequest(null)}
                  className="px-2.5 py-1 hover:bg-[#10354A]/10 text-brand-dark dark:text-brand-default text-xs rounded-lg font-bold"
                >
                  Close Desk
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 p-4 border border-brand-default/30 rounded-xl bg-white dark:bg-brand-darkBg mt-4 text-xs font-semibold shadow-sm">
                <div>Patient: <strong className="text-brand-dark dark:text-slate-200">{selectedRequest.patient?.user?.full_name || 'Mumbai Patient'}</strong></div>
                <div>Blood Group Required: <strong className="text-[#FF5E5E]">{selectedRequest.blood_group}</strong></div>
                <div>Hospital: <strong className="text-slate-700 dark:text-slate-350">{selectedRequest.patient?.hospital_name || 'Mumbai Central Hospital'}</strong></div>
                <div>Urgency: <strong className="text-slate-700 dark:text-slate-350">{selectedRequest.urgency}</strong></div>
              </div>

              <div className="flex flex-col gap-1 mt-4">
                <label className="block text-[10px] font-bold uppercase tracking-wider text-brand-dark dark:text-brand-default">Matching coordination note</label>
                <input
                  type="text"
                  className="w-full bg-white dark:bg-brand-darkBg border border-brand-default/45 dark:border-brand-dark/50 focus:border-brand-dark outline-none rounded-xl px-3 py-2 text-xs text-brand-dark dark:text-slate-100 mt-1"
                  value={matchingNote}
                  onChange={(e) => setMatchingNote(e.target.value)}
                />
              </div>

              <h4 className="font-extrabold text-[10px] uppercase tracking-wider text-brand-dark dark:text-brand-default border-b border-brand-default/20 pb-2 mt-5 mb-3.5">
                Top ML-Ranked Compatible Donors
              </h4>

              {rankingLoading ? (
                <div className="flex flex-col items-center py-12 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-brand-default/20 border-t-brand-dark dark:border-t-brand-default"></div>
                  <p className="text-xs text-brand-dark/80 font-bold mt-1 dark:text-brand-default">Running XGBoost Matcher...</p>
                </div>
              ) : (
                <div className="flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-1">
                  {rankedDonors.length === 0 ? (
                    <p className="text-center py-6 text-xs text-[#FF5E5E] font-bold">
                      No compatible available donors found in system.
                    </p>
                  ) : (
                    rankedDonors.map((donor, index) => (
                      <div key={donor.donor_id} className="flex flex-col gap-2 p-3 border border-brand-default/30 dark:border-brand-dark/40 rounded-xl bg-white dark:bg-brand-dark/10 hover:border-brand-default/60 transition-all shadow-sm">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-2">
                            <span className="font-extrabold text-[10px] text-slate-400">#{index + 1}</span>
                            <span className="font-extrabold text-xs text-brand-dark dark:text-slate-200">Donor ID #{donor.donor_id}</span>
                            <span className="inline-block bg-brand-dark text-white font-extrabold text-[10px] px-1.5 py-0.5 rounded-md border border-transparent dark:bg-brand-default dark:text-brand-dark">{donor.blood_group}</span>
                            <span className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider flex items-center gap-0.5">
                              <Navigation className="w-3 h-3 text-[#FF5E5E]" />
                              {donor.distance_km.toFixed(1)} km
                            </span>
                          </div>
                          <button
                            onClick={() => manualAssign(donor.donor_id)}
                            className="bg-brand-dark hover:bg-brand-dark/90 text-white font-bold py-1 px-2.5 rounded-lg text-[10px] uppercase tracking-wider transition-all dark:bg-brand-default dark:text-brand-dark"
                            disabled={loading}
                          >
                            Assign Match
                          </button>
                        </div>
                        
                        <div className="flex items-center gap-3 mt-1 text-[10px] font-bold">
                          <span className={`font-black uppercase tracking-wider ${getProbabilityColor(donor.match_probability).split(' ')[0]}`}>
                            {(donor.match_probability * 100).toFixed(1)}% Match
                          </span>
                          <div className="w-full bg-[#C7E5F4]/30 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${getProbabilityColor(donor.match_probability).split(' ')[1]}`}
                              style={{ width: `${donor.match_probability * 100}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          ) : (
            /* Map View */
            <div className="glass-panel overflow-hidden border-brand-default/35">
              <div className="p-5 border-b border-brand-default/20 dark:border-brand-dark/20">
                <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-200 flex items-center gap-2">
                  <MapIcon className="text-[#2C5E7A] dark:text-brand-default w-4.5 h-4.5" />
                  Active System Mapping radar
                </h3>
                <p className="text-xs text-slate-550 dark:text-slate-400 font-semibold mt-0.5">
                  Plots patients (red), donors (green), and blood banks (blue)
                </p>
              </div>

              <div className="h-[400px] w-full z-10">
                <MapContainer
                  center={[19.0760, 72.8777]} // Mumbai Central
                  zoom={10}
                  style={{ height: '100%', width: '100%' }}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  {mapFeatures.map((feature, idx) => {
                    const [lon, lat] = feature.geometry.coordinates;
                    const props = feature.properties;
                    
                    let icon = blueIcon;
                    if (props.type === 'donor') icon = greenIcon;
                    if (props.type === 'patient') icon = redIcon;

                    return (
                      <Marker key={idx} position={[lat, lon]} icon={icon}>
                        <Popup>
                          <div className="p-1.5 flex flex-col gap-1 text-xs leading-normal max-w-[200px] font-semibold">
                            <span className="font-extrabold uppercase text-[9px] text-slate-400 tracking-wider">
                              {props.type.replace('_', ' ')}
                            </span>
                            <span className="font-bold text-sm text-brand-dark">{props.name}</span>
                            {props.blood_group && (
                              <div>Blood Group: <strong className="text-[#FF5E5E]">{props.blood_group}</strong></div>
                            )}
                            {props.urgency && (
                              <div>Urgency: <strong>{props.urgency}</strong></div>
                            )}
                            {props.type === 'patient' && props.status === 'pending' && (
                              <button
                                onClick={() => {
                                  const matchingReq = requests.find(r => r.id === props.request_id);
                                  if (matchingReq) runMlRanker(matchingReq);
                                }}
                                className="bg-[#10354A] hover:bg-[#1A4B66] text-white font-extrabold rounded-lg mt-2.5 py-1.5 w-full text-[10px] uppercase tracking-wider transition-all dark:bg-brand-default dark:text-brand-dark"
                              >
                                Inspect AI Match
                              </button>
                            )}
                          </div>
                        </Popup>
                      </Marker>
                    );
                  })}
                </MapContainer>
              </div>
            </div>
          )}

          {/* Blood Stock Distribution Donut card */}
          <div className="glass-panel p-5 flex flex-col">
            <h3 className="text-base font-extrabold text-brand-dark dark:text-slate-200 mb-4 flex items-center gap-2">
              <Heart className="text-brand-dark dark:text-brand-default w-4.5 h-4.5" />
              System Blood Stock Distribution
            </h3>
            
            <div className="flex flex-col sm:flex-row items-center justify-around gap-6 py-2">
              {/* SVG Donut Chart */}
              <div className="relative flex items-center justify-center">
                <svg viewBox="0 0 100 100" className="w-32 h-32 transform -rotate-90">
                  {/* Background Track */}
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="rgba(0,0,0,0.02)" strokeWidth="8" />
                  {/* Segment O- (70%) */}
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="#10354A" strokeWidth="8" strokeDasharray="176 251" strokeDashoffset="0" />
                  {/* Segment O+ (20%) */}
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="#2C5E7A" strokeWidth="8" strokeDasharray="50 251" strokeDashoffset="-176" />
                  {/* Segment Other (10%) */}
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="#C7E5F4" strokeWidth="8" strokeDasharray="25 251" strokeDashoffset="-226" />
                </svg>
                <div className="absolute flex flex-col text-center">
                  <span className="text-base font-black text-brand-dark dark:text-brand-default">1,000ml</span>
                  <span className="text-[8px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">Total Store</span>
                </div>
              </div>

              {/* Legends list */}
              <div className="flex flex-col gap-2 text-xs font-bold text-[#10354A] dark:text-[#C7E5F4]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: '#10354A' }}></span>
                  <span>O- Group (70%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: '#2C5E7A' }}></span>
                  <span>O+ Group (20%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: '#C7E5F4' }}></span>
                  <span>Others (10%)</span>
                </div>
              </div>

            </div>

          </div>

        </div>

      </div>

    </div>
  );
};

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
    return 'text-rose-500 bg-rose-500';
  };

  // Mock static stats inspired by the Tabler dashboard mockup
  const stats = [
    {
      title: 'Active Requests',
      value: requests.filter(r => r.status === 'pending' || r.status === 'matched').length,
      trend: '+6%',
      isUp: true,
      desc: 'Pending matching',
      icon: <Layers className="w-5 h-5 text-rose-500" />
    },
    {
      title: 'Matched Today',
      value: requests.filter(r => r.status === 'accepted' || r.status === 'fulfilled').length,
      trend: '-3%',
      isUp: false,
      desc: 'Completed dispatches',
      icon: <HeartHandshake className="w-5 h-5 text-rose-500" />
    },
    {
      title: 'Active Donors',
      value: mapFeatures.filter(f => f.properties.type === 'donor').length || 4,
      trend: '+9%',
      isUp: true,
      desc: 'Online in system',
      icon: <Users className="w-5 h-5 text-rose-500" />
    },
    {
      title: 'Blood Banks',
      value: mapFeatures.filter(f => f.properties.type === 'blood_bank').length || 1,
      trend: '+3%',
      isUp: true,
      desc: 'Locations mapped',
      icon: <MapIcon className="w-5 h-5 text-rose-500" />
    }
  ];

  return (
    <div className="max-w-[1600px] mx-auto flex flex-col gap-6">
      
      {/* Title Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-black text-slate-800 dark:text-slate-100">Dashboard</h2>
          <p className="text-xs text-slate-455 dark:text-slate-500 font-semibold mt-0.5">System overview & coordination desk</p>
        </div>
      </div>

      {/* Alert boxes */}
      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs p-3 rounded-xl font-bold shadow-sm">
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
          <div key={idx} className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-5 flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <div className="flex flex-col">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">{stat.title}</span>
                <span className="text-2xl font-black text-slate-800 dark:text-slate-100 mt-2">{stat.value}</span>
              </div>
              <div className="p-2.5 bg-rose-500/10 dark:bg-rose-500/20 text-rose-500 rounded-xl border border-rose-500/10">
                {stat.icon}
              </div>
            </div>
            <div className="flex items-center gap-1.5 mt-4 text-[10px] font-bold">
              <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md ${
                stat.isUp 
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-450' 
                  : 'bg-rose-500/10 text-rose-600 dark:text-rose-450'
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
          <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 overflow-hidden">
            <div className="p-5 border-b border-slate-200/40 dark:border-slate-800/40">
              <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                <Layers className="text-rose-500 w-4.5 h-4.5" />
                Active Blood Requests
              </h3>
            </div>
            
            <div className="overflow-x-auto max-h-[350px] overflow-y-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-200/40 dark:border-slate-800/40 bg-slate-100/30 dark:bg-slate-900/10">
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
                          <span className="inline-block bg-slate-800 text-white font-extrabold text-xs px-2.5 py-0.5 rounded-lg border border-slate-700">{req.blood_group}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-block px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase ${
                            req.urgency.toLowerCase() === 'critical' ? 'bg-red-500 text-white animate-pulse' :
                            req.urgency.toLowerCase() === 'high' ? 'bg-rose-500/10 text-rose-600 dark:text-rose-450 border border-rose-500/15' : 
                            'bg-amber-500/10 text-amber-600 dark:text-amber-450 border border-amber-500/15'
                          }`}>
                            {req.urgency}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-[10px] font-black uppercase tracking-wider text-slate-600 dark:text-slate-350">{req.status}</td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex gap-2 justify-end text-[10px] font-bold uppercase">
                            {req.status === 'pending' && (
                              <button
                                onClick={() => runMlRanker(req)}
                                className="bg-rose-500 hover:bg-rose-600 text-white py-1 px-2.5 rounded-lg flex items-center gap-1 transition-all"
                              >
                                <Sparkles className="w-3 h-3" />
                                AI Match
                              </button>
                            )}
                            {['pending', 'matched'].includes(req.status.toLowerCase()) && (
                              <button
                                onClick={() => escalateRequest(req.id)}
                                className="p-1 hover:bg-rose-500/10 rounded-lg text-rose-500 transition-all inline-flex items-center"
                                title="Escalate Request"
                              >
                                <AlertCircle className="w-3.5 h-3.5" />
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

          {/* Development/Matching Activity Chart card */}
          <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-5">
            <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-200 mb-4 flex items-center gap-2">
              <Calendar className="text-rose-500 w-4.5 h-4.5" />
              Platform Matching Activity
            </h3>
            
            {/* Inline SVG Chart showing line activity */}
            <div className="w-full bg-slate-100/10 dark:bg-slate-900/10 rounded-xl p-2 border border-slate-200/30 dark:border-slate-800/40 relative">
              <svg viewBox="0 0 500 120" className="w-full h-32 text-rose-500">
                <defs>
                  <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="rgb(244, 63, 94)" stopOpacity="0.2"/>
                    <stop offset="100%" stopColor="rgb(244, 63, 94)" stopOpacity="0"/>
                  </linearGradient>
                </defs>
                {/* Grid Lines */}
                <line x1="0" y1="30" x2="500" y2="30" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />
                <line x1="0" y1="60" x2="500" y2="60" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />
                <line x1="0" y1="90" x2="500" y2="90" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />
                
                {/* SVG Line path */}
                <path
                  d="M 0 95 Q 50 110 100 80 T 200 45 T 300 75 T 400 30 T 500 20"
                  fill="none"
                  stroke="rgb(244, 63, 94)"
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
            <div className="flex flex-col gap-3.5 mt-6 border-t border-slate-200/40 dark:border-slate-800/40 pt-4">
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">Recent Activity Logs</span>
              
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-rose-500/10 text-rose-500 font-bold border border-rose-500/15">
                    MP
                  </div>
                  <div className="flex flex-col leading-tight">
                    <span className="font-bold text-slate-700 dark:text-slate-300">Mumbai Patient (O+) Request created</span>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 font-semibold">Hospital dispatch pending</span>
                  </div>
                </div>
                <span className="text-slate-400 dark:text-slate-500 text-[10px] font-bold">Just now</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-rose-500/10 text-rose-500 font-bold border border-rose-500/15">
                    MB
                  </div>
                  <div className="flex flex-col leading-tight">
                    <span className="font-bold text-slate-700 dark:text-slate-300">Mumbai Blood Bank claimed Request #76</span>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 font-semibold">Direct stock dispatch</span>
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
            <div className="glass-panel border border-rose-500/20 bg-rose-500/5 p-6 animate-fade-in">
              <div className="flex justify-between items-center border-b border-rose-500/10 pb-3">
                <h3 className="text-base font-extrabold text-rose-500 flex items-center gap-1.5">
                  <Sparkles className="w-5 h-5 animate-pulse" />
                  Manual AI Matcher Desk (Request #{selectedRequest.id})
                </h3>
                <button
                  onClick={() => setSelectedRequest(null)}
                  className="px-2.5 py-1 hover:bg-rose-500/10 text-rose-500 text-xs rounded-lg font-bold"
                >
                  Close Desk
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 p-4 border border-rose-500/10 rounded-xl bg-white/40 dark:bg-slate-900/20 mt-4 text-xs font-semibold shadow-inner">
                <div>Patient: <strong className="text-slate-800 dark:text-slate-100">{selectedRequest.patient?.user?.full_name || 'Mumbai Patient'}</strong></div>
                <div>Blood Group Required: <strong className="text-rose-500">{selectedRequest.blood_group}</strong></div>
                <div>Hospital: <strong className="text-slate-700 dark:text-slate-300">{selectedRequest.patient?.hospital_name || 'Mumbai Central Hospital'}</strong></div>
                <div>Urgency: <strong className="text-slate-700 dark:text-slate-300">{selectedRequest.urgency}</strong></div>
              </div>

              <div className="flex flex-col gap-1 mt-4">
                <label className="block text-[10px] font-bold uppercase tracking-wider text-rose-500 dark:text-rose-400">Matching coordination note</label>
                <input
                  type="text"
                  className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-xl px-3 py-2 text-xs text-slate-800 dark:text-slate-100 mt-1"
                  value={matchingNote}
                  onChange={(e) => setMatchingNote(e.target.value)}
                />
              </div>

              <h4 className="font-extrabold text-[10px] uppercase tracking-wider text-rose-500 dark:text-rose-450 border-b border-rose-500/10 pb-2 mt-5 mb-3.5">
                Top ML-Ranked Compatible Donors
              </h4>

              {rankingLoading ? (
                <div className="flex flex-col items-center py-12 gap-2">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-rose-500/20 border-t-rose-500"></div>
                  <p className="text-xs text-rose-500/80 font-bold mt-1">Running XGBoost Matcher...</p>
                </div>
              ) : (
                <div className="flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-1">
                  {rankedDonors.length === 0 ? (
                    <p className="text-center py-6 text-xs text-rose-500/50 font-bold">
                      No compatible available donors found in system.
                    </p>
                  ) : (
                    rankedDonors.map((donor, index) => (
                      <div key={donor.donor_id} className="flex flex-col gap-2 p-3 border border-slate-200/50 dark:border-slate-800/40 rounded-xl bg-white/40 dark:bg-slate-900/10 hover:border-rose-500/30 transition-all shadow-sm">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-2">
                            <span className="font-extrabold text-[10px] text-slate-400">#{index + 1}</span>
                            <span className="font-extrabold text-xs text-slate-800 dark:text-slate-200">Donor ID #{donor.donor_id}</span>
                            <span className="inline-block bg-slate-800 text-white font-extrabold text-[10px] px-1.5 py-0.5 rounded-md border border-slate-700">{donor.blood_group}</span>
                            <span className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider flex items-center gap-0.5">
                              <Navigation className="w-3 h-3 text-rose-500" />
                              {donor.distance_km.toFixed(1)} km
                            </span>
                          </div>
                          <button
                            onClick={() => manualAssign(donor.donor_id)}
                            className="bg-rose-500 hover:bg-rose-600 text-white font-bold py-1 px-2.5 rounded-lg text-[10px] uppercase tracking-wider transition-all"
                            disabled={loading}
                          >
                            Assign Match
                          </button>
                        </div>
                        
                        <div className="flex items-center gap-3 mt-1 text-[10px] font-bold">
                          <span className={`font-black uppercase tracking-wider ${getProbabilityColor(donor.match_probability).split(' ')[0]}`}>
                            {(donor.match_probability * 100).toFixed(1)}% Match
                          </span>
                          <div className="w-full bg-slate-200/50 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
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
            <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 overflow-hidden">
              <div className="p-5 border-b border-slate-200/40 dark:border-slate-800/40">
                <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                  <MapIcon className="text-rose-500 w-4.5 h-4.5" />
                  Active System Mapping
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mt-0.5">
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
                          <div className="p-1.5 flex flex-col gap-1 text-xs leading-normal max-w-[200px]">
                            <span className="font-extrabold uppercase text-[9px] text-slate-400 tracking-wider">
                              {props.type.replace('_', ' ')}
                            </span>
                            <span className="font-bold text-sm text-slate-800">{props.name}</span>
                            {props.blood_group && (
                              <div>Blood Group: <strong className="text-rose-500">{props.blood_group}</strong></div>
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
                                className="bg-rose-500 hover:bg-rose-650 text-white font-extrabold rounded-lg mt-2.5 py-1.5 w-full text-[10px] uppercase tracking-wider transition-all"
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
          <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-5 flex flex-col">
            <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-200 mb-4 flex items-center gap-2">
              <Heart className="text-rose-500 w-4.5 h-4.5" />
              System Blood Stock Distribution
            </h3>
            
            <div className="flex flex-col sm:flex-row items-center justify-around gap-6 py-2">
              {/* SVG Donut Chart */}
              <div className="relative flex items-center justify-center">
                <svg viewBox="0 0 100 100" className="w-32 h-32 transform -rotate-90">
                  {/* Background Track */}
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
                  {/* Segment O- (70%) */}
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="#E53935" strokeWidth="8" strokeDasharray="176 251" strokeDashoffset="0" />
                  {/* Segment O+ (20%) */}
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="#FDA4AF" strokeWidth="8" strokeDasharray="50 251" strokeDashoffset="-176" />
                  {/* Segment Other (10%) */}
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="#FECDD3" strokeWidth="8" strokeDasharray="25 251" strokeDashoffset="-226" />
                </svg>
                <div className="absolute flex flex-col text-center">
                  <span className="text-lg font-black text-rose-500">1,000ml</span>
                  <span className="text-[8px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">Total Store</span>
                </div>
              </div>

              {/* Legends list */}
              <div className="flex flex-col gap-2 text-xs font-bold text-slate-600 dark:text-slate-350">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-rose-550 rounded-full" style={{ backgroundColor: '#E53935' }}></span>
                  <span>O- Group (70%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-rose-300 rounded-full" style={{ backgroundColor: '#FDA4AF' }}></span>
                  <span>O+ Group (20%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-rose-200 rounded-full" style={{ backgroundColor: '#FECDD3' }}></span>
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

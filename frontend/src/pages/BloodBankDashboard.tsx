import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, Plus, Check, FileText, Upload, Heart, Inbox, Activity } from 'lucide-react';
import api from '../services/api';
import { BloodInventory, BloodUnit, BloodRequest, BloodBankProfile } from '../types';

export const BloodBankDashboard: React.FC = () => {
  const { bloodBankProfile, refreshProfiles, user } = useAuth();
  
  // Database states
  const [inventory, setInventory] = useState<BloodInventory[]>([]);
  const [checkedUnits, setCheckedUnits] = useState<BloodUnit[]>([]);
  const [nearbyRequests, setNearbyRequests] = useState<BloodRequest[]>([]);
  const [assignedRequests, setAssignedRequests] = useState<BloodRequest[]>([]);

  // Action states
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Profile setup fields if missing
  const [hospitalName, setHospitalName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [address, setAddress] = useState('');
  const [latitude, setLatitude] = useState<number | undefined>(undefined);
  const [longitude, setLongitude] = useState<number | undefined>(undefined);

  // Form states: Inventory
  const [invBloodGroup, setInvBloodGroup] = useState('O-');
  const [invQty, setInvQty] = useState(1000);

  // Form states: Check-In
  const [checkDonorId, setCheckDonorId] = useState('');
  const [checkBloodGroup, setCheckBloodGroup] = useState('O-');
  const [checkVolume, setCheckVolume] = useState(450);
  const [checkNotes, setCheckNotes] = useState('');

  // Form states: Validation Report
  const [activeUnitId, setActiveUnitId] = useState<number | null>(null);
  const [hemoglobin, setHemoglobin] = useState(14.5);
  const [sysBp, setSysBp] = useState(120);
  const [diaBp, setDiaBp] = useState(80);
  const [pulse, setPulse] = useState(72);
  const [repStatus, setRepStatus] = useState<'approved' | 'rejected'>('approved');
  const [repNotes, setRepNotes] = useState('Perfect vitals');
  const [repRecs, setRepRecs] = useState('Keep hydrated and donate regularly');
  
  // PDF Upload states
  const [activeReportId, setActiveReportId] = useState<number | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchData = async () => {
    try {
      const invResp = await api.get<any>('/blood-bank/inventory');
      setInventory(invResp.data.items || []);

      const unitResp = await api.get<BloodUnit[]>('/blood-bank/units');
      setCheckedUnits(unitResp.data);

      const reqResp = await api.get<any>('/requests/');
      const items = reqResp.data.items || [];
      const pendingReqs = items.filter((r: any) => r.status === 'pending');
      setNearbyRequests(pendingReqs);

      if (user) {
        const assigned = items.filter(
          (r: any) => r.assigned_blood_bank_id === user.id && r.status === 'accepted'
        );
        setAssignedRequests(assigned);
      }
    } catch (err) {
      console.error('Failed to load blood bank data:', err);
    }
  };

  useEffect(() => {
    if (bloodBankProfile) {
      fetchData();
      const interval = setInterval(fetchData, 5000);
      return () => clearInterval(interval);
    }
  }, [bloodBankProfile]);

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/blood-bank/profile', {
        hospital_name: hospitalName,
        contact_phone: contactPhone,
        address,
        latitude: latitude || 19.0760,
        longitude: longitude || 72.8777
      });
      await refreshProfiles();
      setSuccess('Blood Bank profile created successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create blood bank profile.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      await api.post('/blood-bank/inventory', {
        blood_group: invBloodGroup,
        quantity_ml: invQty
      });
      setSuccess('Inventory stock updated.');
      fetchData();
    } catch (err: any) {
      setError('Failed to update stock.');
    }
  };

  const handleDonorCheckIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const matchingInv = inventory.find(i => i.blood_group === checkBloodGroup);
      if (!matchingInv) {
        throw new Error(`Please credit or set up an inventory stock entry for group ${checkBloodGroup} first.`);
      }

      await api.post('/blood-bank/units/check-in', {
        inventory_id: matchingInv.id,
        donor_id: parseInt(checkDonorId),
        blood_group: checkBloodGroup,
        volume_ml: checkVolume,
        notes: checkNotes
      });

      setSuccess('Blood unit checked in successfully!');
      setCheckDonorId('');
      setCheckNotes('');
      fetchData();
    } catch (err: any) {
      setError(err.message || err.response?.data?.detail || 'Donor ID must be valid and registered.');
    } finally {
      setLoading(false);
    }
  };

  const validateQuality = async (unitId: number, isSafe: boolean) => {
    try {
      await api.patch(`/blood-bank/units/${unitId}/quality`, {
        status: isSafe ? 'available' : 'discarded',
        is_safe: isSafe
      });
      setSuccess(`Unit quality marked as ${isSafe ? 'safe/available' : 'discarded'}.`);
      fetchData();
    } catch {
      setError('Failed to update quality.');
    }
  };

  const confirmDonation = async (reqId: number) => {
    if (!window.confirm('Are you sure you want to confirm this donation? This will update the request and enforce a 3-month cooldown for the donor.')) return;
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await api.patch(`/requests/${reqId}/confirm-donation`);
      setSuccess('Donation confirmed successfully! Cooldown applied.');
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to confirm donation.');
    } finally {
      setLoading(false);
    }
  };

  const submitValidationReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeUnitId) return;
    setError('');
    setSuccess('');
    try {
      const resp = await api.post(`/blood-bank/units/${activeUnitId}/validation-report`, {
        hemoglobin_g_dl: hemoglobin,
        systolic_bp: sysBp,
        diastolic_bp: diaBp,
        pulse_bpm: pulse,
        status: repStatus,
        feedback_notes: repNotes,
        improvement_recommendations: repRecs
      });
      setSuccess('Validation report submitted.');
      setActiveReportId(resp.data.id);
      setActiveUnitId(null);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Report submission failed.');
    }
  };

  const uploadPdfReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeReportId || !selectedFile) return;
    setError('');
    setSuccess('');
    setLoading(true);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      await api.post(`/blood-bank/validation-reports/${activeReportId}/pdf`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setSuccess('PDF validation report uploaded successfully!');
      setActiveReportId(null);
      setSelectedFile(null);
      fetchData();
    } catch {
      setError('PDF upload failed.');
    } finally {
      setLoading(false);
    }
  };

  const acceptPatientRequest = async (reqId: number) => {
    if (!window.confirm('Do you want to accept this request? (Once accepted, your blood bank commits to fulfill it).')) return;
    setError('');
    setSuccess('');
    try {
      await api.patch(`/requests/${reqId}/accept-bank`);
      setSuccess('Blood request claimed successfully.');
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to claim request (distance is likely more than 100 Km).');
    }
  };

  if (!bloodBankProfile) {
    return (
      <div className="max-w-lg mx-auto glass-panel p-8 mt-10 border border-slate-200/50 dark:border-slate-800/40">
        <h2 className="text-xl font-black mb-1.5 flex items-center gap-2 text-slate-800 dark:text-slate-100">
          <ShieldCheck className="text-rose-500 w-5.5 h-5.5" />
          Setup Blood Bank Profile
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold mb-6">
          Register hospital details and GPS coordinates to coordinate pickups.
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
              placeholder="e.g. Mumbai Central Blood Bank"
              className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
              value={hospitalName}
              onChange={(e) => setHospitalName(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Contact Phone</label>
            <input
              type="text"
              placeholder="022-9876543"
              className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Address</label>
            <input
              type="text"
              placeholder="Mumbai Central, Mumbai"
              className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Latitude</label>
              <input
                type="number"
                step="any"
                placeholder="19.0760"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
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

  return (
    <div className="max-w-[1600px] mx-auto grid grid-cols-1 xl:grid-cols-12 gap-6">
      
      {/* Messages */}
      <div className="xl:col-span-12 flex flex-col gap-2">
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
      </div>

      {/* LEFT COLUMN: Inventory and Desk Setup */}
      <div className="flex flex-col gap-6 xl:col-span-4">
        
        {/* Inventory Stock Grid */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
          <h3 className="text-[10px] font-black border-b border-slate-200/40 dark:border-slate-800/40 pb-3 uppercase tracking-wider text-slate-400">
            Live Stock Levels
          </h3>

          <div className="grid grid-cols-4 gap-2.5 mt-4 text-xs">
            {['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'].map(bg => {
              const inv = inventory.find(i => i.blood_group === bg);
              const qty = inv ? inv.quantity_ml : 0;
              return (
                <div key={bg} className={`flex flex-col items-center p-2 rounded-xl border transition-all ${qty > 0 ? 'bg-rose-500/10 border-rose-500/20 font-bold text-rose-500' : 'bg-slate-100/40 border-slate-200/40 dark:bg-slate-900/10 dark:border-slate-850 opacity-60'}`}>
                  <span className="font-extrabold">{bg}</span>
                  <span className="text-[10px] font-semibold mt-1">{qty} ml</span>
                </div>
              );
            })}
          </div>

          {/* Set Stock Form */}
          <form onSubmit={handleAddStock} className="flex gap-2.5 items-end mt-6 border-t border-slate-200/40 dark:border-slate-800/40 pt-4">
            <div className="flex-1">
              <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-550 dark:text-slate-450 mb-1">Blood</label>
              <select
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2 py-1 text-xs font-bold text-slate-800 dark:text-slate-100"
                value={invBloodGroup}
                onChange={(e) => setInvBloodGroup(e.target.value)}
              >
                {['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'].map(bg => (
                  <option key={bg} value={bg}>{bg}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-[9px] font-bold uppercase tracking-wider text-slate-550 dark:text-slate-450 mb-1">Qty (ml)</label>
              <input
                type="number"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1 text-xs font-bold text-slate-800 dark:text-slate-100"
                value={invQty}
                onChange={(e) => setInvQty(parseInt(e.target.value))}
              />
            </div>
            <button type="submit" className="bg-rose-500 hover:bg-rose-600 text-white font-bold py-1 px-3.5 rounded-lg text-xs uppercase tracking-wider transition-all">Set</button>
          </form>
        </div>

        {/* Check-In Desk Form */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
          <h3 className="text-base font-extrabold border-b border-slate-200/40 dark:border-slate-800/40 pb-3 flex items-center gap-2 text-slate-800 dark:text-slate-200">
            <Plus className="w-5 h-5 text-rose-500" />
            Donor Unit Check-In
          </h3>
          <form onSubmit={handleDonorCheckIn} className="flex flex-col gap-3.5 mt-4">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Donor ID</label>
              <input
                type="number"
                placeholder="e.g. 99"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                value={checkDonorId}
                onChange={(e) => setCheckDonorId(e.target.value)}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Blood Group</label>
                <select
                  className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100"
                  value={checkBloodGroup}
                  onChange={(e) => setCheckBloodGroup(e.target.value)}
                >
                  {['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'].map(bg => (
                    <option key={bg} value={bg}>{bg}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Volume (ml)</label>
                <input
                  type="number"
                  className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                  value={checkVolume}
                  onChange={(e) => setCheckVolume(parseInt(e.target.value))}
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1.5">Vitals / Notes</label>
              <input
                type="text"
                placeholder="Healthy vitals, safe check-in"
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-100"
                value={checkNotes}
                onChange={(e) => setCheckNotes(e.target.value)}
              />
            </div>
            <button 
              type="submit" 
              className="w-full bg-rose-500 hover:bg-rose-600 text-white font-bold py-2.5 px-4 rounded-xl shadow-md transition-all text-xs uppercase tracking-wider mt-2" 
              disabled={loading}
            >
              Check-In Blood Unit
            </button>
          </form>
        </div>

      </div>

      {/* RIGHT COLUMN: Checked-in units quality desks & PDF workspace */}
      <div className="flex flex-col gap-6 xl:col-span-8">
        
        {/* Validation Reports & Upload Dialogs */}
        {(activeUnitId || activeReportId) && (
          <div className="glass-panel border border-rose-500/10 bg-rose-500/5 p-6 animate-fade-in">
            {activeUnitId && (
              <form onSubmit={submitValidationReport} className="flex flex-col gap-4">
                <h3 className="font-extrabold text-base flex items-center gap-1.5 text-rose-500 border-b border-rose-500/10 pb-2">
                  <FileText className="w-5 h-5" />
                  Generate Lab Validation Report (Unit #{activeUnitId})
                </h3>
                <div className="grid grid-cols-4 gap-3">
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-rose-500 dark:text-rose-400 mb-1">Hemoglobin (g/dL)</label>
                    <input
                      type="number"
                      step="any"
                      className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800 dark:text-slate-100"
                      value={hemoglobin}
                      onChange={(e) => setHemoglobin(parseFloat(e.target.value))}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-rose-500 dark:text-rose-400 mb-1">Systolic BP</label>
                    <input
                      type="number"
                      className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800 dark:text-slate-100"
                      value={sysBp}
                      onChange={(e) => setSysBp(parseInt(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-rose-500 dark:text-rose-400 mb-1">Diastolic BP</label>
                    <input
                      type="number"
                      className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800 dark:text-slate-100"
                      value={diaBp}
                      onChange={(e) => setDiaBp(parseInt(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-rose-500 dark:text-rose-400 mb-1">Pulse (bpm)</label>
                    <input
                      type="number"
                      className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-xs font-bold text-slate-800 dark:text-slate-100"
                      value={pulse}
                      onChange={(e) => setPulse(parseInt(e.target.value))}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-rose-500 dark:text-rose-400 mb-1">Status</label>
                    <select
                      className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2 py-1.5 text-xs font-semibold text-slate-800 dark:text-slate-100"
                      value={repStatus}
                      onChange={(e: any) => setRepStatus(e.target.value)}
                    >
                      <option value="approved">Approved (Safe to Use)</option>
                      <option value="rejected">Rejected (Flag health issue)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-wider text-rose-500 dark:text-rose-400 mb-1">Vitals Notes</label>
                    <input
                      type="text"
                      className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-100"
                      value={repNotes}
                      onChange={(e) => setRepNotes(e.target.value)}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-rose-500 dark:text-rose-400 mb-1">Improvement Recommendations</label>
                  <input
                    type="text"
                    className="w-full bg-white/45 dark:bg-slate-900/35 border border-slate-200/50 dark:border-slate-800/55 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-100"
                    value={repRecs}
                    onChange={(e) => setRepRecs(e.target.value)}
                  />
                </div>

                <div className="flex gap-2 justify-end mt-2 text-xs font-bold uppercase">
                  <button type="button" onClick={() => setActiveUnitId(null)} className="px-3 py-1.5 hover:bg-slate-500/10 text-slate-500 rounded-lg">Cancel</button>
                  <button type="submit" className="px-3.5 py-1.5 bg-rose-500 hover:bg-rose-600 text-white rounded-lg transition-all">Submit Report</button>
                </div>
              </form>
            )}

            {activeReportId && (
              <form onSubmit={uploadPdfReport} className="flex flex-col gap-4">
                <h3 className="font-extrabold text-base flex items-center gap-1.5 text-rose-500 border-b border-rose-500/10 pb-2">
                  <Upload className="w-5 h-5 animate-bounce" />
                  Upload PDF Validation Report (Report #{activeReportId})
                </h3>
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                  <input
                    type="file"
                    accept="application/pdf"
                    className="w-full max-w-xs text-xs file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-rose-500/10 file:text-rose-500 hover:file:bg-rose-500/20 text-slate-500 focus:outline-none"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setSelectedFile(e.target.files[0]);
                      }
                    }}
                    required
                  />
                  <button type="submit" className="bg-rose-500 hover:bg-rose-600 text-white font-bold py-2 px-4 rounded-xl text-xs uppercase tracking-wider flex items-center gap-1.5 disabled:opacity-50" disabled={loading}>
                    {loading && <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white/20 border-t-white"></div>}
                    Upload report.pdf
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Quality Controls and Validation reports desk */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
          <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-200 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-1.5">
            <ShieldCheck className="text-rose-500 w-5 h-5" />
            Quality Validation & Labs Desk
          </h3>

          <div className="overflow-x-auto mt-4">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-200/40 dark:border-slate-800/40">
                  <th className="pb-3.5 font-bold">Unit ID</th>
                  <th className="pb-3.5 font-bold">Group</th>
                  <th className="pb-3.5 font-bold">Volume</th>
                  <th className="pb-3.5 font-bold">Donor</th>
                  <th className="pb-3.5 font-bold">Vitals Status</th>
                  <th className="pb-3.5 font-bold text-right">Action Hub</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/50 dark:divide-slate-900/30 text-xs">
                {checkedUnits.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-slate-400 dark:text-slate-500 font-bold">
                      No checked-in units awaiting validation.
                    </td>
                  </tr>
                ) : (
                  checkedUnits.map(unit => (
                    <tr key={unit.id} className="hover:bg-slate-100/10 dark:hover:bg-slate-900/10 transition-colors">
                      <td className="py-4 font-bold text-slate-400">#{unit.id}</td>
                      <td className="py-4">
                        <span className="inline-block bg-slate-850 text-white font-extrabold text-xs px-2.5 py-0.5 rounded-lg border border-slate-700">{unit.blood_group}</span>
                      </td>
                      <td className="py-4 font-bold text-slate-700 dark:text-slate-300">{unit.volume_ml} ml</td>
                      <td className="py-4 font-bold text-slate-400">Donor #{unit.donor_id}</td>
                      <td className="py-4">
                        <span className={`inline-block px-2 py-0.5 rounded-lg text-[9px] font-bold uppercase ${
                          unit.is_safe 
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/10' 
                            : 'bg-rose-500/10 text-rose-600 dark:text-rose-405 border border-rose-500/10'
                        }`}>
                          {unit.is_safe ? 'Safe' : 'Unchecked'}
                        </span>
                      </td>
                      <td className="py-4 text-right">
                        <div className="flex gap-1.5 justify-end text-[10px] font-bold uppercase">
                          {/* Mark Safe/Quality checks */}
                          {!unit.is_safe && (
                            <button
                              onClick={() => validateQuality(unit.id, true)}
                              className="bg-emerald-550 hover:bg-emerald-600 text-white py-1 px-2.5 rounded-lg flex items-center gap-0.5 transition-all"
                              title="Mark Safe"
                            >
                              <Check className="w-3.5 h-3.5" />
                              Safe
                            </button>
                          )}

                          {/* Generate validation report details */}
                          {!unit.validation_report && (
                            <button
                              onClick={() => {
                                setActiveUnitId(unit.id);
                                setActiveReportId(null);
                              }}
                              className="bg-rose-500 hover:bg-rose-600 text-white py-1 px-2.5 rounded-lg transition-all"
                            >
                              Create Lab Report
                            </button>
                          )}

                          {/* Upload PDF triggers */}
                          {unit.validation_report && !unit.validation_report.report_pdf_path && (
                            <button
                              onClick={() => {
                                setActiveReportId(unit.validation_report!.id);
                                setActiveUnitId(null);
                              }}
                              className="bg-rose-500 hover:bg-rose-600 text-white py-1 px-2.5 rounded-lg transition-all"
                            >
                              Upload PDF
                            </button>
                          )}

                          {/* Completed status */}
                          {unit.validation_report && unit.validation_report.report_pdf_path && (
                            <span className="text-[10px] uppercase font-bold text-emerald-500 dark:text-emerald-400 flex items-center gap-0.5 py-1">
                              Verified ✔
                            </span>
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

        {/* Pending Mapped Donations Section */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
          <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-200 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-1.5">
            <Activity className="text-rose-500 w-5 h-5 animate-pulse" />
            Pending Mapped Donor Donations
          </h3>
          
          <div className="flex flex-col gap-3.5 mt-4">
            {assignedRequests.length === 0 ? (
              <div className="text-center py-4 text-xs text-slate-400 dark:text-slate-500 font-bold">
                No active donor appointments scheduled for your blood bank.
              </div>
            ) : (
              assignedRequests.map(req => (
                <div key={req.id} className="flex justify-between items-center p-4 border border-rose-500/15 bg-rose-500/5 rounded-2xl">
                  <div className="flex flex-col gap-0.5 leading-tight">
                    <span className="font-extrabold text-rose-500 text-sm">
                      🩸 {req.blood_group} Mapped Donation
                    </span>
                    <span className="text-xs text-slate-600 dark:text-slate-350 font-bold mt-1">
                      Donor: <strong className="text-slate-800 dark:text-slate-100">{req.assigned_donor?.user?.full_name || `Donor #${req.assigned_donor_id}`}</strong>
                    </span>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider mt-1">
                      Patient: {req.patient?.user?.full_name || 'Patient'} ({req.patient?.hospital_name})
                    </span>
                  </div>
                  <button
                    onClick={() => confirmDonation(req.id)}
                    className="bg-emerald-500 hover:bg-emerald-600 text-white font-extrabold rounded-xl py-2 px-4 shadow-md text-[10px] uppercase tracking-wider transition-all"
                    disabled={loading}
                  >
                    Confirm Donation
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Patient Request Claim Queue */}
        <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
          <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-200 border-b border-slate-200/50 dark:border-slate-800/50 pb-3 flex items-center gap-1.5">
            <Inbox className="text-rose-500 w-5 h-5" />
            Patient Request Claim Desk (100 Km Radius)
          </h3>
          
          <div className="flex flex-col gap-3.5 mt-4">
            {nearbyRequests.length === 0 ? (
              <div className="text-center py-4 text-xs text-slate-450 dark:text-slate-500 font-bold">
                No active pending patient requests in your dispatch zone.
              </div>
            ) : (
              nearbyRequests.map(req => (
                <div key={req.id} className="flex justify-between items-center p-4 border border-rose-500/15 bg-rose-500/5 rounded-2xl">
                  <div className="flex flex-col gap-0.5 leading-tight">
                    <span className="font-extrabold text-rose-500 text-sm">🩸 {req.blood_group} Needed</span>
                    <span className="text-xs text-slate-600 dark:text-slate-350 font-bold mt-1">
                      Hospital: {req.patient?.hospital_name || 'Mumbai Hospital'}
                    </span>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider mt-1">
                      Urgency: {req.urgency} | Units: {req.units_required}
                    </span>
                  </div>
                  <button
                    onClick={() => acceptPatientRequest(req.id)}
                    className="bg-rose-500 hover:bg-rose-600 text-white font-extrabold rounded-xl py-2 px-4 shadow-md text-[10px] uppercase tracking-wider transition-all"
                  >
                    Claim Request
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
};

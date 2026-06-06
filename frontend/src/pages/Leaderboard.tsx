import React, { useEffect, useState } from 'react';
import { Trophy, Medal, Award, Flame, Star, Sparkles } from 'lucide-react';
import api from '../services/api';
import { DonorProfile } from '../types';

export const Leaderboard: React.FC = () => {
  const [topDonors, setTopDonors] = useState<DonorProfile[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLeaderboard = async () => {
    try {
      const resp = await api.get<DonorProfile[]>('/donors/leaderboard', {
        params: { limit: 10 }
      });
      setTopDonors(resp.data);
    } catch (err) {
      console.error('Failed to fetch leaderboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const getRankBadge = (idx: number) => {
    switch (idx) {
      case 0: return <Trophy className="w-5 h-5 text-amber-500 fill-amber-500 animate-pulse" />;
      case 1: return <Medal className="w-5 h-5 text-slate-400 fill-slate-350" />;
      case 2: return <Medal className="w-5 h-5 text-amber-600 fill-amber-500" />;
      default: return <span className="font-extrabold text-xs text-slate-400 w-5 text-center">{idx + 1}</span>;
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      
      {/* Leaderboard Header */}
      <div className="glass-panel bg-gradient-to-r from-rose-500/10 to-pink-500/5 border border-rose-500/15 p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 translate-x-1/4 -translate-y-1/4 w-60 h-60 bg-rose-500/5 rounded-full blur-3xl"></div>
        <div className="flex items-center gap-4 relative z-10">
          <Trophy className="w-10 h-10 text-rose-500 fill-rose-500/10 animate-bounce" />
          <div>
            <h2 className="text-2xl font-black tracking-tight text-slate-800 dark:text-slate-100">RaktaSanchaar Hall of Fame</h2>
            <p className="text-xs font-bold text-slate-500 dark:text-slate-400 mt-1">
              Celebrating our top blood donors and local lifesavers
            </p>
          </div>
        </div>
      </div>

      {/* Leaderboard Table Card */}
      <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 p-6">
        {loading ? (
          <div className="flex flex-col items-center py-12 gap-2">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-rose-500/20 border-t-rose-500"></div>
            <p className="text-xs text-slate-400 dark:text-slate-500 font-bold">Loading leaderboard...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-200/40 dark:border-slate-800/40">
                  <th className="w-16 pb-3 text-center font-bold">Rank</th>
                  <th className="pb-3 font-bold">Donor ID</th>
                  <th className="pb-3 font-bold">Blood Group</th>
                  <th className="pb-3 font-bold">Completed Donations</th>
                  <th className="pb-3 font-bold">Reliability Rating</th>
                  <th className="pb-3 font-bold text-right">Badges</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/50 dark:divide-slate-900/30 text-xs">
                {topDonors.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-slate-400 dark:text-slate-500 font-bold">
                      No entries on the leaderboard yet.
                    </td>
                  </tr>
                ) : (
                  topDonors.map((donor, idx) => (
                    <tr key={donor.id} className="hover:bg-slate-100/10 dark:hover:bg-slate-900/10 transition-colors">
                      <td className="py-4 flex justify-center items-center">
                        {getRankBadge(idx)}
                      </td>
                      <td className="py-4 font-bold text-slate-700 dark:text-slate-200">
                        Donor #{donor.id}
                      </td>
                      <td className="py-4">
                        <span className="inline-block bg-slate-800 text-white font-extrabold text-xs px-2.5 py-0.5 rounded-lg border border-slate-700">{donor.blood_group}</span>
                      </td>
                      <td className="py-4 font-bold text-slate-700 dark:text-slate-300">
                        <div className="flex items-center gap-1">
                          <Flame className="w-4 h-4 text-rose-500 fill-rose-500/10" />
                          <span>{donor.total_donations}</span>
                        </div>
                      </td>
                      <td className="py-4">
                        <div className="flex items-center gap-1 font-bold">
                          <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                          <span>{(donor.reliability_score * 5).toFixed(1)}</span>
                        </div>
                      </td>
                      <td className="py-4 text-right">
                        <div className="flex gap-1.5 justify-end text-[9px] font-bold uppercase">
                          {donor.total_donations >= 1 && (
                            <span className="inline-block bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/10 px-2 py-0.5 rounded-md" title="First Donation Completed">
                              🏅 Seeder
                            </span>
                          )}
                          {donor.total_donations >= 5 && (
                            <span className="inline-block bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/10 px-2 py-0.5 rounded-md" title="5+ Donations completed">
                              🏆 Hero
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
        )}
      </div>

    </div>
  );
};

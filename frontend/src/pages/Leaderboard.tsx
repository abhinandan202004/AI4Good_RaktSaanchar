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
      case 0: return <Trophy className="w-5 h-5 text-amber-500 fill-amber-500/20 animate-pulse" />;
      case 1: return <Medal className="w-5 h-5 text-slate-400 fill-slate-300/20" />;
      case 2: return <Medal className="w-5 h-5 text-amber-600 fill-amber-600/20" />;
      default: return <span className="font-extrabold text-xs text-slate-400 w-5 text-center">{idx + 1}</span>;
    }
  };

  // Extract top 3 for podium display
  const podiumDonors = topDonors.slice(0, 3);
  const remainingDonors = topDonors.slice(3);

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6 p-6">
      
      {/* Leaderboard Header */}
      <div className="glass-panel bg-gradient-to-r from-brand-light/30 to-[#ffffff]/10 border border-brand-default/40 p-8 relative overflow-hidden dark:from-brand-dark/15 dark:to-transparent">
        <div className="absolute top-0 right-0 translate-x-1/4 -translate-y-1/4 w-60 h-60 bg-brand-default/10 rounded-full blur-3xl"></div>
        <div className="flex items-center gap-4 relative z-10">
          <Trophy className="w-10 h-10 text-brand-dark dark:text-brand-default animate-bounce" />
          <div>
            <h2 className="text-2xl font-black tracking-tight text-brand-dark dark:text-slate-100">Hall of Fame</h2>
            <p className="text-xs font-bold text-slate-500 dark:text-slate-405 mt-1">
              Celebrating our top blood donors and local lifesavers
            </p>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="glass-panel p-12 flex flex-col items-center gap-2">
          <div className="animate-spin rounded-full h-8 w-8 border-4 border-brand-default/20 border-t-brand-dark dark:border-t-brand-default"></div>
          <p className="text-xs text-slate-400 dark:text-slate-500 font-bold">Loading leaderboard...</p>
        </div>
      ) : (
        <>
          {/* Podium Display for Top 3 */}
          {podiumDonors.length > 0 && (
            <div className="grid grid-cols-3 gap-4 items-end pt-8 pb-4">
              
              {/* Rank 2 */}
              {podiumDonors[1] && (
                <div className="flex flex-col items-center gap-2 order-1">
                  <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-300/50 flex items-center justify-center font-bold text-slate-500 shadow-sm text-xs">
                    Donor #{podiumDonors[1].id}
                  </div>
                  <div className="h-24 bg-slate-100/70 border-t border-x border-slate-200 w-full rounded-t-2xl shadow-inner flex flex-col justify-center items-center gap-1 p-2 dark:bg-brand-darkCard dark:border-slate-800">
                    <Medal className="w-6 h-6 text-slate-400 fill-slate-300/20" />
                    <span className="text-[10px] font-black text-slate-400">2ND PLACE</span>
                    <span className="text-xs font-extrabold text-brand-dark dark:text-brand-light">{podiumDonors[1].points || 0} pts</span>
                  </div>
                </div>
              )}

              {/* Rank 1 */}
              {podiumDonors[0] && (
                <div className="flex flex-col items-center gap-2 order-2 scale-[1.08] z-10">
                  <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-300 flex items-center justify-center font-black text-amber-700 shadow-md text-sm dark:bg-brand-dark dark:border-amber-500/40 dark:text-amber-400">
                    Donor #{podiumDonors[0].id}
                  </div>
                  <div className="h-32 bg-amber-50 border-t-2 border-x border-amber-200 w-full rounded-t-2xl shadow-md flex flex-col justify-center items-center gap-1.5 p-3 dark:bg-brand-dark/20 dark:border-amber-500/20">
                    <Trophy className="w-7 h-7 text-amber-500 fill-amber-500/15 animate-pulse" />
                    <span className="text-[10px] font-black text-amber-600 dark:text-amber-400">CHAMPION</span>
                    <span className="text-sm font-black text-brand-dark dark:text-amber-400">{podiumDonors[0].points || 0} pts</span>
                  </div>
                </div>
              )}

              {/* Rank 3 */}
              {podiumDonors[2] && (
                <div className="flex flex-col items-center gap-2 order-3">
                  <div className="w-10 h-10 rounded-full bg-amber-100/50 border border-amber-300/30 flex items-center justify-center font-bold text-amber-700/80 shadow-sm text-xs dark:bg-brand-dark/50">
                    Donor #{podiumDonors[2].id}
                  </div>
                  <div className="h-20 bg-amber-100/30 border-t border-x border-amber-200/50 w-full rounded-t-2xl shadow-inner flex flex-col justify-center items-center gap-1 p-2 dark:bg-brand-darkCard dark:border-slate-800">
                    <Medal className="w-6 h-6 text-amber-600 fill-amber-600/10" />
                    <span className="text-[10px] font-black text-amber-600/70 dark:text-amber-500/70">3RD PLACE</span>
                    <span className="text-xs font-extrabold text-brand-dark dark:text-brand-light">{podiumDonors[2].points || 0} pts</span>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* Leaderboard Table Card */}
          <div className="glass-panel p-6">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-brand-default/20 dark:border-brand-dark/20">
                    <th className="w-16 pb-3 text-center font-bold">Rank</th>
                    <th className="pb-3 font-bold">Donor ID</th>
                    <th className="pb-3 font-bold">Blood Group</th>
                    <th className="pb-3 font-bold">Completed Donations</th>
                    <th className="pb-3 font-bold">Reliability Rating</th>
                    <th className="pb-3 font-bold text-right">Badges</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#C7E5F4]/10 dark:divide-slate-800/20 text-xs">
                  {topDonors.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-450 dark:text-slate-500 font-semibold">
                        No entries on the leaderboard yet.
                      </td>
                    </tr>
                  ) : (
                    topDonors.map((donor, idx) => (
                      <tr key={donor.id} className="hover:bg-slate-100/10 dark:hover:bg-slate-900/10 transition-colors">
                        <td className="py-4 flex justify-center items-center">
                          {getRankBadge(idx)}
                        </td>
                        <td className="py-4 font-bold text-brand-dark dark:text-slate-200">
                          Donor #{donor.id}
                        </td>
                        <td className="py-4">
                          <span className="inline-block bg-brand-dark text-white font-extrabold text-xs px-2.5 py-0.5 rounded-lg border border-transparent dark:bg-brand-default dark:text-brand-dark">{donor.blood_group}</span>
                        </td>
                        <td className="py-4 font-bold text-brand-dark dark:text-slate-300">
                          <div className="flex items-center gap-1">
                            <Flame className="w-4 h-4 text-[#FF5E5E]" />
                            <span>{donor.total_donations}</span>
                          </div>
                        </td>
                        <td className="py-4">
                          <div className="flex items-center gap-1 font-bold text-brand-dark dark:text-brand-light">
                            <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                            <span>{(donor.reliability_score * 5).toFixed(1)}</span>
                          </div>
                        </td>
                        <td className="py-4 text-right">
                          <div className="flex gap-1.5 justify-end text-[9px] font-bold uppercase">
                            {donor.total_donations >= 1 && (
                              <span className="inline-block bg-emerald-500/10 text-emerald-600 dark:text-emerald-450 border border-emerald-550/10 px-2 py-0.5 rounded-md" title="First Donation Completed">
                                🏅 Seeder
                              </span>
                            )}
                            {donor.total_donations >= 5 && (
                              <span className="inline-block bg-amber-550/10 text-amber-600 dark:text-amber-450 border border-amber-500/10 px-2 py-0.5 rounded-md" title="5+ Donations completed">
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
          </div>
        </>
      )}

    </div>
  );
};
export default Leaderboard;

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Layers,
  Database,
  GitMerge,
  AlertTriangle,
  ShieldCheck,
  Clock,
  PlayCircle,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import { api } from '../services/api';
import { DashboardSummary, PipelineRun } from '../types';
import { KpiCard } from '../components/common/KpiCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { KpiCardSkeleton, TableSkeleton } from '../components/common/SkeletonLoader';
import { ErrorState } from '../components/common/EmptyState';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

export const OverviewPage: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentRuns, setRecentRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumData, runsData] = await Promise.all([
        api.getDashboardSummary(),
        api.listRuns({ page: 1, page_size: 6 }),
      ]);
      setSummary(sumData);
      setRecentRuns(runsData.items);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to backend service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <KpiCardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton rows={6} />
      </div>
    );
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  // Outcome distribution data for Recharts
  const outcomeData = [
    { name: 'Exact Merges', value: summary?.exact_merges || 0, color: '#06B6D4' },
    { name: 'Probable Merges', value: summary?.probable_merges || 0, color: '#8B5CF6' },
    { name: 'Review Items', value: summary?.manual_reviews_pending || 0, color: '#F59E0B' },
    { name: 'Quarantined', value: summary?.quarantined_records || 0, color: '#EF4444' },
  ];

  // Entity distribution data
  const entityData = Object.entries(summary?.runs_by_entity || {}).map(([key, count]) => ({
    name: key,
    runs: count,
  }));

  // Rejection code distribution
  const rejectionData = Object.entries(summary?.rejection_distribution || {}).map(([key, count]) => ({
    code: key.replace(/_/g, ' '),
    count,
  }));

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner / Callout */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-[#0F1C31] via-[#111B2D] to-[#14182E] border border-[#1C283F] flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              DATAFORGE ENGINE ACTIVE
            </span>
            <span className="text-xs text-slate-400">• SQLite WAL Persistence</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Master Data Quality & Entity Resolution
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Real-time deduplication with hard-conflict vetoes, multi-attribute RapidFuzz corroboration, and deterministic UUIDv5 survivorship.
          </p>
        </div>
        <Link
          to="/runs"
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-400 text-slate-950 font-semibold text-xs hover:opacity-90 transition-all shadow-glow whitespace-nowrap"
        >
          <PlayCircle className="w-4 h-4" />
          <span>Launch Pipeline Run</span>
        </Link>
      </div>

      {/* 6 Core KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          title="Total Processed"
          value={summary?.total_records_processed?.toLocaleString() || '0'}
          subtitle="Cumulative input rows"
          icon={Database}
          variant="cyan"
        />
        <KpiCard
          title="Golden Masters"
          value={summary?.golden_masters_created?.toLocaleString() || '0'}
          subtitle="Consolidated identities"
          icon={Layers}
          variant="violet"
        />
        <KpiCard
          title="Exact Merges"
          value={summary?.exact_merges?.toLocaleString() || '0'}
          subtitle="Tax ID, UPC & SKU links"
          icon={GitMerge}
          variant="emerald"
        />
        <KpiCard
          title="Probable Merges"
          value={summary?.probable_merges?.toLocaleString() || '0'}
          subtitle="Fuzzy & corroborated"
          icon={TrendingUp}
          variant="cyan"
        />
        <KpiCard
          title="Manual Review"
          value={summary?.manual_reviews_pending?.toLocaleString() || '0'}
          subtitle="Flagged candidate pairs"
          icon={AlertTriangle}
          variant="amber"
          badge={summary?.manual_reviews_pending ? 'Needs Attention' : undefined}
        />
        <KpiCard
          title="Quarantined"
          value={summary?.quarantined_records?.toLocaleString() || '0'}
          subtitle="Schema & type errors"
          icon={ShieldCheck}
          variant="rose"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart 1: Outcomes Breakdown */}
        <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl p-5 shadow-card flex flex-col">
          <h3 className="text-sm font-semibold text-white mb-1">Deduplication Outcomes</h3>
          <p className="text-xs text-slate-400 mb-4">Breakdown of merges, review queues, and quarantine</p>
          <div className="h-60 w-full flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={outcomeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {outcomeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0D1423', borderColor: '#1C283F', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#F8FAFC' }}
                />
                <Legend
                  formatter={(val) => <span className="text-xs text-slate-300">{val}</span>}
                  iconSize={8}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Rejections by Code */}
        <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl p-5 shadow-card flex flex-col">
          <h3 className="text-sm font-semibold text-white mb-1">Quarantine Reasons</h3>
          <p className="text-xs text-slate-400 mb-4">Distribution of data quality failure codes</p>
          <div className="h-60 w-full flex-1">
            {rejectionData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No quarantined records recorded
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rejectionData} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1C283F" horizontal={false} />
                  <XAxis type="number" stroke="#64748B" fontSize={10} tickLine={false} />
                  <YAxis type="category" dataKey="code" stroke="#64748B" fontSize={9} tickLine={false} width={80} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0D1423', borderColor: '#1C283F', borderRadius: '8px', fontSize: '12px' }}
                    itemStyle={{ color: '#F8FAFC' }}
                  />
                  <Bar dataKey="count" fill="#F43F5E" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 3: Entity Runs Breakdown */}
        <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl p-5 shadow-card flex flex-col">
          <h3 className="text-sm font-semibold text-white mb-1">Execution Volume by Domain</h3>
          <p className="text-xs text-slate-400 mb-4">Customer vs. Product pipeline executions</p>
          <div className="h-60 w-full flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={entityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1C283F" vertical={false} />
                <XAxis dataKey="name" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0D1423', borderColor: '#1C283F', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#F8FAFC' }}
                />
                <Bar dataKey="runs" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Pipeline Activity Table */}
      <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl overflow-hidden shadow-card">
        <div className="p-5 border-b border-[#1C283F] flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent Pipeline Executions</h3>
            <p className="text-xs text-slate-400 mt-0.5">Audit log of recent batch deduplication runs</p>
          </div>
          <Link
            to="/runs"
            className="flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <span>View All Runs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0D1423] text-slate-400 uppercase tracking-wider text-[10px] border-b border-[#1C283F]">
              <tr>
                <th className="px-5 py-3">Run ID</th>
                <th className="px-5 py-3">Entity Domain</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Input Rows</th>
                <th className="px-5 py-3">Exact Merges</th>
                <th className="px-5 py-3">Review Items</th>
                <th className="px-5 py-3">Duration</th>
                <th className="px-5 py-3 text-right">Started At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1C283F] text-slate-300">
              {recentRuns.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-slate-400">
                    No pipeline runs recorded in the database yet.
                  </td>
                </tr>
              ) : (
                recentRuns.map((run) => (
                  <tr key={run.run_id} className="hover:bg-[#16233B]/50 transition-colors">
                    <td className="px-5 py-3.5 font-mono text-cyan-300 font-medium">
                      {run.run_id}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="font-semibold text-white">{run.entity_type}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={run.status} size="sm" />
                    </td>
                    <td className="px-5 py-3.5 font-mono">{run.input_count.toLocaleString()}</td>
                    <td className="px-5 py-3.5 font-mono text-emerald-400">
                      {run.exact_match_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-amber-400">
                      {run.review_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-slate-400">
                      {run.elapsed_seconds ? `${run.elapsed_seconds.toFixed(2)}s` : '—'}
                    </td>
                    <td className="px-5 py-3.5 text-right font-mono text-slate-400">
                      {new Date(run.started_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};


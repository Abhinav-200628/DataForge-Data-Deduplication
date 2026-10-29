import React, { useEffect, useState } from 'react';
import {
  FileText,
  RotateCw,
  Download,
  CheckCircle,
  AlertTriangle,
  Award,
  Layers,
  BarChart3,
  Cpu,
} from 'lucide-react';
import { api } from '../services/api';
import { PipelineRun } from '../types';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import { ErrorState, EmptyState } from '../components/common/EmptyState';

export const ReportsPage: React.FC = () => {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load runs list
  useEffect(() => {
    setLoading(true);
    api
      .listRuns({ page: 1, page_size: 50 })
      .then((data) => {
        setRuns(data.items);
        if (data.items.length > 0) {
          setSelectedRunId(data.items[0].run_id);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Load selected report
  useEffect(() => {
    if (!selectedRunId) return;
    setReportLoading(true);
    api
      .getRunReport(selectedRunId)
      .then((data) => setReportData(data))
      .catch((err) => setReportData({ error: err.message }))
      .finally(() => setReportLoading(false));
  }, [selectedRunId]);

  const downloadJson = () => {
    if (!reportData) return;
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reconciliation_report_${selectedRunId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <TableSkeleton rows={6} />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  const recon = reportData?.reconciliation;
  const dedup = reportData?.deduplication_metrics;
  const gt = reportData?.ground_truth_evaluation;
  const info = reportData?.run_info;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header & Run Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
              <FileText className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Audit & Reconciliation Reports
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Mathematical conservation audits, deduplication ratios, and ground-truth precision/recall.
          </p>
        </div>

        {/* Run Selector & Download */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <select
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
            className="px-3.5 py-2 rounded-xl bg-[#111B2D] border border-[#1C283F] text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500/40"
          >
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id} ({r.entity_type} • {r.status})
              </option>
            ))}
          </select>

          {reportData && !reportData.error && (
            <button
              onClick={downloadJson}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#111B2D] border border-[#1C283F] text-slate-300 hover:text-white hover:border-cyan-500/40 text-xs font-semibold transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-cyan-400" />
              <span>Export JSON</span>
            </button>
          )}
        </div>
      </div>

      {reportLoading ? (
        <TableSkeleton rows={6} />
      ) : reportData?.error ? (
        <ErrorState message={reportData.error} />
      ) : !reportData ? (
        <EmptyState title="No report available" description="Select a run to view its audit report." />
      ) : (
        <div className="space-y-6">
          {/* Section 1: Reconciliation Conservation Balance */}
          <div className="p-6 rounded-2xl bg-[#111B2D] border border-[#1C283F] shadow-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">
                  Mathematical Reconciliation Conservation Check
                </h3>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-mono font-bold border ${
                  recon?.is_balanced
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                    : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
                }`}
              >
                {recon?.is_balanced ? 'CONSERVATION BALANCED: PASSED' : 'CONSERVATION VIOLATION'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono mb-4">
              <div className="p-4 rounded-xl bg-[#0D1423] border border-[#1C283F]">
                <span className="text-slate-400 block text-[10px] uppercase">Total Input Rows</span>
                <span className="text-xl font-bold text-white mt-1 block">
                  {recon?.input_count?.toLocaleString()}
                </span>
              </div>
              <div className="p-4 rounded-xl bg-[#0D1423] border border-[#1C283F]">
                <span className="text-slate-400 block text-[10px] uppercase">Valid Records Resolved</span>
                <span className="text-xl font-bold text-cyan-400 mt-1 block">
                  {recon?.valid_count?.toLocaleString()}
                </span>
              </div>
              <div className="p-4 rounded-xl bg-[#0D1423] border border-[#1C283F]">
                <span className="text-slate-400 block text-[10px] uppercase">Quarantined Records</span>
                <span className="text-xl font-bold text-rose-400 mt-1 block">
                  {recon?.quarantined_count?.toLocaleString()}
                </span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-[#0D1423] border border-[#1C283F] font-mono text-xs text-slate-300 text-center">
              Conservation Law: <span className="text-cyan-400 font-bold">{recon?.formula}</span>
            </div>
          </div>

          {/* Section 2: Deduplication Consolidation Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="p-6 rounded-2xl bg-[#111B2D] border border-[#1C283F] shadow-card">
              <h3 className="text-sm font-bold text-white mb-1">Entity Consolidation Metrics</h3>
              <p className="text-xs text-slate-400 mb-4">Golden master generation and compression efficiency</p>

              <div className="grid grid-cols-2 gap-3 text-xs mb-4">
                <div className="p-3 rounded-xl bg-[#0D1423] border border-[#1C283F]">
                  <span className="text-[10px] text-slate-400 block">Golden Masters Created</span>
                  <span className="text-lg font-mono font-bold text-white mt-0.5 block">
                    {dedup?.golden_master_records?.toLocaleString()}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-[#0D1423] border border-[#1C283F]">
                  <span className="text-[10px] text-slate-400 block">Deduplication Ratio</span>
                  <span className="text-lg font-mono font-bold text-emerald-400 mt-0.5 block">
                    {dedup?.deduplication_ratio_pct}%
                  </span>
                </div>
              </div>

              <h4 className="text-xs font-semibold text-slate-300 mb-2">Rule Attribution</h4>
              <div className="space-y-1.5 text-xs font-mono">
                {dedup?.rule_breakdown?.map((rb: any, i: number) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg bg-[#0D1423] border border-[#1C283F] flex justify-between items-center"
                  >
                    <div>
                      <span className="text-cyan-400 font-bold">{rb.decision}</span>
                      <span className="text-slate-400 text-[11px] block">{rb.rule_id}</span>
                    </div>
                    <span className="font-bold text-white">{rb.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 3: Ground-Truth Precision & Recall Evaluation */}
            <div className="p-6 rounded-2xl bg-[#111B2D] border border-[#1C283F] shadow-card flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Award className="w-5 h-5 text-amber-400" />
                  <h3 className="text-sm font-bold text-white">
                    Ground-Truth Benchmark Evaluation
                  </h3>
                </div>
                <p className="text-xs text-slate-400 mb-4">
                  Accuracy evaluated against isolated ground-truth labels (if supplied)
                </p>

                {gt ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-3 text-center text-xs font-mono">
                      <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                        <span className="text-[10px] text-slate-400 block">Precision</span>
                        <span className="text-lg font-bold text-cyan-300 mt-0.5 block">
                          {(gt.precision * 100).toFixed(2)}%
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-violet-500/10 border border-violet-500/20">
                        <span className="text-[10px] text-slate-400 block">Recall</span>
                        <span className="text-lg font-bold text-violet-300 mt-0.5 block">
                          {(gt.recall * 100).toFixed(2)}%
                        </span>
                      </div>
                      <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                        <span className="text-[10px] text-slate-400 block">F1 Score</span>
                        <span className="text-lg font-bold text-emerald-300 mt-0.5 block">
                          {gt.f1_score.toFixed(4)}
                        </span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-[#0D1423] border border-[#1C283F] space-y-1 text-xs">
                      <div className="flex justify-between text-slate-300">
                        <span>True Positives (Correct Merges):</span>
                        <span className="font-mono font-bold text-emerald-400">{gt.true_positives}</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span>False Positives (Over-merges):</span>
                        <span className="font-mono font-bold text-rose-400">{gt.false_positives}</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span>False Negatives (Missed Merges):</span>
                        <span className="font-mono font-bold text-amber-400">{gt.false_negatives}</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-xs text-slate-400 bg-[#0D1423] rounded-xl border border-[#1C283F] border-dashed">
                    No ground-truth dataset was configured for this run. Ground-truth evaluation is available for synthetic benchmark runs.
                  </div>
                )}
              </div>

              {/* Hardware / Environment Specs */}
              <div className="mt-4 pt-4 border-t border-[#1C283F] text-[11px] text-slate-400 flex items-center justify-between font-mono">
                <span>Run Status: {info?.status || 'COMPLETED'}</span>
                <span>Elapsed: {info?.elapsed_seconds ? `${info.elapsed_seconds.toFixed(2)}s` : '—'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


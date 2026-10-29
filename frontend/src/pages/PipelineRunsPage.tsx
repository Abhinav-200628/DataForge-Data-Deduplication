import React, { useEffect, useState } from 'react';
import {
  Play,
  RotateCw,
  Search,
  CheckCircle,
  AlertCircle,
  FileCheck,
  Clock,
  Filter,
  Layers,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { AvailableFile, PipelineRun } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { Pagination } from '../components/common/Pagination';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import { ErrorState, EmptyState } from '../components/common/EmptyState';

export const PipelineRunsPage: React.FC = () => {
  // Launch state
  const [selectedEntity, setSelectedEntity] = useState<'customer' | 'product'>('customer');
  const [selectedFile, setSelectedFile] = useState<string>('data/sample/customers_500.csv');
  const [availableFiles, setAvailableFiles] = useState<AvailableFile[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [launchMessage, setLaunchMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Table state
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [totalRuns, setTotalRuns] = useState(0);
  const [page, setPage] = useState(1);
  const [entityFilter, setEntityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load available files for dropdown
  useEffect(() => {
    api
      .listAvailableFiles()
      .then((data) => {
        setAvailableFiles(data.files);
        // Default to suitable sample
        const defaultF = data.files.find((f) =>
          selectedEntity === 'customer' ? f.filename.includes('customer') : f.filename.includes('product')
        );
        if (defaultF) setSelectedFile(defaultF.path);
      })
      .catch(() => {});
  }, [selectedEntity]);

  const loadRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listRuns({
        entity_type: entityFilter || undefined,
        status: statusFilter || undefined,
        page,
        page_size: 10,
      });
      setRuns(data.items);
      setTotalRuns(data.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load pipeline runs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [page, entityFilter, statusFilter]);

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsSubmitting(true);
    setLaunchMessage(null);

    try {
      const res = await api.triggerRun({
        entity_type: selectedEntity,
        input_file: selectedFile,
      });
      setLaunchMessage({
        type: 'success',
        text: `Run ${res.run_id} finished successfully: ${res.message}`,
      });
      loadRuns();
    } catch (err: any) {
      setLaunchMessage({
        type: 'error',
        text: err.message || 'Pipeline execution failed.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Execution Launcher Panel */}
      <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl p-6 shadow-card">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400">
            <Play className="w-5 h-5 fill-current" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Execute Deduplication Pipeline</h2>
            <p className="text-xs text-slate-400">
              Run full entity resolution lifecycle on an input CSV batch with atomic SQLite persistence.
            </p>
          </div>
        </div>

        <form onSubmit={handleLaunch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Entity Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Target Entity Domain
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedEntity('customer');
                    const match = availableFiles.find((f) => f.filename.includes('customer'));
                    if (match) setSelectedFile(match.path);
                  }}
                  className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all ${
                    selectedEntity === 'customer'
                      ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-300 shadow-sm'
                      : 'bg-[#0D1423] border-[#1C283F] text-slate-400 hover:text-white'
                  }`}
                >
                  Customer
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedEntity('product');
                    const match = availableFiles.find((f) => f.filename.includes('product'));
                    if (match) setSelectedFile(match.path);
                  }}
                  className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all ${
                    selectedEntity === 'product'
                      ? 'bg-violet-500/15 border-violet-500/40 text-violet-300 shadow-sm'
                      : 'bg-[#0D1423] border-[#1C283F] text-slate-400 hover:text-white'
                  }`}
                >
                  Product
                </button>
              </div>
            </div>

            {/* Input File Selector */}
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Input Batch File (CSV)
              </label>
              <select
                value={selectedFile}
                onChange={(e) => setSelectedFile(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#0D1423] border border-[#1C283F] text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 font-mono"
              >
                {availableFiles.map((f) => (
                  <option key={f.path} value={f.path}>
                    {f.filename} ({f.entity_hint.toUpperCase()}) — {(f.size_bytes / 1024).toFixed(1)} KB
                  </option>
                ))}
              </select>
            </div>
          </div>

          {launchMessage && (
            <div
              className={`p-3.5 rounded-xl border text-xs flex items-center gap-2 ${
                launchMessage.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
              }`}
            >
              {launchMessage.type === 'success' ? (
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              )}
              <span>{launchMessage.text}</span>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isSubmitting || !selectedFile}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-400 text-slate-950 font-bold text-xs hover:opacity-90 transition-all shadow-glow disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Processing Deduplication Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Run {selectedEntity.toUpperCase()} Pipeline</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* History & Table View */}
      <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl overflow-hidden shadow-card">
        {/* Filters Bar */}
        <div className="p-4 border-b border-[#1C283F] flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#0D1423]/60">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-semibold text-slate-300">Filter Execution Logs</span>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            {/* Entity Filter */}
            <select
              value={entityFilter}
              onChange={(e) => {
                setEntityFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-lg bg-[#111B2D] border border-[#1C283F] text-xs text-slate-300 focus:outline-none focus:border-cyan-500/40"
            >
              <option value="">All Domains</option>
              <option value="CUSTOMER">Customer</option>
              <option value="PRODUCT">Product</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-lg bg-[#111B2D] border border-[#1C283F] text-xs text-slate-300 focus:outline-none focus:border-cyan-500/40"
            >
              <option value="">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="RUNNING">Running</option>
              <option value="FAILED">Failed</option>
            </select>

            <button
              onClick={loadRuns}
              className="p-2 rounded-lg bg-[#111B2D] border border-[#1C283F] text-slate-300 hover:text-white hover:border-cyan-500/40"
              title="Refresh Runs"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Runs Table */}
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={5} />
          </div>
        ) : error ? (
          <div className="p-6">
            <ErrorState message={error} onRetry={loadRuns} />
          </div>
        ) : runs.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No pipeline executions found"
              description="No runs matched your filters, or no pipelines have been triggered yet."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0D1423] text-slate-400 uppercase tracking-wider text-[10px] border-b border-[#1C283F]">
                <tr>
                  <th className="px-5 py-3">Run ID</th>
                  <th className="px-5 py-3">Domain</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Input</th>
                  <th className="px-5 py-3">Valid</th>
                  <th className="px-5 py-3">Quarantined</th>
                  <th className="px-5 py-3">Exact Merges</th>
                  <th className="px-5 py-3">Review Items</th>
                  <th className="px-5 py-3">Duration</th>
                  <th className="px-5 py-3 text-right">Started At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C283F] text-slate-300">
                {runs.map((r) => (
                  <tr key={r.run_id} className="hover:bg-[#16233B]/50 transition-colors">
                    <td className="px-5 py-3.5 font-mono text-cyan-300 font-medium">
                      {r.run_id}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="font-semibold text-white">{r.entity_type}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={r.status} size="sm" />
                    </td>
                    <td className="px-5 py-3.5 font-mono">{r.input_count.toLocaleString()}</td>
                    <td className="px-5 py-3.5 font-mono text-slate-200">
                      {r.valid_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-rose-400">
                      {r.quarantined_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-emerald-400">
                      {r.exact_match_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-amber-400">
                      {r.review_count.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-slate-400">
                      {r.elapsed_seconds ? `${r.elapsed_seconds.toFixed(2)}s` : '—'}
                    </td>
                    <td className="px-5 py-3.5 text-right font-mono text-slate-400">
                      {new Date(r.started_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalRuns > 0 && (
          <Pagination
            currentPage={page}
            totalItems={totalRuns}
            pageSize={10}
            onPageChange={(p) => setPage(p)}
          />
        )}
      </div>
    </div>
  );
};


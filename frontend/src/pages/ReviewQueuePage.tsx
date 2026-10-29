import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  RotateCw,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  ArrowRight,
  Gavel,
} from 'lucide-react';
import { api } from '../services/api';
import { ReviewItem } from '../types';
import { StatusBadge } from '../components/common/StatusBadge';
import { Pagination } from '../components/common/Pagination';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import { ErrorState, EmptyState } from '../components/common/EmptyState';
import { ReviewActionModal } from '../components/review/ReviewActionModal';

export const ReviewQueuePage: React.FC = () => {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [entityFilter, setEntityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('PENDING');
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Triage modal state
  const [selectedReviewItem, setSelectedReviewItem] = useState<ReviewItem | null>(null);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  const loadReviewQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listReviewQueue({
        entity_type: entityFilter || undefined,
        status: statusFilter || undefined,
        search: debouncedSearch || undefined,
        page,
        page_size: 10,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load review queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReviewQueue();
  }, [page, entityFilter, statusFilter, debouncedSearch]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Human-in-the-Loop Review Queue
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Ambiguous matches, shared family contact channels, and records vetoed by hard-conflict safeguards.
          </p>
        </div>

        {/* Search */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search source ID, system, reasons..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#111B2D] border border-[#1C283F] text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-amber-500/40"
            />
          </div>
          <button
            onClick={loadReviewQueue}
            className="p-2 rounded-xl border border-[#1C283F] bg-[#111B2D] text-slate-300 hover:text-white hover:border-amber-500/40 transition-colors"
            title="Refresh Review Queue"
          >
            <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin text-amber-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Review Workspace */}
      <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl overflow-hidden shadow-card">
        {/* Filters */}
        <div className="p-4 border-b border-[#1C283F] flex flex-wrap items-center justify-between gap-3 bg-[#0D1423]/60">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-semibold text-slate-300">Queue Triage Filters</span>
          </div>

          <div className="flex items-center gap-2">
            {/* Status Tabs */}
            <div className="flex rounded-lg bg-[#111B2D] p-1 border border-[#1C283F]">
              {['PENDING', 'APPROVED', 'REJECTED', ''].map((st) => (
                <button
                  key={st}
                  onClick={() => {
                    setStatusFilter(st);
                    setPage(1);
                  }}
                  className={`px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
                    statusFilter === st
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {st || 'ALL'}
                </button>
              ))}
            </div>

            {/* Entity Filter */}
            <select
              value={entityFilter}
              onChange={(e) => {
                setEntityFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 rounded-lg bg-[#111B2D] border border-[#1C283F] text-xs text-slate-300 focus:outline-none focus:border-amber-500/40"
            >
              <option value="">All Domains</option>
              <option value="CUSTOMER">Customer</option>
              <option value="PRODUCT">Product</option>
            </select>
          </div>
        </div>

        {/* Content list */}
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={5} />
          </div>
        ) : error ? (
          <div className="p-6">
            <ErrorState message={error} onRetry={loadReviewQueue} />
          </div>
        ) : items.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="Review queue is clear"
              description="No ambiguous matches or conflict flags are currently pending review."
            />
          </div>
        ) : (
          <div className="divide-y divide-[#1C283F]">
            {items.map((item) => {
              const hasConflict = item.reasons.some(
                (r) => r.toLowerCase().includes('hard conflict') || r.toLowerCase().includes('conflicting')
              );

              return (
                <div
                  key={item.review_id}
                  className="p-5 hover:bg-[#16233B]/40 transition-colors flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 text-xs"
                >
                  {/* Left: Review Info */}
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-cyan-400 font-bold text-[11px]">
                        {item.review_id}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 text-[10px] font-mono font-semibold">
                        {item.entity_type}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono">
                        {item.source_system} : {item.source_record_id}
                      </span>
                      <StatusBadge status={item.status} size="sm" />
                    </div>

                    {/* Reasons List */}
                    <div className="pt-1">
                      {item.reasons.map((r, i) => (
                        <div
                          key={i}
                          className={`flex items-start gap-1.5 text-xs ${
                            r.toLowerCase().includes('conflict')
                              ? 'text-rose-300 font-medium'
                              : 'text-slate-300'
                          }`}
                        >
                          <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-amber-400" />
                          <span>{r}</span>
                        </div>
                      ))}
                    </div>

                    <div className="text-[10px] text-slate-400 font-mono">
                      Queued: {new Date(item.created_at).toLocaleString()}
                    </div>
                  </div>

                  {/* Right: Similarity Score & Triage Button */}
                  <div className="flex items-center gap-4 flex-shrink-0 self-end lg:self-center">
                    {item.similarity_score !== null && (
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 block font-mono uppercase">
                          Similarity
                        </span>
                        <span className="text-base font-bold font-mono text-amber-400">
                          {(item.similarity_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}

                    <button
                      onClick={() => setSelectedReviewItem(item)}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#0D1423] border border-[#1C283F] text-slate-200 hover:text-white hover:border-amber-500/50 hover:bg-[#111B2D] transition-all font-semibold"
                    >
                      <Gavel className="w-3.5 h-3.5 text-amber-400" />
                      <span>Triage Item</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {total > 0 && (
          <Pagination
            currentPage={page}
            totalItems={total}
            pageSize={10}
            onPageChange={(p) => setPage(p)}
          />
        )}
      </div>

      {/* Review Action Dialog */}
      <ReviewActionModal
        isOpen={Boolean(selectedReviewItem)}
        onClose={() => setSelectedReviewItem(null)}
        item={selectedReviewItem}
        onSuccess={loadReviewQueue}
      />
    </div>
  );
};


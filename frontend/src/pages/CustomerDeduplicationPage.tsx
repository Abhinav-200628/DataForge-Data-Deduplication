import React, { useEffect, useState } from 'react';
import { Search, RotateCw, Eye, Users, Mail, Phone, Tag, MapPin, GitCommit } from 'lucide-react';
import { api } from '../services/api';
import { MasterCustomerRecord } from '../types';
import { Pagination } from '../components/common/Pagination';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import { ErrorState, EmptyState } from '../components/common/EmptyState';
import { RecordDetailModal } from '../components/records/RecordDetailModal';

export const CustomerDeduplicationPage: React.FC = () => {
  const [records, setRecords] = useState<MasterCustomerRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal state
  const [selectedMasterId, setSelectedMasterId] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  const loadRecords = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listRecords({
        entity_type: 'customer',
        search: debouncedSearch || undefined,
        page,
        page_size: 15,
      });
      setRecords(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load customer records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, [page, debouncedSearch]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Header & Search Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
              <Users className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Customer Golden Records
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Canonical customer profiles produced by deterministic survivorship and UUIDv5 master keying.
          </p>
        </div>

        {/* Search Control */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name, email, phone, tax ID..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#111B2D] border border-[#1C283F] text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500/40"
            />
          </div>
          <button
            onClick={loadRecords}
            className="p-2 rounded-xl border border-[#1C283F] bg-[#111B2D] text-slate-300 hover:text-white hover:border-cyan-500/40 transition-colors"
            title="Refresh Records"
          >
            <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Records Table */}
      <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl overflow-hidden shadow-card">
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={8} />
          </div>
        ) : error ? (
          <div className="p-6">
            <ErrorState message={error} onRetry={loadRecords} />
          </div>
        ) : records.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No customer golden records found"
              description={
                debouncedSearch
                  ? `No customer records matched '${debouncedSearch}'.`
                  : 'Execute a customer pipeline run to generate golden master records.'
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0D1423] text-slate-400 uppercase tracking-wider text-[10px] border-b border-[#1C283F]">
                <tr>
                  <th className="px-5 py-3">Master ID</th>
                  <th className="px-5 py-3">Customer Name</th>
                  <th className="px-5 py-3">Primary Contact</th>
                  <th className="px-5 py-3">Location</th>
                  <th className="px-5 py-3">Tax ID / SSN</th>
                  <th className="px-5 py-3 text-center">Merged Sources</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C283F] text-slate-300">
                {records.map((r) => {
                  const fullName = `${r.first_name || ''} ${r.last_name || ''}`.trim() || '—';
                  const location = [r.city, r.state, r.postal_code].filter(Boolean).join(', ') || '—';
                  const sources = r.source_count || 1;

                  return (
                    <tr key={r.master_id} className="hover:bg-[#16233B]/50 transition-colors">
                      <td className="px-5 py-3.5 font-mono text-cyan-300 font-medium">
                        <span className="truncate block max-w-[140px]" title={r.master_id}>
                          {r.master_id}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-white">
                        {fullName}
                      </td>
                      <td className="px-5 py-3.5 space-y-0.5">
                        {r.primary_email && (
                          <div className="flex items-center gap-1.5 text-slate-300 font-mono text-[11px] truncate max-w-[180px]">
                            <Mail className="w-3 h-3 text-cyan-400 flex-shrink-0" />
                            <span>{r.primary_email}</span>
                          </div>
                        )}
                        {r.primary_phone && (
                          <div className="flex items-center gap-1.5 text-slate-400 font-mono text-[10px]">
                            <Phone className="w-3 h-3 text-slate-500 flex-shrink-0" />
                            <span>{r.primary_phone}</span>
                          </div>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-slate-300 truncate max-w-[140px]">
                        {location}
                      </td>
                      <td className="px-5 py-3.5 font-mono text-slate-300">
                        {r.tax_id || '—'}
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-mono text-[11px] font-semibold ${
                            sources > 1
                              ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                              : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                          }`}
                        >
                          <GitCommit className="w-3 h-3" />
                          {sources} {sources === 1 ? 'source' : 'sources'}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => setSelectedMasterId(r.master_id)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1C283F] bg-[#0D1423] text-slate-300 hover:text-white hover:border-cyan-500/40 hover:bg-[#111B2D] transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Lineage</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {total > 0 && (
          <Pagination
            currentPage={page}
            totalItems={total}
            pageSize={15}
            onPageChange={(p) => setPage(p)}
          />
        )}
      </div>

      {/* Record Lineage Modal */}
      <RecordDetailModal
        isOpen={Boolean(selectedMasterId)}
        onClose={() => setSelectedMasterId(null)}
        entityType="customer"
        masterId={selectedMasterId}
      />
    </div>
  );
};


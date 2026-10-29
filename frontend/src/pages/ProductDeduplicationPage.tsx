import React, { useEffect, useState } from 'react';
import { Search, RotateCw, Eye, Package, Tag, DollarSign, GitCommit, Layers } from 'lucide-react';
import { api } from '../services/api';
import { MasterProductRecord } from '../types';
import { Pagination } from '../components/common/Pagination';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import { ErrorState, EmptyState } from '../components/common/EmptyState';
import { RecordDetailModal } from '../components/records/RecordDetailModal';

export const ProductDeduplicationPage: React.FC = () => {
  const [records, setRecords] = useState<MasterProductRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal state
  const [selectedMasterId, setSelectedMasterId] = useState<string | null>(null);

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
        entity_type: 'product',
        search: debouncedSearch || undefined,
        page,
        page_size: 15,
      });
      setRecords(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load product records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, [page, debouncedSearch]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header & Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400">
              <Package className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Product Golden Catalog
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Deduplicated catalog items unified across SKU collisions, UPC check-digits, and brand hierarchies.
          </p>
        </div>

        {/* Search Input */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by product name, brand, SKU, UPC..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-[#111B2D] border border-[#1C283F] text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-violet-500/40"
            />
          </div>
          <button
            onClick={loadRecords}
            className="p-2 rounded-xl border border-[#1C283F] bg-[#111B2D] text-slate-300 hover:text-white hover:border-violet-500/40 transition-colors"
            title="Refresh Products"
          >
            <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin text-violet-400' : ''}`} />
          </button>
        </div>
      </div>

      {/* Products Table */}
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
              title="No product golden records found"
              description={
                debouncedSearch
                  ? `No product records matched '${debouncedSearch}'.`
                  : 'Execute a product pipeline run to generate golden catalog records.'
              }
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0D1423] text-slate-400 uppercase tracking-wider text-[10px] border-b border-[#1C283F]">
                <tr>
                  <th className="px-5 py-3">Master ID</th>
                  <th className="px-5 py-3">Product Name</th>
                  <th className="px-5 py-3">Brand</th>
                  <th className="px-5 py-3">SKU & UPC</th>
                  <th className="px-5 py-3">Category</th>
                  <th className="px-5 py-3">Unit Price</th>
                  <th className="px-5 py-3 text-center">Merged Sources</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C283F] text-slate-300">
                {records.map((r) => {
                  const sources = r.source_count || 1;
                  return (
                    <tr key={r.master_id} className="hover:bg-[#16233B]/50 transition-colors">
                      <td className="px-5 py-3.5 font-mono text-violet-300 font-medium">
                        <span className="truncate block max-w-[140px]" title={r.master_id}>
                          {r.master_id}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-white max-w-[200px] truncate" title={r.product_name}>
                        {r.product_name}
                      </td>
                      <td className="px-5 py-3.5 font-medium text-slate-200">
                        {r.brand}
                      </td>
                      <td className="px-5 py-3.5 space-y-0.5">
                        <div className="font-mono text-[11px] text-slate-300">
                          SKU: {r.primary_sku || '—'}
                        </div>
                        {r.primary_upc_ean && (
                          <div className="font-mono text-[10px] text-slate-400">
                            UPC: {r.primary_upc_ean}
                          </div>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-slate-300 truncate max-w-[120px]">
                        {r.category || '—'}
                      </td>
                      <td className="px-5 py-3.5 font-mono font-bold text-emerald-400">
                        {r.unit_price ? `$${Number(r.unit_price).toFixed(2)}` : '—'}
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
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1C283F] bg-[#0D1423] text-slate-300 hover:text-white hover:border-violet-500/40 hover:bg-[#111B2D] transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5 text-violet-400" />
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
        entityType="product"
        masterId={selectedMasterId}
      />
    </div>
  );
};


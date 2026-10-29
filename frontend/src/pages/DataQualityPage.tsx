import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertOctagon,
  FileX,
  RotateCw,
  Search,
  Code,
} from 'lucide-react';
import { api } from '../services/api';
import { DataQualitySummary, QuarantineRecordItem } from '../types';
import { KpiCard } from '../components/common/KpiCard';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import { ErrorState, EmptyState } from '../components/common/EmptyState';
import { Modal } from '../components/common/Modal';

export const DataQualityPage: React.FC = () => {
  const [dataQuality, setDataQuality] = useState<DataQualitySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPayload, setSelectedPayload] = useState<QuarantineRecordItem | null>(null);

  const loadDataQuality = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDataQualitySummary(1, 30);
      setDataQuality(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load data quality metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDataQuality();
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Data Quality & Quarantine Store
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Diagnostic breakdown of schema errors, unparseable timestamps, and missing identifiers.
          </p>
        </div>

        <button
          onClick={loadDataQuality}
          className="p-2 rounded-xl border border-[#1C283F] bg-[#111B2D] text-slate-300 hover:text-white hover:border-cyan-500/40 transition-colors"
          title="Refresh Data Quality"
        >
          <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Accepted Clean Records"
          value={dataQuality?.total_accepted.toLocaleString() || '0'}
          subtitle="Passed all schema validations"
          icon={ShieldCheck}
          variant="emerald"
        />
        <KpiCard
          title="Quarantined Records"
          value={dataQuality?.total_quarantined.toLocaleString() || '0'}
          subtitle="Isolated without pipeline crash"
          icon={ShieldAlert}
          variant="rose"
        />
        <KpiCard
          title="Quarantine Rate"
          value={`${dataQuality?.quarantine_rate_pct.toFixed(1) || '0.0'}%`}
          subtitle="Proportion of corrupted rows"
          icon={AlertOctagon}
          variant="amber"
        />
        <KpiCard
          title="Active Error Codes"
          value={Object.keys(dataQuality?.rejection_code_counts || {}).length}
          subtitle="Unique validation fault types"
          icon={FileX}
          variant="cyan"
        />
      </div>

      {/* Error Codes Distribution Grid */}
      <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl p-6 shadow-card">
        <h3 className="text-sm font-semibold text-white mb-1">
          Quarantine Attribution by Diagnostic Code
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          Exact violations recorded during streaming ingestion validation
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(dataQuality?.rejection_code_counts || {}).map(([code, count]) => (
            <div
              key={code}
              className="p-4 rounded-xl bg-[#0D1423] border border-[#1C283F] flex items-center justify-between"
            >
              <div>
                <span className="font-mono text-xs font-bold text-rose-300 block">
                  {code}
                </span>
                <span className="text-[10px] text-slate-400">
                  {code === 'MISSING_REQUIRED_FIELD' && 'Non-nullable column was blank'}
                  {code === 'INVALID_DATA_TYPE' && 'Malformed email, price, or data format'}
                  {code === 'MALFORMED_DATE' && 'Date of birth or timestamp parsing error'}
                  {code === 'DUPLICATE_SOURCE_KEY' && 'Duplicate source system + ID in batch'}
                  {code === 'MALFORMED_ROW' && 'Column count mismatch in CSV line'}
                </span>
              </div>
              <span className="font-mono text-base font-bold text-white px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20">
                {count.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Quarantined Records Table */}
      <div className="bg-[#111B2D] border border-[#1C283F] rounded-2xl overflow-hidden shadow-card">
        <div className="p-5 border-b border-[#1C283F]">
          <h3 className="text-sm font-semibold text-white">Quarantine Record Audit Trail</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Preserved original payloads and explicit diagnostic rejection messages
          </p>
        </div>

        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={6} />
          </div>
        ) : error ? (
          <div className="p-6">
            <ErrorState message={error} onRetry={loadDataQuality} />
          </div>
        ) : dataQuality?.recent_quarantines.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="Zero quarantine violations"
              description="No records have failed schema validation."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0D1423] text-slate-400 uppercase tracking-wider text-[10px] border-b border-[#1C283F]">
                <tr>
                  <th className="px-5 py-3">Quarantine ID</th>
                  <th className="px-5 py-3">Domain</th>
                  <th className="px-5 py-3">Source Key</th>
                  <th className="px-5 py-3">Rejection Reason</th>
                  <th className="px-5 py-3">Quarantined At</th>
                  <th className="px-5 py-3 text-right">Raw Payload</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1C283F] text-slate-300">
                {dataQuality?.recent_quarantines.map((q) => {
                  const firstReason = q.rejection_reasons?.[0];
                  return (
                    <tr key={q.quarantine_id} className="hover:bg-[#16233B]/50 transition-colors">
                      <td className="px-5 py-3.5 font-mono text-rose-300 font-medium">
                        {q.quarantine_id}
                      </td>
                      <td className="px-5 py-3.5">
                        <span className="font-semibold text-white">{q.entity_type}</span>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-slate-300">
                        {q.source_system}:{q.source_record_id}
                      </td>
                      <td className="px-5 py-3.5 max-w-sm">
                        {firstReason ? (
                          <div>
                            <span className="px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 font-mono text-[10px] font-bold mr-1.5">
                              {firstReason.code}
                            </span>
                            <span className="text-slate-300">{firstReason.message}</span>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="px-5 py-3.5 font-mono text-slate-400">
                        {new Date(q.quarantined_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => setSelectedPayload(q)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#1C283F] bg-[#0D1423] text-slate-300 hover:text-white hover:border-cyan-500/40 hover:bg-[#111B2D] transition-colors"
                        >
                          <Code className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Raw Payload Inspection Modal */}
      <Modal
        isOpen={Boolean(selectedPayload)}
        onClose={() => setSelectedPayload(null)}
        title="Quarantined Record Payload"
        subtitle={`ID: ${selectedPayload?.quarantine_id || ''} • System: ${selectedPayload?.source_system || ''}`}
        maxWidth="xl"
      >
        <div className="space-y-4 text-xs">
          <div>
            <h4 className="font-semibold text-slate-300 mb-2">Rejection Faults</h4>
            <div className="space-y-1.5">
              {selectedPayload?.rejection_reasons.map((r, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300"
                >
                  <span className="font-mono font-bold block mb-0.5">{r.code}</span>
                  <p>{r.message}</p>
                  {r.invalid_value !== undefined && (
                    <span className="mt-1 block font-mono text-[10px] text-slate-400">
                      Invalid Value: {JSON.stringify(r.invalid_value)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-slate-300 mb-2">Original Raw CSV Payload</h4>
            <pre className="p-4 rounded-xl bg-[#0D1423] border border-[#1C283F] text-slate-200 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(selectedPayload?.raw_payload, null, 2)}
            </pre>
          </div>
        </div>
      </Modal>
    </div>
  );
};


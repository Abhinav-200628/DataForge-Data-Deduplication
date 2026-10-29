import React, { useEffect, useState } from 'react';
import { Modal } from '../common/Modal';
import { api } from '../../services/api';
import { MasterLineageDetail } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { Skeleton } from '../common/SkeletonLoader';
import { GitCommit, ShieldAlert, CheckCircle, ExternalLink, Calendar, Mail, Phone, MapPin, Tag } from 'lucide-react';

interface RecordDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  entityType: 'customer' | 'product';
  masterId: string | null;
}

export const RecordDetailModal: React.FC<RecordDetailModalProps> = ({
  isOpen,
  onClose,
  entityType,
  masterId,
}) => {
  const [detail, setDetail] = useState<MasterLineageDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && masterId) {
      setLoading(true);
      setError(null);
      api
        .getRecordLineage(entityType, masterId)
        .then((data) => setDetail(data))
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
    }
  }, [isOpen, masterId, entityType]);

  if (!isOpen) return null;

  const m = detail?.master_record;
  const isCust = entityType === 'customer';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isCust ? 'Customer Master Record & Provenance' : 'Product Master Record & Provenance'}
      subtitle={`Canonical Golden Record: ${masterId || ''}`}
      maxWidth="3xl"
    >
      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-20 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-xl" />
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          {error}
        </div>
      ) : m ? (
        <div className="space-y-6">
          {/* Top Master Record Card */}
          <div className="p-5 rounded-xl bg-[#0D1423] border border-[#1C283F]">
            <div className="flex items-start justify-between gap-4 mb-4 pb-3 border-b border-[#1C283F]/80">
              <div>
                <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-cyan-400">
                  {entityType} Master Entity (Version {m.record_version || 1})
                </span>
                <h4 className="text-lg font-bold text-white mt-0.5">
                  {isCust
                    ? `${m.first_name || ''} ${m.last_name || ''}`.trim() || 'Unknown Customer'
                    : m.product_name}
                </h4>
                {!isCust && m.brand && (
                  <span className="text-xs font-semibold text-slate-300">
                    Brand: <span className="text-cyan-400">{m.brand}</span>
                  </span>
                )}
              </div>
              <div className="text-right">
                <span className="text-[10px] text-slate-400 font-mono block">Master UUIDv5</span>
                <span className="text-xs font-mono font-medium text-slate-200 select-all">
                  {m.master_id}
                </span>
              </div>
            </div>

            {/* Field Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
              {isCust ? (
                <>
                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60">
                    <span className="text-[10px] text-slate-400 flex items-center gap-1 mb-1">
                      <Mail className="w-3 h-3 text-cyan-400" /> Primary Email
                    </span>
                    <span className="font-mono text-slate-200 truncate block">
                      {m.primary_email || '—'}
                    </span>
                    {Array.isArray(m.secondary_emails) && m.secondary_emails.length > 0 && (
                      <span className="text-[10px] text-slate-400 mt-1 block">
                        Aliases: {m.secondary_emails.join(', ')}
                      </span>
                    )}
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60">
                    <span className="text-[10px] text-slate-400 flex items-center gap-1 mb-1">
                      <Phone className="w-3 h-3 text-cyan-400" /> Primary Phone
                    </span>
                    <span className="font-mono text-slate-200 truncate block">
                      {m.primary_phone || '—'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60">
                    <span className="text-[10px] text-slate-400 flex items-center gap-1 mb-1">
                      <Tag className="w-3 h-3 text-cyan-400" /> Tax ID / SSN
                    </span>
                    <span className="font-mono text-slate-200 truncate block">
                      {m.tax_id || '—'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60 sm:col-span-2">
                    <span className="text-[10px] text-slate-400 flex items-center gap-1 mb-1">
                      <MapPin className="w-3 h-3 text-cyan-400" /> Address
                    </span>
                    <span className="text-slate-200">
                      {[m.street_address, m.city, m.state, m.postal_code, m.country]
                        .filter(Boolean)
                        .join(', ') || '—'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60">
                    <span className="text-[10px] text-slate-400 flex items-center gap-1 mb-1">
                      <Calendar className="w-3 h-3 text-cyan-400" /> Date of Birth
                    </span>
                    <span className="font-mono text-slate-200">{m.date_of_birth || '—'}</span>
                  </div>
                </>
              ) : (
                <>
                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60">
                    <span className="text-[10px] text-slate-400 block mb-1">Primary SKU</span>
                    <span className="font-mono text-slate-200 truncate block">
                      {m.primary_sku || '—'}
                    </span>
                    {Array.isArray(m.secondary_skus) && m.secondary_skus.length > 0 && (
                      <span className="text-[10px] text-slate-400 mt-1 block">
                        Aliases: {m.secondary_skus.join(', ')}
                      </span>
                    )}
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60">
                    <span className="text-[10px] text-slate-400 block mb-1">UPC / EAN</span>
                    <span className="font-mono text-slate-200 truncate block">
                      {m.primary_upc_ean || '—'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60">
                    <span className="text-[10px] text-slate-400 block mb-1">Price</span>
                    <span className="font-mono text-emerald-400 font-bold block">
                      {m.unit_price ? `$${Number(m.unit_price).toFixed(2)} ${m.currency || 'USD'}` : '—'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-[#111B2D] border border-[#1C283F]/60 sm:col-span-3">
                    <span className="text-[10px] text-slate-400 block mb-1">Category</span>
                    <span className="text-slate-200">{m.category || '—'}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Contributing Lineage Provenance */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <GitCommit className="w-4 h-4 text-cyan-400" />
              <h5 className="text-sm font-semibold text-white">
                Source Lineage & Contributing Records ({detail?.lineage.length || 0})
              </h5>
            </div>

            <div className="space-y-2">
              {detail?.lineage.map((l) => (
                <div
                  key={l.lineage_id}
                  className="p-3.5 rounded-xl bg-[#0D1423] border border-[#1C283F] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono text-[10px] font-bold border border-cyan-500/20">
                        {l.source_system}
                      </span>
                      <span className="font-mono font-medium text-slate-200">
                        {l.source_record_id}
                      </span>
                      <StatusBadge status={l.decision} size="sm" />
                    </div>
                    <div className="text-slate-400 text-[11px]">
                      Rule: <span className="font-mono text-slate-300">{l.match_rule_id}</span>
                      {l.confidence_score && (
                        <span className="ml-2 font-mono text-cyan-400">
                          (Confidence: {(l.confidence_score * 100).toFixed(0)}%)
                        </span>
                      )}
                    </div>
                    {Array.isArray(l.merge_reasons) && l.merge_reasons.length > 0 && (
                      <div className="text-[10px] text-slate-400 mt-1 italic">
                        {l.merge_reasons.join(' • ')}
                      </div>
                    )}
                  </div>
                  <div className="text-right text-[10px] text-slate-400 font-mono whitespace-nowrap">
                    {new Date(l.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </Modal>
  );
};


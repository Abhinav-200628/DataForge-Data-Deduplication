import React, { useEffect, useState } from 'react';
import { Settings, Shield, Cpu, Database, FolderCheck, Sliders, CheckCircle } from 'lucide-react';
import { api } from '../services/api';
import { SettingsData } from '../types';
import { TableSkeleton } from '../components/common/SkeletonLoader';
import { ErrorState } from '../components/common/EmptyState';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .getSettings()
      .then((data) => setSettings(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <TableSkeleton rows={6} />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
            <Settings className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight">
            Pipeline Architecture & Configuration
          </h2>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          Active matching thresholds, survivorship policies, and storage destinations.
        </p>
      </div>

      {/* Storage and System Paths */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl bg-[#111B2D] border border-[#1C283F] shadow-card flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 flex-shrink-0">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-slate-400">
              Active SQLite Storage
            </span>
            <div className="text-xs font-mono font-semibold text-white mt-1 break-all">
              {settings?.database_path}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              SQLite WAL mode with transactional publishing and ACID rollback.
            </p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-[#111B2D] border border-[#1C283F] shadow-card flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400 flex-shrink-0">
            <FolderCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-slate-400">
              Export Destination
            </span>
            <div className="text-xs font-mono font-semibold text-white mt-1 break-all">
              {settings?.output_directory}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Dual CSV and JSON exports for masters, lineage, quarantine, and review queue.
            </p>
          </div>
        </div>
      </div>

      {/* Core Rules Display */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Customer Rules */}
        <div className="p-6 rounded-2xl bg-[#111B2D] border border-[#1C283F] shadow-card">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">Customer Resolution Rules</h3>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Thresholds for exact Tax ID links, RapidFuzz corroboration, and shared contact safeguards.
          </p>

          <pre className="p-4 rounded-xl bg-[#0D1423] border border-[#1C283F] text-slate-200 font-mono text-[11px] overflow-x-auto max-h-72">
            {JSON.stringify(settings?.customer_rules, null, 2)}
          </pre>
        </div>

        {/* Product Rules */}
        <div className="p-6 rounded-2xl bg-[#111B2D] border border-[#1C283F] shadow-card">
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-4 h-4 text-violet-400" />
            <h3 className="text-sm font-bold text-white">Product Resolution Rules</h3>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            UPC/EAN check-digit verification, SKU collision alerts, and price tolerance filters.
          </p>

          <pre className="p-4 rounded-xl bg-[#0D1423] border border-[#1C283F] text-slate-200 font-mono text-[11px] overflow-x-auto max-h-72">
            {JSON.stringify(settings?.product_rules, null, 2)}
          </pre>
        </div>
      </div>

      {/* Architecture Highlights Note */}
      <div className="p-5 rounded-2xl bg-[#111B2D] border border-[#1C283F] text-xs text-slate-300 space-y-2">
        <h4 className="font-semibold text-white flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-cyan-400" />
          Senior Engineering Architectural Guarantees
        </h4>
        <ul className="list-disc pl-5 space-y-1 text-slate-400">
          <li>
            <strong className="text-slate-200">Zero False Merges Guarantee:</strong> Hard-conflict vetoes on Tax ID, DOB, Brand, and UPC prevent wrongful identity consolidation.
          </li>
          <li>
            <strong className="text-slate-200">Transitive Merge Protection:</strong> Graph connected components are audited for internal pairwise contradictions before cluster consolidation.
          </li>
          <li>
            <strong className="text-slate-200">Deterministic Survivorship:</strong> Golden master attributes survive based on source priority (ERP &gt; CRM &gt; WEB), update recency timestamps, and stable tie-breaking.
          </li>
          <li>
            <strong className="text-slate-200">Strict Conservation Laws:</strong> Reconciliation balance (Input = Valid + Quarantined) is asserted at runtime.
          </li>
        </ul>
      </div>
    </div>
  );
};

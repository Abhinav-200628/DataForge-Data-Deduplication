import React from 'react';
import { useLocation } from 'react-router-dom';
import {
  Menu,
  RotateCw,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import { HealthStatus, PipelineRun } from '../../types';

interface HeaderProps {
  onToggleMobileMenu: () => void;
  health: HealthStatus | null;
  latestRun: PipelineRun | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onToggleMobileMenu,
  health,
  latestRun,
  isLoading,
  onRefresh,
}) => {
  const location = useLocation();

  const getPageTitle = (path: string): { title: string; category: string } => {
    switch (path) {
      case '/':
        return { title: 'Overview Dashboard', category: 'Analytics & Telemetry' };
      case '/runs':
        return { title: 'Pipeline Execution', category: 'Orchestration' };
      case '/customers':
        return { title: 'Customer Deduplication', category: 'Master Data' };
      case '/products':
        return { title: 'Product Deduplication', category: 'Catalog Master' };
      case '/review-queue':
        return { title: 'Manual Review Workspace', category: 'Quality Assurance' };
      case '/data-quality':
        return { title: 'Data Quality & Quarantine', category: 'Observability' };
      case '/reports':
        return { title: 'Audit & Reconciliation Reports', category: 'Governance' };
      case '/settings':
        return { title: 'Pipeline Rules & Configuration', category: 'Settings' };
      default:
        return { title: 'Data Deduplication Platform', category: 'DataForge' };
    }
  };

  const { title, category } = getPageTitle(location.pathname);

  return (
    <header className="h-16 px-6 bg-[#0D1423]/90 backdrop-blur-md border-b border-[#1C283F] flex items-center justify-between sticky top-0 z-30">
      {/* Left: Mobile Toggle & Breadcrumbs */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleMobileMenu}
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium">
            <span>DATAFORGE</span>
            <span>/</span>
            <span className="text-cyan-400/90">{category}</span>
          </div>
          <h1 className="text-base font-bold text-white tracking-tight leading-tight">
            {title}
          </h1>
        </div>
      </div>

      {/* Right: Telemetry Controls & Status */}
      <div className="flex items-center gap-3">
        {/* Latest Run Pill */}
        {latestRun && (
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#111B2D] border border-[#1C283F] text-xs">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-400">Latest Run:</span>
            <span className="font-mono text-slate-200 font-medium truncate max-w-[120px]">
              {latestRun.run_id}
            </span>
            <span
              className={`w-2 h-2 rounded-full ${
                latestRun.status === 'COMPLETED'
                  ? 'bg-emerald-400'
                  : latestRun.status === 'RUNNING'
                  ? 'bg-amber-400 animate-ping'
                  : 'bg-rose-400'
              }`}
            />
          </div>
        )}

        {/* Backend Connection Pill */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
            health?.database_connected
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
          }`}
        >
          {health?.database_connected ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Backend API: Connected</span>
              <span className="sm:hidden">Online</span>
            </>
          ) : (
            <>
              <XCircle className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Backend API: Offline</span>
              <span className="sm:hidden">Offline</span>
            </>
          )}
        </div>

        {/* Refresh Action */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh Data"
          className="p-2 rounded-lg border border-[#1C283F] bg-[#111B2D] text-slate-300 hover:text-white hover:border-cyan-500/40 hover:bg-[#16233B] transition-all disabled:opacity-50"
        >
          <RotateCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
        </button>

        {/* User Profile Avatar Placeholder */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#1C283F]">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-600 to-violet-600 flex items-center justify-center font-bold text-xs text-white shadow-sm ring-1 ring-white/10">
            DF
          </div>
          <div className="hidden xl:block text-left">
            <div className="text-xs font-semibold text-slate-200 leading-tight">Data Steward</div>
            <div className="text-[10px] text-slate-400 font-mono">Demo Role</div>
          </div>
        </div>
      </div>
    </header>
  );
};


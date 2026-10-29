import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PlayCircle,
  Users,
  Package,
  AlertTriangle,
  ShieldCheck,
  FileText,
  Settings,
  Layers,
  Sparkles,
} from 'lucide-react';

interface SidebarProps {
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onCloseMobile }) => {
  const navItems = [
    { name: 'Overview', to: '/', icon: LayoutDashboard },
    { name: 'Pipeline Runs', to: '/runs', icon: PlayCircle },
    { name: 'Customer Deduplication', to: '/customers', icon: Users },
    { name: 'Product Deduplication', to: '/products', icon: Package },
    { name: 'Review Queue', to: '/review-queue', icon: AlertTriangle },
    { name: 'Data Quality', to: '/data-quality', icon: ShieldCheck },
    { name: 'Reports', to: '/reports', icon: FileText },
    { name: 'Settings', to: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#0D1423] border-r border-[#1C283F] flex flex-col h-screen fixed inset-y-0 left-0 z-40 transition-transform">
      {/* Brand Header */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-[#1C283F] bg-[#0A101C]">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 flex items-center justify-center shadow-glow">
          <Layers className="w-5 h-5 text-slate-950 font-bold" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-bold tracking-wider text-white">DATAFORGE</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 font-mono font-medium border border-cyan-500/20">
              MDM
            </span>
          </div>
          <span className="text-[10.5px] text-slate-400 font-medium tracking-tight block">
            Data Deduplication Platform
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          Platform Workspace
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onCloseMobile}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 group ${
                isActive
                  ? 'bg-gradient-to-r from-cyan-500/15 to-violet-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-[#111B2D]/80 border border-transparent'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={`w-4 h-4 transition-colors ${
                    isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-slate-300'
                  }`}
                />
                <span className="truncate">{item.name}</span>
                {item.name === 'Review Queue' && (
                  <span className="ml-auto w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer Info Box */}
      <div className="p-4 border-t border-[#1C283F] bg-[#0A101C]/60">
        <div className="p-3 rounded-xl bg-[#111B2D] border border-[#1C283F]/80 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="text-[11px] font-semibold text-slate-200 truncate">
              MDM Survivorship Engine
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              Deterministic UUIDv5 & SQLite
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};


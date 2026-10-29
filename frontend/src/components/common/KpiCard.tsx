import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: 'cyan' | 'violet' | 'emerald' | 'amber' | 'rose' | 'slate';
  badge?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = 'cyan',
  badge,
}) => {
  const variantStyles = {
    cyan: {
      bg: 'bg-cyan-500/10',
      border: 'border-cyan-500/20 hover:border-cyan-500/40',
      text: 'text-cyan-400',
      glow: 'group-hover:shadow-[0_0_20px_-5px_rgba(6,182,212,0.25)]',
    },
    violet: {
      bg: 'bg-violet-500/10',
      border: 'border-violet-500/20 hover:border-violet-500/40',
      text: 'text-violet-400',
      glow: 'group-hover:shadow-[0_0_20px_-5px_rgba(139,92,246,0.25)]',
    },
    emerald: {
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20 hover:border-emerald-500/40',
      text: 'text-emerald-400',
      glow: 'group-hover:shadow-[0_0_20px_-5px_rgba(16,185,129,0.25)]',
    },
    amber: {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20 hover:border-amber-500/40',
      text: 'text-amber-400',
      glow: 'group-hover:shadow-[0_0_20px_-5px_rgba(245,158,11,0.25)]',
    },
    rose: {
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/20 hover:border-rose-500/40',
      text: 'text-rose-400',
      glow: 'group-hover:shadow-[0_0_20px_-5px_rgba(244,63,94,0.25)]',
    },
    slate: {
      bg: 'bg-slate-500/10',
      border: 'border-slate-500/20 hover:border-slate-500/40',
      text: 'text-slate-400',
      glow: '',
    },
  }[variant];

  return (
    <div
      className={`group relative bg-[#111B2D] border rounded-xl p-5 transition-all duration-300 hover:-translate-y-0.5 ${variantStyles.border} ${variantStyles.glow}`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {title}
        </span>
        <div className={`p-2 rounded-lg ${variantStyles.bg} ${variantStyles.text}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-white font-mono">
          {value}
        </span>
        {badge && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-medium">
            {badge}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="mt-2 text-xs text-slate-400 line-clamp-1">{subtitle}</p>
      )}
    </div>
  );
};


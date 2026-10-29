import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const norm = (status || '').toUpperCase().trim();

  let styles = 'bg-slate-500/10 text-slate-400 border-slate-500/20';

  if (norm === 'COMPLETED' || norm === 'APPROVED' || norm === 'PASSED' || norm === 'RESOLVED') {
    styles = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  } else if (norm === 'RUNNING' || norm === 'PENDING') {
    styles = 'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse';
  } else if (norm === 'FAILED' || norm === 'REJECTED' || norm === 'ERROR') {
    styles = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
  } else if (norm === 'EXACT_MATCH') {
    styles = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
  } else if (norm === 'PROBABLE_MATCH') {
    styles = 'bg-violet-500/10 text-violet-400 border-violet-500/20';
  } else if (norm === 'MANUAL_REVIEW') {
    styles = 'bg-amber-500/10 text-amber-300 border-amber-500/30';
  } else if (norm === 'DISTINCT') {
    styles = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  }

  const sizeClass = size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span
      className={`inline-flex items-center font-medium font-mono uppercase tracking-wider rounded-md border ${sizeClass} ${styles}`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-70" />
      {norm}
    </span>
  );
};


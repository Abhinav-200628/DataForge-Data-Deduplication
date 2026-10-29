import React from 'react';
import { Database, AlertCircle } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ElementType;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No records found',
  description = 'No data matching your current filters or no runs have been executed yet.',
  icon: Icon = Database,
  actionText,
  onAction,
}) => (
  <div className="flex flex-col items-center justify-center p-12 text-center bg-[#111B2D]/50 border border-[#1C283F] border-dashed rounded-xl">
    <div className="p-4 rounded-2xl bg-cyan-500/10 text-cyan-400 mb-4">
      <Icon className="w-8 h-8" />
    </div>
    <h3 className="text-base font-semibold text-white mb-1">{title}</h3>
    <p className="text-sm text-slate-400 max-w-sm mb-5">{description}</p>
    {actionText && onAction && (
      <button
        onClick={onAction}
        className="px-4 py-2 text-xs font-semibold rounded-lg bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-colors shadow-glow"
      >
        {actionText}
      </button>
    )}
  </div>
);

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Failed to load data',
  message,
  onRetry,
}) => (
  <div className="flex flex-col items-center justify-center p-8 text-center bg-rose-500/5 border border-rose-500/20 rounded-xl my-4">
    <div className="p-3 rounded-xl bg-rose-500/10 text-rose-400 mb-3">
      <AlertCircle className="w-6 h-6" />
    </div>
    <h4 className="text-sm font-semibold text-rose-300 mb-1">{title}</h4>
    <p className="text-xs text-slate-400 max-w-md mb-4 font-mono">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="px-3.5 py-1.5 text-xs font-medium rounded-lg border border-rose-500/30 text-rose-300 hover:bg-rose-500/10 transition-colors"
      >
        Retry Connection
      </button>
    )}
  </div>
);


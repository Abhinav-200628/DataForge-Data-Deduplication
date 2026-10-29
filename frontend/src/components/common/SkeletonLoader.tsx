import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = 'h-4 w-full' }) => (
  <div className={`bg-[#1C283F]/60 animate-pulse rounded ${className}`} />
);

export const KpiCardSkeleton: React.FC = () => (
  <div className="bg-[#111B2D] border border-[#1C283F] rounded-xl p-5">
    <div className="flex justify-between items-center mb-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-8 rounded-lg" />
    </div>
    <Skeleton className="h-7 w-20 mb-2" />
    <Skeleton className="h-3 w-36" />
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="w-full bg-[#111B2D] border border-[#1C283F] rounded-xl overflow-hidden p-4 space-y-4">
    <div className="flex gap-4 mb-4">
      <Skeleton className="h-8 w-48 rounded-lg" />
      <Skeleton className="h-8 w-32 rounded-lg" />
    </div>
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex gap-4 items-center">
        <Skeleton className="h-5 w-1/4" />
        <Skeleton className="h-5 w-1/4" />
        <Skeleton className="h-5 w-1/4" />
        <Skeleton className="h-5 w-1/4" />
      </div>
    ))}
  </div>
);


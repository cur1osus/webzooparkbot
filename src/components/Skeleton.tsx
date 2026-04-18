interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'circular' | 'rectangular';
}

export function Skeleton({
  className = '',
  width,
  height,
  variant = 'rectangular',
}: SkeletonProps) {
  const style: React.CSSProperties = {
    width: width ?? '100%',
    height: height ?? (variant === 'text' ? '1em' : '100%'),
  };

  const baseClass = variant === 'circular' ? 'skeleton skeleton-circle' : 'skeleton';

  return (
    <div className={`${baseClass} ${className}`} style={style} />
  );
}

export function CardSkeleton() {
  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-3">
        <Skeleton width={48} height={48} variant="circular" />
        <div className="flex-1">
          <Skeleton width="60%" height={16} className="mb-2" />
          <Skeleton width="40%" height={12} />
        </div>
      </div>
      <Skeleton height={36} />
    </div>
  );
}

export function StatTileSkeleton() {
  return (
    <div className="stat-tile">
      <Skeleton width={34} height={34} variant="circular" className="mb-2" />
      <Skeleton width="50%" height={22} className="mb-1" />
      <Skeleton width="70%" height={11} />
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="px-[14px] pt-3 flex flex-col gap-3">
      <div className="card">
        <div className="flex gap-2 mb-3">
          <Skeleton width={80} height={32} />
          <Skeleton width={80} height={32} />
          <Skeleton width={80} height={32} />
        </div>
        <Skeleton height={60} className="mb-2" />
        <Skeleton height={60} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <StatTileSkeleton />
        <StatTileSkeleton />
        <StatTileSkeleton />
        <StatTileSkeleton />
      </div>
    </div>
  );
}
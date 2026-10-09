// Pulse only when the user has not requested reduced motion.
export default function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`bg-slate-200 dark:bg-slate-700 rounded motion-safe:animate-pulse ${className}`} />;
}
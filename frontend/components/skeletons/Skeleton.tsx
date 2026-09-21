// motion-safe:animate-pulse — Tailwind's built-in prefers-reduced-motion
// handling: the pulse only runs under `@media (prefers-reduced-motion: no-preference)`.
// No custom animation, no JS — satisfies the "respect reduced motion" requirement
// using the design system's existing tooling, not a new dependency.
export default function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`bg-slate-200 dark:bg-slate-700 rounded motion-safe:animate-pulse ${className}`} />;
}
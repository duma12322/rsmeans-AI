import type { DivisionCandidate } from "@/lib/api";

// The RSMeans tree route the backend navigated. Prefers the named breadcrumb
// ("23 - Electrical" › "2301 - Operation & Maintenance" › …) and falls back to
// bare codes when only `path` is available (older responses).
export function PathBreadcrumb({
  path,
  breadcrumb,
}: {
  path: string[];
  breadcrumb?: DivisionCandidate[];
}) {
  const levels: DivisionCandidate[] =
    breadcrumb?.length
      ? breadcrumb
      : (path ?? []).map((code) => ({ code, name: "" }));

  if (!levels.length) return null;

  return (
    <nav className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
      {levels.map((level, i) => (
        <span key={level.code + i} className="flex items-center gap-1.5">
          <span className="flex items-center gap-1">
            <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {level.code}
            </code>
            {level.name && (
              <span className="text-slate-600 dark:text-slate-300">
                {level.name}
              </span>
            )}
          </span>
          {i < levels.length - 1 && (
            <span className="text-slate-300 dark:text-slate-600">›</span>
          )}
        </span>
      ))}
    </nav>
  );
}

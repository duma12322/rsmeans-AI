// The RSMeans tree route the backend navigated, e.g. 26 > 2656 > 265613 > 265613.10
export function PathBreadcrumb({ path }: { path: string[] }) {
  if (!path?.length) return null;
  return (
    <nav className="flex flex-wrap items-center gap-1 text-xs text-slate-500">
      {path.map((code, i) => (
        <span key={code + i} className="flex items-center gap-1">
          <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-slate-600">
            {code}
          </code>
          {i < path.length - 1 && <span className="text-slate-300">›</span>}
        </span>
      ))}
    </nav>
  );
}

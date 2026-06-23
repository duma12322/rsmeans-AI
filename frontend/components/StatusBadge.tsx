import type { Confidence } from "@/lib/api";
import { confidenceStyles } from "@/lib/format";

export function ConfidenceBadge({ value }: { value: Confidence }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${confidenceStyles[value]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {value} confidence
    </span>
  );
}

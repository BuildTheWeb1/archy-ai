import type { Confidence } from "../types";

const CONFIG: Record<Confidence, { label: string; classes: string; tooltip: string }> = {
  high: {
    label: "Sigur",
    classes: "bg-green-100 text-green-700 border-green-200",
    tooltip: "Extras din tabel de armare existent în desen",
  },
  medium: {
    label: "Mediu",
    classes: "bg-yellow-100 text-yellow-700 border-yellow-200",
    tooltip: "Parsată din etichete cu număr de marcă",
  },
  low: {
    label: "Scăzut",
    classes: "bg-red-100 text-red-700 border-red-200",
    tooltip: "Cantitate estimată sau marcă lipsă — verificați manual",
  },
};

interface Props {
  confidence: Confidence;
}

export function ConfidenceBadge({ confidence }: Props) {
  const { label, classes, tooltip } = CONFIG[confidence] ?? CONFIG.low;
  return (
    <span
      title={tooltip}
      className={`inline-block text-xs font-medium px-2 py-0.5 rounded border cursor-help ${classes}`}
    >
      {label}
    </span>
  );
}

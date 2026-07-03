export function StatsCards({
  total,
  success,
  failed,
  elapsed,
}: {
  total: number;
  success: number;
  failed: number;
  elapsed: number;
}) {
  const cards = [
    ["Files", total],
    ["Success", success],
    ["Failed", failed],
    ["Elapsed", `${elapsed}s`],
  ];
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {cards.map(([k, v]) => (
        <div
          key={k}
          className="rounded-3xl border border-white/30 bg-white/60 p-5 shadow-glass dark:bg-slate-900/60"
        >
          <p className="text-sm text-slate-500">{k}</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">
            {v}
          </p>
        </div>
      ))}
    </div>
  );
}

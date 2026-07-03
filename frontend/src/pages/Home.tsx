import { useState } from "react";
import { UploadCard } from "../components/UploadCard";
import { ResultGallery } from "../components/ResultGallery";
import { StatsCards } from "../components/StatsCards";
import { ErrorModal } from "../components/ErrorModal";
import type { ErrorDetail, ProcessingSummary, SessionItem } from "../types/api";
export function Home() {
  const [items, setItems] = useState<SessionItem[]>([]);
  const [stats, setStats] = useState({
    total: 0,
    success: 0,
    failed: 0,
    elapsed: 0,
  });
  const [errors, setErrors] = useState<ErrorDetail[]>([]);
  const onComplete = (summary: ProcessingSummary) => {
    setStats({
      total: summary.total,
      success: summary.successful,
      failed: summary.failed,
      elapsed: summary.elapsed_seconds,
    });
    setItems((prev) => [
      ...summary.results.map((r) => ({
        ...r,
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
      })),
      ...prev,
    ]);
    setErrors(summary.errors);
  };
  return (
    <div className="space-y-8">
      <StatsCards {...stats} />
      <UploadCard onComplete={onComplete} />
      <ResultGallery
        items={items}
        onDelete={(id) => setItems((v) => v.filter((i) => i.id !== id))}
      />
      <ErrorModal errors={errors} onClose={() => setErrors([])} />
      <section
        id="history"
        className="rounded-3xl bg-white/60 p-6 dark:bg-slate-900/60"
      >
        <h2 className="text-2xl font-bold dark:text-white">
          Processing History
        </h2>
        {items.map((i) => (
          <p
            className="mt-2 text-sm text-slate-600 dark:text-slate-300"
            key={i.id}
          >
            {new Date(i.createdAt).toLocaleTimeString()} — {i.original_filename}{" "}
            → {i.output_filename}
          </p>
        ))}
      </section>
    </div>
  );
}

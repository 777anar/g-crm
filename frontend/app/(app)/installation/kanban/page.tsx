"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { listCrews, listInstallationJobs, updateInstallationJobStatus } from "@/lib/api/installation";
import { INSTALLATION_JOB_STATUSES, type Crew, type InstallationJob } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";

const NEXT_STATUS: Record<string, string | null> = {
  scheduled: "en_route",
  en_route: "in_progress",
  in_progress: "completed",
  completed: null,
  cancelled: null,
};

const COLUMN_ACCENT: Record<string, string> = {
  scheduled: "border-t-text-secondary",
  en_route: "border-t-info",
  in_progress: "border-t-warning",
  completed: "border-t-success",
  cancelled: "border-t-danger",
};

/** Click-to-advance Kanban -- no drag-and-drop library in this project, so
 * each card carries its own "move to next stage" action instead. */
export default function InstallationKanbanPage() {
  const t = useTranslations("installation");
  const router = useRouter();

  const [jobs, setJobs] = useState<InstallationJob[] | null>(null);
  const [crews, setCrews] = useState<Crew[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [advancingId, setAdvancingId] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([listInstallationJobs({ limit: 200 }), listCrews()])
      .then(([jobsRes, crewsRes]) => {
        setJobs(jobsRes.items);
        setCrews(crewsRes.items);
      })
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const crewName = (crewId: string | null) => crews.find((c) => c.id === crewId)?.name ?? null;

  const columns = useMemo(() => {
    const map: Record<string, InstallationJob[]> = Object.fromEntries(
      INSTALLATION_JOB_STATUSES.map((s) => [s, []])
    );
    for (const job of jobs ?? []) {
      map[job.status]?.push(job);
    }
    return map;
  }, [jobs]);

  async function handleAdvance(job: InstallationJob) {
    const next = NEXT_STATUS[job.status];
    if (!next) return;
    setAdvancingId(job.id);
    try {
      await updateInstallationJobStatus(job.id, next);
      load();
    } finally {
      setAdvancingId(null);
    }
  }

  if (jobs === null && !error) return <TableSkeleton rows={5} columns={5} />;

  return (
    <div className="flex flex-col gap-4">
      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {INSTALLATION_JOB_STATUSES.map((status) => (
          <div key={status} className="flex flex-col gap-2">
            <div className="flex items-center justify-between px-1">
              <h3 className="text-sm font-semibold text-text-primary">{t(status as any)}</h3>
              <span className="text-xs text-text-secondary">{columns[status]?.length ?? 0}</span>
            </div>
            <div className="flex flex-col gap-2">
              {(columns[status] ?? []).map((job) => (
                <Card
                  key={job.id}
                  className={`cursor-pointer border-t-2 ${COLUMN_ACCENT[status]}`}
                >
                  <div onClick={() => router.push(`/installation/jobs/${job.id}`)}>
                    <p className="font-mono text-sm font-medium text-text-primary">{job.job_number}</p>
                    <p className="mt-1 text-xs text-text-secondary">
                      {job.scheduled_date ? formatDate(job.scheduled_date) : t("unscheduled")}
                    </p>
                    {crewName(job.crew_id) && (
                      <p className="text-xs text-text-secondary">{crewName(job.crew_id)}</p>
                    )}
                  </div>
                  {NEXT_STATUS[job.status] && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleAdvance(job); }}
                      disabled={advancingId === job.id}
                      className="mt-2 w-full rounded-md border border-border py-1 text-xs font-medium text-primary hover:bg-bg disabled:opacity-50"
                    >
                      {advancingId === job.id ? t("saving") : `→ ${t(NEXT_STATUS[job.status] as any)}`}
                    </button>
                  )}
                </Card>
              ))}
              {(columns[status] ?? []).length === 0 && (
                <p className="px-1 text-xs text-text-secondary">{t("noJobsInColumn")}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

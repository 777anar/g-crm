"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { listPortalInstallationJobs } from "@/lib/api/portal";
import type { PortalInstallationJob } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { InstallationJobStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { stickyTheadClass, tableScrollShellClass } from "@/components/ui/data-table";
import { formatDate } from "@/lib/format";

export default function PortalInstallationPage() {
  const t = useTranslations("portal");
  const tCommon = useTranslations("common");
  const [jobs, setJobs] = useState<PortalInstallationJob[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const reload = useCallback(async (options: { append?: boolean; cursor?: string } = {}) => {
    const res = await listPortalInstallationJobs({ cursor: options.cursor });
    setJobs((prev) => (options.append && prev ? [...prev, ...res.items] : res.items));
    setNextCursor(res.next_cursor);
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  function handleLoadMore() {
    if (nextCursor) reload({ append: true, cursor: nextCursor });
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("nav.installation")}</h1>
      </div>

      {jobs === null && <TableSkeleton rows={4} columns={4} />}
      {jobs && jobs.length === 0 && <EmptyState title={t("noInstallationYet")} description={t("noInstallationDesc")} />}

      {jobs && jobs.length > 0 && (
        <>
          <div className={tableScrollShellClass}>
            <table className="w-full text-left text-sm">
              <thead className={stickyTheadClass}>
                <tr>
                  <th className="px-4 py-2 font-medium">{t("jobNumber")}</th>
                  <th className="px-4 py-2 font-medium">{t("tableStatus")}</th>
                  <th className="px-4 py-2 font-medium">{t("scheduledDate")}</th>
                  <th className="px-4 py-2 font-medium">{t("timeSlot")}</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-b border-border last:border-0 hover:bg-bg">
                    <td className="px-4 py-2 font-mono text-text-primary">{job.job_number}</td>
                    <td className="px-4 py-2">
                      <InstallationJobStatusBadge status={job.status} />
                    </td>
                    <td className="px-4 py-2 text-text-secondary">
                      {job.scheduled_date ? formatDate(job.scheduled_date) : tCommon("dash")}
                    </td>
                    <td className="px-4 py-2 text-text-secondary">{job.scheduled_time_slot ?? tCommon("dash")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextCursor && (
            <div className="flex justify-center">
              <Button variant="secondary" onClick={handleLoadMore}>
                {tCommon("loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

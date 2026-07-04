"""Installation Analytics: real data from the Installation module (jobs,
crews) now that it exists, rather than the Orders-field proxy this used
before Installation was built. Daily throughput, delays (finished later than
scheduled), crew productivity, and average installation time are all
computed directly from InstallationJob's own scheduled/started/completed
timestamps -- no audit-log inference needed, since the module tracks these
natively."""
from collections import defaultdict
from datetime import date as date_type

from sqlalchemy.orm import Session

from modules.reports.application.dtos import ReportFilterInput
from modules.reports.infrastructure.repositories.reports_repository import ReportsRepository


class InstallationAnalyticsUseCase:
    def __init__(self, db: Session):
        self.repo = ReportsRepository(db)

    def execute(self, data: ReportFilterInput) -> dict:
        company_id = data.company_id
        dr = data.date_range

        jobs = self.repo.installation_jobs_created_in_range(company_id=company_id, date_range=dr)
        status_snapshot = dict(self.repo.installation_job_status_snapshot(company_id=company_id))
        crew_names = self.repo.crew_names_by_id(company_id=company_id)

        completed_jobs = [j for j in jobs if j.status == "completed" and j.completed_at]

        daily_counts: dict = defaultdict(int)
        for job in completed_jobs:
            daily_counts[job.completed_at.date().isoformat()] += 1
        daily_installations = [{"date": d, "count": c} for d, c in sorted(daily_counts.items())]

        delay_days = []
        delayed_count = 0
        for job in completed_jobs:
            if not job.scheduled_date:
                continue
            scheduled = date_type.fromisoformat(job.scheduled_date)
            actual = job.completed_at.date()
            delta = (actual - scheduled).days
            if delta > 0:
                delayed_count += 1
                delay_days.append(delta)
        avg_delay_days = round(sum(delay_days) / len(delay_days), 1) if delay_days else None

        install_hours = []
        crew_stats: dict = defaultdict(lambda: {"completed_count": 0, "hours": []})
        for job in completed_jobs:
            crew_id = str(job.crew_id) if job.crew_id else None
            if crew_id:
                crew_stats[crew_id]["completed_count"] += 1
            if job.started_at:
                hours = (job.completed_at - job.started_at).total_seconds() / 3600
                if hours >= 0:
                    install_hours.append(hours)
                    if crew_id:
                        crew_stats[crew_id]["hours"].append(hours)

        avg_installation_hours = round(sum(install_hours) / len(install_hours), 1) if install_hours else None

        crew_productivity = [
            {
                "crew_id": crew_id,
                "crew_name": crew_names.get(crew_id, "—"),
                "completed_count": stats["completed_count"],
                "avg_installation_hours": (
                    round(sum(stats["hours"]) / len(stats["hours"]), 1) if stats["hours"] else None
                ),
            }
            for crew_id, stats in crew_stats.items()
        ]
        crew_productivity.sort(key=lambda r: r["completed_count"], reverse=True)

        jobs_awaiting = (
            status_snapshot.get("scheduled", 0)
            + status_snapshot.get("en_route", 0)
            + status_snapshot.get("in_progress", 0)
        )

        return {
            "date_from": dr.date_from,
            "date_to": dr.date_to,
            "kpis": {
                "jobs_created": len(jobs),
                "jobs_completed": len(completed_jobs),
                "jobs_awaiting": jobs_awaiting,
                "jobs_delayed": delayed_count,
                "avg_delay_days": avg_delay_days,
                "avg_installation_hours": avg_installation_hours,
            },
            "job_status_breakdown": [{"status": s, "count": c} for s, c in status_snapshot.items()],
            "daily_installations": daily_installations,
            "crew_productivity": crew_productivity,
        }

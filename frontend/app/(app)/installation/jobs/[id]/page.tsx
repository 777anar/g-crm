"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  addInstallationPhoto,
  getDocumentUrl,
  getInstallationJob,
  listCrews,
  listInstallationPhotos,
  updateInstallationJob,
  updateInstallationJobStatus,
  uploadInstallationAsset,
} from "@/lib/api/installation";
import type { Crew, InstallationJob, InstallationPhoto, PhotoType } from "@/lib/types";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { InstallationJobStatusBadge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { SignaturePad } from "@/components/signature-pad";
import { useToast } from "@/components/ui/toast";
import { ApiRequestError } from "@/lib/api-client";
import { formatDate } from "@/lib/format";

const NEXT_STATUS: Record<string, string | null> = {
  scheduled: "en_route",
  en_route: "in_progress",
  in_progress: null, // completion goes through the dedicated "Complete Job" panel, not a plain advance
  completed: null,
  cancelled: null,
};

const PHOTO_TYPES: PhotoType[] = ["before", "after", "damage", "other"];

export default function InstallationJobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("installation");
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");
  const toast = useToast();

  const [job, setJob] = useState<InstallationJob | null>(null);
  const [crews, setCrews] = useState<Crew[]>([]);
  const [photos, setPhotos] = useState<InstallationPhoto[]>([]);
  const [photoUrls, setPhotoUrls] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [completeMode, setCompleteMode] = useState(false);
  const [completionNotes, setCompletionNotes] = useState("");
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState({
    crew_id: "",
    scheduled_date: "",
    scheduled_time_slot: "",
    route_sequence: "",
    notes: "",
  });

  const reload = useCallback(async () => {
    const [jobRes, crewsRes, photosRes] = await Promise.all([
      getInstallationJob(id),
      listCrews(),
      listInstallationPhotos(id),
    ]);
    setJob(jobRes);
    setCrews(crewsRes.items);
    setPhotos(photosRes.items);
    setForm({
      crew_id: jobRes.crew_id ?? "",
      scheduled_date: jobRes.scheduled_date ?? "",
      scheduled_time_slot: jobRes.scheduled_time_slot ?? "",
      route_sequence: jobRes.route_sequence?.toString() ?? "",
      notes: jobRes.notes ?? "",
    });

    const urls: Record<string, string> = {};
    await Promise.all(
      photosRes.items.map(async (p) => {
        try {
          const { url } = await getDocumentUrl(p.document_id);
          urls[p.document_id] = url;
        } catch {
          // Signed URL fetch failing shouldn't block the rest of the page.
        }
      })
    );
    setPhotoUrls(urls);
    setLoading(false);
  }, [id]);

  useEffect(() => { reload(); }, [reload]);

  async function handleSaveSchedule() {
    try {
      await updateInstallationJob(id, {
        crew_id: form.crew_id || null,
        scheduled_date: form.scheduled_date || null,
        scheduled_time_slot: form.scheduled_time_slot || null,
        route_sequence: form.route_sequence ? Number(form.route_sequence) : null,
        notes: form.notes || null,
      });
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    }
  }

  async function handleAdvance() {
    if (!job) return;
    const next = NEXT_STATUS[job.status];
    if (!next) return;
    setTransitioning(true);
    try {
      await updateInstallationJobStatus(id, next);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleCancel() {
    setTransitioning(true);
    try {
      await updateInstallationJobStatus(id, "cancelled", { cancelledReason: cancelReason || undefined });
      setCancelMode(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleComplete() {
    setTransitioning(true);
    try {
      await updateInstallationJobStatus(id, "completed", { completionNotes: completionNotes || undefined });
      setCompleteMode(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setTransitioning(false);
    }
  }

  async function handleUploadPhoto(file: File, photoType: string) {
    setUploadingPhoto(true);
    try {
      const doc = await uploadInstallationAsset(id, file);
      await addInstallationPhoto(id, { document_id: doc.id, photo_type: photoType });
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setUploadingPhoto(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleCaptureSignature(file: File) {
    setUploadingPhoto(true);
    try {
      const doc = await uploadInstallationAsset(id, file);
      await addInstallationPhoto(id, { document_id: doc.id, photo_type: "signature" });
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : tCommon("actionFailed"));
    } finally {
      setUploadingPhoto(false);
    }
  }

  if (loading || !job) return <TableSkeleton rows={5} columns={4} />;

  const isTerminal = job.status === "completed" || job.status === "cancelled";
  const nextStatus = NEXT_STATUS[job.status];
  const signature = photos.find((p) => p.photo_type === "signature");
  const otherPhotos = photos.filter((p) => p.photo_type !== "signature");

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb items={[{ label: tNav("installation"), href: "/installation/kanban" }, { label: job.job_number }]} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-mono text-xl font-semibold text-text-primary">{job.job_number}</h1>
            <InstallationJobStatusBadge status={job.status} />
          </div>
          <p className="mt-1 text-xs text-text-secondary">
            {t("forOrder")}: <Link href={`/orders/${job.order_id}`} className="text-primary hover:underline">{job.order_id}</Link>
          </p>
        </div>
        {!isTerminal && (
          <div className="flex gap-2">
            {nextStatus && (
              <Button onClick={handleAdvance} disabled={transitioning}>
                {transitioning ? t("saving") : `→ ${t(nextStatus as any)}`}
              </Button>
            )}
            {job.status === "in_progress" && (
              <Button onClick={() => setCompleteMode(!completeMode)}>{t("completeJob")}</Button>
            )}
            {!cancelMode && (
              <Button variant="secondary" onClick={() => setCancelMode(true)}>{t("markCancelled")}</Button>
            )}
          </div>
        )}
      </div>

      {completeMode && (
        <Card className="border-success/30 bg-success/5">
          <p className="mb-2 text-sm font-medium text-text-primary">{t("completionNotes")}</p>
          <textarea
            className="mb-3 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            rows={3}
            value={completionNotes}
            onChange={(e) => setCompletionNotes(e.target.value)}
            placeholder={t("completionNotesPlaceholder")}
          />
          <p className="mb-2 text-sm font-medium text-text-primary">{t("customerSignature")}</p>
          {signature ? (
            <p className="mb-3 text-sm text-success">{t("signatureCaptured")}</p>
          ) : (
            <div className="mb-3">
              <SignaturePad onCapture={handleCaptureSignature} />
            </div>
          )}
          <div className="flex gap-2">
            <Button onClick={handleComplete} disabled={transitioning}>
              {transitioning ? t("saving") : t("confirmCompletion")}
            </Button>
            <Button variant="secondary" onClick={() => setCompleteMode(false)}>{tCommon("cancel")}</Button>
          </div>
        </Card>
      )}

      {cancelMode && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="mb-2 text-sm font-medium text-danger">{t("cancelReason")}</p>
          <textarea
            className="mb-2 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            rows={2}
            aria-label={t("cancelReason")}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
          <div className="flex gap-2">
            <Button onClick={handleCancel} disabled={transitioning}>{t("cancelJob")}</Button>
            <Button variant="secondary" onClick={() => setCancelMode(false)}>{tCommon("cancel")}</Button>
          </div>
        </Card>
      )}

      {job.cancelled_reason && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="text-sm text-danger">{t("cancelReason")}: {job.cancelled_reason}</p>
        </Card>
      )}

      {job.completion_notes && (
        <Card className="border-success/30 bg-success/5">
          <p className="text-sm font-medium text-text-primary">{t("completionNotes")}</p>
          <p className="text-sm text-text-secondary">{job.completion_notes}</p>
        </Card>
      )}

      {/* Schedule */}
      <Card>
        <CardHeader title={t("schedule")} />
        <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="text-xs text-text-secondary">{t("crew")}</label>
            <select
              value={form.crew_id}
              onChange={(e) => setForm({ ...form, crew_id: e.target.value })}
              disabled={isTerminal}
              className="mt-0.5 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            >
              <option value="">{t("unassigned")}</option>
              {crews.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-text-secondary">{t("scheduledDate")}</label>
            <input
              type="date"
              value={form.scheduled_date}
              onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })}
              disabled={isTerminal}
              className="mt-0.5 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            />
          </div>
          <div>
            <label className="text-xs text-text-secondary">{t("timeSlot")}</label>
            <input
              value={form.scheduled_time_slot}
              onChange={(e) => setForm({ ...form, scheduled_time_slot: e.target.value })}
              disabled={isTerminal}
              placeholder="09:00-12:00"
              className="mt-0.5 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            />
          </div>
          <div>
            <label className="text-xs text-text-secondary">{t("routeSequence")}</label>
            <input
              type="number"
              value={form.route_sequence}
              onChange={(e) => setForm({ ...form, route_sequence: e.target.value })}
              disabled={isTerminal}
              className="mt-0.5 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            />
          </div>
        </div>
        <div className="mt-3">
          <label className="text-xs text-text-secondary">{t("notes")}</label>
          <textarea
            className="mt-0.5 w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
            rows={2}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            disabled={isTerminal}
          />
        </div>
        {!isTerminal && (
          <div className="mt-3">
            <Button onClick={handleSaveSchedule}>{tCommon("save")}</Button>
          </div>
        )}
      </Card>

      {/* Signature */}
      {signature && photoUrls[signature.document_id] && (
        <Card>
          <CardHeader title={t("customerSignature")} />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={photoUrls[signature.document_id]} alt={t("customerSignature")} className="max-h-40 rounded-md border border-border bg-white" />
        </Card>
      )}

      {/* Photos */}
      <Card>
        <CardHeader title={t("photos")} />
        {otherPhotos.length === 0 ? (
          <p className="mb-3 text-sm text-text-secondary">{t("noPhotosYet")}</p>
        ) : (
          <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {otherPhotos.map((p) => (
              <div key={p.id} className="overflow-hidden rounded-md border border-border">
                {photoUrls[p.document_id] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={photoUrls[p.document_id]} alt={p.caption ?? p.photo_type} className="h-28 w-full object-cover" />
                ) : (
                  <div className="flex h-28 items-center justify-center text-xs text-text-secondary">{tCommon("loading")}</div>
                )}
                <p className="px-2 py-1 text-xs text-text-secondary">{t(`photoType_${p.photo_type}` as any)}</p>
              </div>
            ))}
          </div>
        )}
        {!isTerminal && (
          <div className="flex flex-wrap items-center gap-2">
            {PHOTO_TYPES.map((type) => (
              <label key={type} className="cursor-pointer rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-bg">
                {uploadingPhoto ? t("saving") : `+ ${t(`photoType_${type}` as any)}`}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  disabled={uploadingPhoto}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUploadPhoto(file, type);
                  }}
                />
              </label>
            ))}
          </div>
        )}
      </Card>

      <p className="text-xs text-text-secondary">
        {t("created")}: {formatDate(job.created_at)}
        {job.completed_at && ` · ${t("completed")}: ${formatDate(job.completed_at)}`}
      </p>
    </div>
  );
}

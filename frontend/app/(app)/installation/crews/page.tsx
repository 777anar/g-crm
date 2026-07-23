"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  addCrewMember,
  createCrew,
  listCrewMembers,
  listCrews,
  removeCrewMember,
  updateCrew,
} from "@/lib/api/installation";
import { listCompanyUsers } from "@/lib/api/companies";
import type { Crew, CrewMember, CompanyUser } from "@/lib/types";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { CrewStatusBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { ApiRequestError } from "@/lib/api-client";
import { usePermission } from "@/lib/permissions";

export default function CrewsPage() {
  const t = useTranslations("installation");
  const tCommon = useTranslations("common");
  const canWrite = usePermission("installation:write");

  const [crews, setCrews] = useState<Crew[] | null>(null);
  const [users, setUsers] = useState<CompanyUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newCrewName, setNewCrewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [expandedCrewId, setExpandedCrewId] = useState<string | null>(null);
  const [members, setMembers] = useState<CrewMember[] | null>(null);
  const [selectedUserId, setSelectedUserId] = useState("");

  const loadCrews = useCallback(() => {
    listCrews()
      .then((r) => setCrews(r.items))
      .catch((err) => setError(err instanceof ApiRequestError ? err.message : t("loadFailed")));
  }, [t]);

  useEffect(() => {
    loadCrews();
    listCompanyUsers().then(setUsers).catch(() => {});
  }, [loadCrews]);

  async function handleCreateCrew(e: React.FormEvent) {
    e.preventDefault();
    if (!newCrewName.trim()) return;
    setCreating(true);
    try {
      await createCrew({ name: newCrewName.trim() });
      setNewCrewName("");
      loadCrews();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    } finally {
      setCreating(false);
    }
  }

  async function handleToggleStatus(crew: Crew) {
    try {
      await updateCrew(crew.id, { status: crew.status === "active" ? "inactive" : "active" });
      loadCrews();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }

  async function handleExpand(crewId: string) {
    if (expandedCrewId === crewId) {
      setExpandedCrewId(null);
      setMembers(null);
      return;
    }
    setExpandedCrewId(crewId);
    setMembers(null);
    try {
      const res = await listCrewMembers(crewId);
      setMembers(res.items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }

  async function handleAddMember(crewId: string) {
    if (!selectedUserId) return;
    try {
      await addCrewMember(crewId, { user_id: selectedUserId });
      setSelectedUserId("");
      setMembers((await listCrewMembers(crewId)).items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }

  async function handleRemoveMember(crewId: string, memberId: string) {
    try {
      await removeCrewMember(crewId, memberId);
      setMembers((await listCrewMembers(crewId)).items);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loadFailed"));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {canWrite && (
        <Card>
          <form onSubmit={handleCreateCrew} className="flex items-end gap-3">
            <div className="flex-1">
              <TextField
                label={t("crewName")}
                value={newCrewName}
                onChange={(e) => setNewCrewName(e.target.value)}
                placeholder={t("crewNamePlaceholder")}
              />
            </div>
            <Button type="submit" disabled={creating || !newCrewName.trim()}>
              {creating ? t("creating") : t("createCrew")}
            </Button>
          </form>
        </Card>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}
      {crews === null && !error && <TableSkeleton rows={3} columns={2} />}
      {crews && crews.length === 0 && <EmptyState title={t("noCrewsYet")} description={t("noCrewsDesc")} />}

      <div className="flex flex-col gap-3">
        {crews?.map((crew) => (
          <Card key={crew.id}>
            <div className="flex items-center justify-between">
              <button className="flex items-center gap-3 text-left" onClick={() => handleExpand(crew.id)}>
                <span className="font-medium text-text-primary">{crew.name}</span>
                <CrewStatusBadge status={crew.status} />
              </button>
              {canWrite && (
                <Button variant="secondary" onClick={() => handleToggleStatus(crew)}>
                  {crew.status === "active" ? t("deactivate") : t("activate")}
                </Button>
              )}
            </div>

            {expandedCrewId === crew.id && (
              <div className="mt-4 border-t border-border pt-4">
                <CardHeader title={t("crewMembers")} />
                {members === null ? (
                  <TableSkeleton rows={2} columns={2} />
                ) : (
                  <ul className="mb-3 flex flex-col divide-y divide-border">
                    {members.map((m) => (
                      <li key={m.id} className="flex items-center justify-between py-2 text-sm">
                        <span className="text-text-primary">
                          {m.full_name} <span className="text-text-secondary">({m.email})</span>
                          {m.is_lead && <span className="ml-2 text-xs font-medium text-primary">{t("crewLead")}</span>}
                        </span>
                        {canWrite && (
                          <button
                            onClick={() => handleRemoveMember(crew.id, m.id)}
                            className="text-xs text-danger hover:underline"
                          >
                            {tCommon("remove")}
                          </button>
                        )}
                      </li>
                    ))}
                    {members.length === 0 && (
                      <li className="py-2 text-sm text-text-secondary">{t("noMembersYet")}</li>
                    )}
                  </ul>
                )}
                {canWrite && (
                  <div className="flex gap-2">
                    <select
                      value={selectedUserId}
                      onChange={(e) => setSelectedUserId(e.target.value)}
                      className="flex-1 rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-primary"
                    >
                      <option value="">{tCommon("select")}…</option>
                      {users
                        .filter((u) => !members?.some((m) => m.user_id === u.id))
                        .map((u) => (
                          <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                        ))}
                    </select>
                    <Button onClick={() => handleAddMember(crew.id)} disabled={!selectedUserId}>
                      {t("addMember")}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

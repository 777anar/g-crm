"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { disableMfa, enableMfa, me, setupMfa } from "@/lib/api/auth";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { TextField } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";

export default function SecuritySettingsPage() {
  const t = useTranslations("security");
  const toast = useToast();

  const [mfaEnabled, setMfaEnabled] = useState<boolean | null>(null);
  const [pendingSecret, setPendingSecret] = useState<string | null>(null);
  const [pendingUri, setPendingUri] = useState<string | null>(null);
  const [enableCode, setEnableCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    me()
      .then((profile) => setMfaEnabled(profile.mfa_enabled))
      .catch(() => setMfaEnabled(false));
  }, []);

  async function handleStartSetup() {
    setError(null);
    setBusy(true);
    try {
      const result = await setupMfa();
      setPendingSecret(result.secret);
      setPendingUri(result.otpauth_uri);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("setupFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmEnable(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await enableMfa(enableCode);
      setMfaEnabled(true);
      setPendingSecret(null);
      setPendingUri(null);
      setEnableCode("");
      toast.success(t("mfaEnabled"));
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("enableFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleDisable(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await disableMfa(disableCode);
      setMfaEnabled(false);
      setDisableCode("");
      toast.success(t("mfaDisabled"));
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("disableFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{t("title")}</h1>
        <p className="text-sm text-text-secondary">{t("subtitle")}</p>
      </div>

      <Card>
        <CardHeader title={t("mfaTitle")} />
        {mfaEnabled === null && <p className="text-sm text-text-secondary">{t("loading")}</p>}

        {mfaEnabled === true && (
          <form className="flex flex-col gap-4" onSubmit={handleDisable}>
            <p className="text-sm text-success">{t("mfaStatusEnabled")}</p>
            <p className="text-sm text-text-secondary">{t("disablePrompt")}</p>
            <TextField
              label={t("mfaCode")}
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value)}
              inputMode="numeric"
              required
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <div>
              <Button type="submit" variant="destructive" disabled={busy}>
                {t("disableMfa")}
              </Button>
            </div>
          </form>
        )}

        {mfaEnabled === false && !pendingSecret && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-text-secondary">{t("mfaStatusDisabled")}</p>
            <div>
              <Button onClick={handleStartSetup} disabled={busy}>
                {t("enableMfa")}
              </Button>
            </div>
            {error && <p className="text-sm text-danger">{error}</p>}
          </div>
        )}

        {mfaEnabled === false && pendingSecret && (
          <form className="flex flex-col gap-4" onSubmit={handleConfirmEnable}>
            <p className="text-sm text-text-secondary">{t("setupInstructions")}</p>
            <div className="rounded-md border border-border bg-bg p-3">
              <p className="text-xs text-text-secondary">{t("secretLabel")}</p>
              <p className="break-all font-mono text-sm text-text-primary">{pendingSecret}</p>
              <p className="mt-2 text-xs text-text-secondary">{t("uriLabel")}</p>
              <p className="break-all font-mono text-xs text-text-secondary">{pendingUri}</p>
            </div>
            <TextField
              label={t("mfaCode")}
              value={enableCode}
              onChange={(e) => setEnableCode(e.target.value)}
              inputMode="numeric"
              autoFocus
              required
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <div>
              <Button type="submit" disabled={busy}>
                {t("confirmEnable")}
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}

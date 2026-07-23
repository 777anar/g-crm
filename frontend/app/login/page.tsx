"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { login, selectCompany, verifyMfa } from "@/lib/api/auth";
import { markSessionActive, setSessionClaims } from "@/lib/session";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { Card } from "@/components/ui/card";
import { LanguageSwitcher } from "@/components/language-switcher";
import type { CompanyMembership } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const t = useTranslations("auth");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companies, setCompanies] = useState<CompanyMembership[] | null>(null);
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(email, password);
      if (result.mfa_required && result.mfa_token) {
        setMfaToken(result.mfa_token);
        return;
      }
      markSessionActive();
      setCompanies(result.companies);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loginFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifyMfa(e: React.FormEvent) {
    e.preventDefault();
    if (!mfaToken) return;
    setError(null);
    setSubmitting(true);
    try {
      const result = await verifyMfa(mfaToken, mfaCode);
      markSessionActive();
      setMfaToken(null);
      setCompanies(result.companies);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("mfaVerifyFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSelectCompany(companyId: string) {
    setSubmitting(true);
    setError(null);
    try {
      const result = await selectCompany(companyId);
      setSessionClaims({
        role: result.role,
        module_permissions: result.module_permissions,
        active_company_id: result.active_company_id,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("selectCompanyFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="relative flex min-h-screen flex-col items-center justify-center gap-4 bg-bg"
      style={{ backgroundImage: "radial-gradient(circle at top, rgba(31,79,216,0.06), transparent 60%)" }}
    >
      <div className="absolute right-4 top-4">
        <LanguageSwitcher />
      </div>

      <Card className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-1 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-sm font-bold text-white">
            GS
          </div>
          <h1 className="mt-2 text-xl font-semibold text-text-primary">{t("title")}</h1>
          <p className="text-sm text-text-secondary">{t("subtitle")}</p>
        </div>

        {!companies && !mfaToken && (
          <form className="flex flex-col gap-4" onSubmit={handleLogin}>
            <TextField
              label={t("email")}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
            <TextField
              label={t("password")}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <Button type="submit" disabled={submitting}>
              {submitting ? t("signingIn") : t("signIn")}
            </Button>
          </form>
        )}

        {mfaToken && (
          <form className="flex flex-col gap-4" onSubmit={handleVerifyMfa}>
            <p className="text-sm text-text-secondary">{t("mfaPrompt")}</p>
            <TextField
              label={t("mfaCode")}
              type="text"
              inputMode="numeric"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              required
              autoFocus
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <Button type="submit" disabled={submitting}>
              {submitting ? t("verifying") : t("verify")}
            </Button>
          </form>
        )}

        {companies && (
          <div className="flex flex-col gap-2">
            <p className="mb-1 text-sm text-text-secondary">{t("chooseCompany")}</p>
            {companies.map((c) => (
              <Button
                key={c.id}
                variant="secondary"
                disabled={submitting}
                onClick={() => handleSelectCompany(c.id)}
                className="justify-between"
              >
                <span>{c.name}</span>
                <span className="text-xs text-text-secondary">{t(`role_${c.role}` as Parameters<typeof t>[0])}</span>
              </Button>
            ))}
            {error && <p className="text-sm text-danger">{error}</p>}
          </div>
        )}
      </Card>
      <p className="text-xs text-text-secondary">{t("footerCompanies")}</p>
    </div>
  );
}

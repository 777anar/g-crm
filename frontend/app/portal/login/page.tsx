"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { portalLogin } from "@/lib/api/portal";
import { markPortalSessionActive } from "@/lib/portal-session";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { Card } from "@/components/ui/card";
import { LanguageSwitcher } from "@/components/language-switcher";

export default function PortalLoginPage() {
  const router = useRouter();
  const t = useTranslations("portal");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await portalLogin(email, password);
      markPortalSessionActive();
      router.push("/portal/dashboard");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("loginFailed"));
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
          <h1 className="mt-2 text-xl font-semibold text-text-primary">{t("loginTitle")}</h1>
          <p className="text-sm text-text-secondary">{t("loginSubtitle")}</p>
        </div>

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
      </Card>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, selectCompany } from "@/lib/api/auth";
import { setAccessToken } from "@/lib/session";
import { ApiRequestError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { Card } from "@/components/ui/card";
import type { CompanyMembership } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companies, setCompanies] = useState<CompanyMembership[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await login(email, password);
      setAccessToken(result.access_token);
      setCompanies(result.companies);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSelectCompany(companyId: string) {
    setSubmitting(true);
    setError(null);
    try {
      const result = await selectCompany(companyId);
      setAccessToken(result.access_token);
      router.push("/crm/customers");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not select company.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg">
      <Card className="w-full max-w-sm">
        <h1 className="mb-4 text-xl font-semibold text-text-primary">Sign in to G-ERP</h1>

        {!companies && (
          <form className="flex flex-col gap-4" onSubmit={handleLogin}>
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && <p className="text-sm text-danger">{error}</p>}
            <Button type="submit" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        )}

        {companies && (
          <div className="flex flex-col gap-2">
            <p className="mb-1 text-sm text-text-secondary">Choose a company to continue</p>
            {companies.map((c) => (
              <Button
                key={c.id}
                variant="secondary"
                disabled={submitting}
                onClick={() => handleSelectCompany(c.id)}
                className="justify-between"
              >
                <span>{c.name}</span>
                <span className="text-xs text-text-secondary">{c.role}</span>
              </Button>
            ))}
            {error && <p className="text-sm text-danger">{error}</p>}
          </div>
        )}
      </Card>
    </div>
  );
}

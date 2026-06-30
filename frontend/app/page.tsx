"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAccessToken } from "@/lib/session";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(getAccessToken() ? "/crm/customers" : "/login");
  }, [router]);

  return null;
}

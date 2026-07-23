"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { hasSession } from "@/lib/session";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(hasSession() ? "/dashboard" : "/login");
  }, [router]);

  return null;
}

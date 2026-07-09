"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function SectionTabs({
  items,
  className = "",
}: {
  items: { label: string; href: string }[];
  className?: string;
}) {
  const pathname = usePathname();
  return (
    <div className={`flex gap-1 border-b border-border ${className}`.trim()}>
      {items.map((item) => {
        const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
              active
                ? "border-primary text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}

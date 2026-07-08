import Link from "next/link";
import { useTranslations } from "next-intl";

export function Breadcrumb({
  items,
  className = "",
}: {
  items: { label: string; href?: string }[];
  className?: string;
}) {
  const tCommon = useTranslations("common");
  return (
    <nav
      className={`flex items-center gap-1 text-sm text-text-secondary ${className}`.trim()}
      aria-label={tCommon("breadcrumb")}
    >
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <span>/</span>}
          {item.href ? (
            <Link href={item.href} className="hover:text-primary hover:underline">
              {item.label}
            </Link>
          ) : (
            <span className="text-text-primary">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}

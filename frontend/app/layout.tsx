import type { Metadata } from "next";
import "./globals.css";
import { LocaleProvider } from "@/lib/i18n/locale-context";

export const metadata: Metadata = {
  title: "G-STONE ERP",
  description: "G-STONE ERP — CRM for G-STONE GALLERY, KORONA PREMIUM, and NEOLITH BAKU",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="az">
      <body className="font-sans text-sm text-text-primary antialiased">
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}

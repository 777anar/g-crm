import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "G-STONE ERP",
  description: "G-STONE ERP — CRM for G-STONE GALLERY, KORONA PREMIUM, and NEOLITH BAKU",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans text-sm text-text-primary antialiased">{children}</body>
    </html>
  );
}

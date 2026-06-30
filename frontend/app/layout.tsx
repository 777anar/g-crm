import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "G-ERP",
  description: "G-ERP — CRM, Sales, Inventory, Production, Installation, Finance, Reports, Marketing, AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans text-sm text-text-primary antialiased">{children}</body>
    </html>
  );
}

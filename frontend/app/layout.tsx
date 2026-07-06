import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import "./globals.css";
import { LocaleProvider } from "@/lib/i18n/locale-context";
import { ThemeProvider } from "@/lib/theme/theme-context";

const montserrat = Montserrat({
  subsets: ["latin", "cyrillic", "latin-ext"],
  variable: "--font-montserrat",
  display: "swap",
});

export const metadata: Metadata = {
  title: "G-STONE ERP",
  description: "G-STONE ERP — CRM for G-STONE GALLERY, KORONA PREMIUM, and NEOLITH BAKU",
};

// Reads the persisted theme choice and applies the `dark` class before React
// hydrates, so the very first paint already matches the user's stored
// preference instead of flashing light-then-dark. Runs inline (not from an
// external file) specifically so it executes before anything else on the
// page, including the CSS itself painting.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem("g_erp_theme");
    if (stored === "dark") {
      document.documentElement.classList.add("dark");
    }
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="az" className={montserrat.variable}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="font-sans text-sm text-text-primary antialiased">
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <ThemeProvider>
          <LocaleProvider>{children}</LocaleProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

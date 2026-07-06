import type { Config } from "tailwindcss";

// Design tokens per UI_UX_GUIDELINES.md section 3-4, expressed as CSS custom
// properties (defined in app/globals.css) rather than hardcoded hex values --
// this is what makes dark mode a token swap instead of a component rewrite,
// exactly as anticipated by that doc's "Dark mode ... later, low-cost
// addition" note. Every existing `bg-bg`/`text-text-primary`/etc. usage
// across the app repoints to the new variable automatically, with no
// per-page changes required.
const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        "surface-raised": "var(--color-surface-raised)",
        border: "var(--color-border)",
        "text-primary": "var(--color-text-primary)",
        "text-secondary": "var(--color-text-secondary)",
        primary: { DEFAULT: "var(--color-primary)", hover: "var(--color-primary-hover)" },
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        danger: "var(--color-danger)",
        info: "var(--color-info)",
      },
      fontFamily: {
        sans: ["var(--font-montserrat)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      spacing: {
        "4.5": "1.125rem",
        "18": "4.5rem",
      },
      borderRadius: {
        DEFAULT: "0.375rem",
      },
      boxShadow: {
        elevated: "var(--shadow-elevated)",
      },
      screens: {
        print: { raw: "print" },
      },
    },
  },
  plugins: [],
};

export default config;

import type { Config } from "tailwindcss";

// Tokens lifted directly from UI_UX_GUIDELINES.md section 3-4.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F8F9FB",
        surface: "#FFFFFF",
        border: "#E2E5EA",
        "text-primary": "#16181D",
        "text-secondary": "#5B6270",
        primary: { DEFAULT: "#1F4FD8", hover: "#173EAD" },
        success: "#1A8754",
        warning: "#B8860B",
        danger: "#C0392B",
        info: "#0E7C9D",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;

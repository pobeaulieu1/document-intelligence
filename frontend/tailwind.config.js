/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      colors: {
        // ── Brand ──────────────────────────────────────────────────────
        // Change these two lines to retheme the whole app.
        brand: {
          50:  "#f5f3ff",
          100: "#ede9fe",
          500: "#8b5cf6",
          600: "#7c3aed",   // primary buttons / accents
          700: "#6d28d9",   // hover state
        },
        // ── Surface ────────────────────────────────────────────────────
        surface: {
          DEFAULT: "#ffffff",
          subtle:  "#f9fafb",
          raised:  "#f3f4f6",
        },
        // ── Status colours ─────────────────────────────────────────────
        success: {
          bg:   "#ecfdf5",
          text: "#065f46",
          ring: "#059669",
        },
        warning: {
          bg:   "#fffbeb",
          text: "#92400e",
          ring: "#d97706",
        },
      },
      boxShadow: {
        card:   "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)",
        drawer: "−24px 0 64px −8px rgb(0 0 0 / 0.18)",
        modal:  "0 20px 60px -12px rgb(0 0 0 / 0.22)",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.25rem",
      },
      animation: {
        "slide-in":  "slideIn 0.22s cubic-bezier(0.16,1,0.3,1)",
        "fade-up":   "fadeUp 0.18s ease-out",
        "new-row":   "newRow 2.4s ease-out forwards",
      },
      keyframes: {
        slideIn: {
          from: { transform: "translateX(100%)", opacity: "0" },
          to:   { transform: "translateX(0)",    opacity: "1" },
        },
        fadeUp: {
          from: { transform: "translateY(8px)", opacity: "0" },
          to:   { transform: "translateY(0)",   opacity: "1" },
        },
        newRow: {
          "0%":   { backgroundColor: "#ede9fe" },
          "100%": { backgroundColor: "transparent" },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

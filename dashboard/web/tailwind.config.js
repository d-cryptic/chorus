export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
    fontFamily: {
      sans: ['"Instrument Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
    },
    colors: {
      background: "var(--background)", foreground: "var(--foreground)",
      card: { DEFAULT: "var(--card)", foreground: "var(--card-foreground)" },
      popover: { DEFAULT: "var(--popover)", foreground: "var(--popover-foreground)" },
      primary: { DEFAULT: "var(--primary)", foreground: "var(--primary-foreground)" },
      secondary: { DEFAULT: "var(--secondary)", foreground: "var(--secondary-foreground)" },
      muted: { DEFAULT: "var(--muted)", foreground: "var(--muted-foreground)" },
      accent: { DEFAULT: "var(--accent)", foreground: "var(--accent-foreground)" },
      destructive: "var(--destructive)", warning: "var(--warning)",
      border: "var(--border)", input: "var(--input)", ring: "var(--ring)",
      "x-blue": "var(--x-blue)",
    },
    animation:{ "fade-in":"fade-in .18s ease-out", "collapse":"collapse .16s ease-in forwards" },
  } },
  plugins: [require('tailwindcss-animate')],
}

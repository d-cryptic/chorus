export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
    fontFamily: {
      sans: ['"Instrument Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
    },
    colors: {
    bg: "var(--bg)", surface: "var(--surface)", "surface-2": "var(--surface-2)",
    line: "var(--line)", "line-soft": "var(--line-soft)",
    text: "var(--text)", muted: "var(--muted)", faint: "var(--faint)",
    "x-blue": "var(--x-blue)", accent: "var(--accent)",
    danger: "var(--danger)", warn: "var(--warn)", good: "var(--good)",
    border:"hsl(var(--border))", input:"hsl(var(--input))", ring:"hsl(var(--ring))",
    background:"hsl(var(--background))", foreground:"hsl(var(--foreground))",
    primary:{DEFAULT:"hsl(var(--primary))",foreground:"hsl(var(--primary-foreground))"},
    secondary:{DEFAULT:"hsl(var(--secondary))",foreground:"hsl(var(--secondary-foreground))"},
    muted:{DEFAULT:"hsl(var(--muted))",foreground:"hsl(var(--muted-foreground))"},
    accent:{DEFAULT:"hsl(var(--accent))",foreground:"hsl(var(--accent-foreground))"},
    destructive:{DEFAULT:"hsl(var(--destructive))",foreground:"hsl(var(--destructive-foreground))"},
    card:{DEFAULT:"hsl(var(--card))",foreground:"hsl(var(--card-foreground))"},
  }, borderRadius:{lg:"var(--radius)",md:"calc(var(--radius) - 2px)",sm:"calc(var(--radius) - 4px)"},
    keyframes:{
      "accordion-down":{from:{height:"0"},to:{height:"var(--radix-accordion-content-height)"}},
      "fade-in":{from:{opacity:"0",transform:"translateY(2px)"},to:{opacity:"1",transform:"none"}},
      "collapse":{from:{opacity:"1",maxHeight:"800px"},to:{opacity:"0",maxHeight:"0px"}},
    },
    animation:{ "fade-in":"fade-in .18s ease-out", "collapse":"collapse .16s ease-in forwards" },
  } },
  plugins: [require('tailwindcss-animate')],
}

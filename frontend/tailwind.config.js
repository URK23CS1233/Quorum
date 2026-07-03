/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg:      "#07070d",
        bg2:     "#0e0e18",
        bg3:     "#141422",
        border:  "#1e1e2e",
        accent:  "#6366f1",
        green:   "#10b981",
        yellow:  "#f59e0b",
        red:     "#ef4444",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "monospace"],
      },
      animation: {
        "float":        "float 5s ease-in-out infinite",
        "float-alt":    "float-alt 6s ease-in-out infinite",
        "aurora":       "aurora 8s ease infinite",
        "spin-slow":    "spin-slow 3s linear infinite",
        "slide-up":     "slide-up 500ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "slide-down":   "slide-down 280ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "slide-right":  "slide-right 280ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "slide-left":   "slide-left 350ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "scale-in":     "scale-in 280ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "scale-spring": "scale-spring 400ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards",
        "fade-in":      "fade-in 280ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "fade-up":      "fade-up 350ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "message-in":   "message-in 350ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards",
        "bar-fill":     "bar-fill 600ms ease-out forwards",
        "ripple":       "ripple 500ms ease-out",
        "pulse-red":    "pulse-red 1.4s ease-in-out infinite",
        "pulse-dot":    "pulse-dot 1s ease-in-out infinite",
        "pulse-glow":   "pulse-glow 2s ease-in-out infinite",
        "glow-breathe": "glow-breathe 2.5s ease-in-out infinite",
        "incident":     "incident-pulse 1.6s ease-in-out infinite",
        "count-flash":  "count-flash 400ms ease-out",
        "shimmer":      "shimmer 1.5s infinite",
        "orbit":        "orbit 4s linear infinite",
        "gradient":     "gradient-pan 3s ease infinite",
        "stagger-fade": "stagger-fade 400ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
      },
      keyframes: {
        "slide-up": {
          from: { opacity: "0", transform: "translateY(20px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          from: { opacity: "0", transform: "translateY(-12px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "slide-right": {
          from: { opacity: "0", transform: "translateX(-20px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        "slide-left": {
          from: { opacity: "0", transform: "translateX(40px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.92)" },
          to:   { opacity: "1", transform: "scale(1)" },
        },
        "scale-spring": {
          "0%":   { transform: "scale(0.85)" },
          "70%":  { transform: "scale(1.02)" },
          "100%": { transform: "scale(1)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "float": {
          "0%":   { transform: "translateY(0px)" },
          "40%":  { transform: "translateY(-18px)" },
          "70%":  { transform: "translateY(-8px)" },
          "100%": { transform: "translateY(0px)" },
        },
        "float-alt": {
          "0%":   { transform: "translateY(0px) rotate(0deg)" },
          "33%":  { transform: "translateY(-14px) rotate(1.5deg)" },
          "66%":  { transform: "translateY(-6px) rotate(-1deg)" },
          "100%": { transform: "translateY(0px) rotate(0deg)" },
        },
        "aurora": {
          "0%":   { backgroundPosition: "0% 50%" },
          "50%":  { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        "gradient-pan": {
          "0%":   { backgroundPosition: "0% 50%" },
          "50%":  { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        "pulse-red": {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 0 0 rgba(239, 68, 68, 0.6)" },
          "50%":      { opacity: "0.7", boxShadow: "0 0 0 8px rgba(239, 68, 68, 0)" },
        },
        "pulse-dot": {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%":      { transform: "scale(1.5)", opacity: "0.6" },
        },
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(99, 102, 241, 0.5)" },
          "50%":      { boxShadow: "0 0 0 10px rgba(99, 102, 241, 0)" },
        },
        "glow-breathe": {
          "0%, 100%": { boxShadow: "0 0 8px rgba(99, 102, 241, 0.3), 0 0 20px rgba(99, 102, 241, 0.1)" },
          "50%":      { boxShadow: "0 0 20px rgba(99, 102, 241, 0.6), 0 0 40px rgba(99, 102, 241, 0.25)" },
        },
        "incident-pulse": {
          "0%, 100%": {
            borderColor: "rgba(239, 68, 68, 0.4)",
            boxShadow: "0 0 0 0 rgba(239, 68, 68, 0.4), 0 0 12px rgba(239, 68, 68, 0.15)",
          },
          "50%": {
            borderColor: "rgba(239, 68, 68, 0.9)",
            boxShadow: "0 0 0 6px rgba(239, 68, 68, 0), 0 0 24px rgba(239, 68, 68, 0.35)",
          },
        },
        "ripple": {
          from: { transform: "scale(0)", opacity: "0.7" },
          to:   { transform: "scale(3)", opacity: "0" },
        },
        "bar-fill": {
          from: { transform: "scaleX(0)" },
          to:   { transform: "scaleX(1)" },
        },
        "count-flash": {
          "0%":   { color: "#e2e8f0" },
          "30%":  { color: "#6366f1" },
          "100%": { color: "#e2e8f0" },
        },
        "shimmer": {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "spin-slow": {
          from: { transform: "rotate(0deg)" },
          to:   { transform: "rotate(360deg)" },
        },
        "orbit": {
          from: { transform: "rotate(0deg) translateX(60px) rotate(0deg)" },
          to:   { transform: "rotate(360deg) translateX(60px) rotate(-360deg)" },
        },
        "typing-dot": {
          "0%, 100%": { transform: "translateY(0)", opacity: "0.4" },
          "40%":      { transform: "translateY(-6px)", opacity: "1" },
          "60%":      { transform: "translateY(0)", opacity: "0.6" },
        },
        "message-in": {
          "0%":   { opacity: "0", transform: "translateY(12px) scale(0.94)" },
          "60%":  { opacity: "1", transform: "translateY(-3px) scale(1.01)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        "stagger-fade": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
      backdropBlur: {
        "xs":  "4px",
        "2xl": "40px",
      },
      transitionTimingFunction: {
        "spring":     "cubic-bezier(0.34, 1.56, 0.64, 1)",
        "smooth-out": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [],
};

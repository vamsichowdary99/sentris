import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#0B0F14",
        surface: "#121821",
        "surface-raised": "#171F2A",
        line: "#1E2733",
        cyan: {
          DEFAULT: "#4FD1E8",
          dim: "#2C6B78",
        },
        amber: {
          DEFAULT: "#F5A623",
          dim: "#8A6220",
        },
        threat: {
          DEFAULT: "#E5484D",
          dim: "#7A2C2E",
        },
        mist: "#8B98A8",
        paper: "#E8EDF2",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "serif"],
        sans: ["var(--font-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        grid: "linear-gradient(to right, #1E2733 1px, transparent 1px), linear-gradient(to bottom, #1E2733 1px, transparent 1px)",
      },
      keyframes: {
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        scan: "scan 6s linear infinite",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;

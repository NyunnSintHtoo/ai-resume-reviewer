import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: "#faf8f5",
        ink: "#1c1917",
        smoke: "#57534e",
        mist: "#a8a29e",
        teal: {
          DEFAULT: "#0d9488",
          hover: "#14b8a6",
          wash: "#f0fdfa",
        },
        amber: {
          DEFAULT: "#d97706",
          wash: "#fffbeb",
        },
        good: {
          DEFAULT: "#059669",
          wash: "#ecfdf5",
        },
        crit: {
          DEFAULT: "#dc2626",
          wash: "#fef2f2",
        },
      },
      borderColor: {
        soft: "rgba(41,37,36,0.08)",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(41,37,36,0.04), 0 8px 24px rgba(41,37,36,0.06)",
        lift: "0 2px 4px rgba(41,37,36,0.05), 0 16px 40px rgba(41,37,36,0.10)",
      },
      fontFamily: {
        sans: ["var(--font-jakarta)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;

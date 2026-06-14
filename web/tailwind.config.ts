import type { Config } from "tailwindcss";

const config: Config = {
  // 启用基于类名（.dark）的暗黑模式切换
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // 配置正文字体
        sans: ["Plus Jakarta Sans", "Inter", "Segoe UI", "PingFang SC", "sans-serif"],
        // 配置标题展示字体
        display: ["Outfit", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#fafafa",
          100: "#f4f4f5",
          200: "#e4e4e7",
          300: "#d4d4d8",
          400: "#a1a1aa",
          500: "#71717a",
          550: "#616167",
          600: "#52525b",
          650: "#4b4b4f",
          700: "#3f3f46",
          800: "#27272a",
          900: "#18181b",
          950: "#09090b",
        },
      },
      boxShadow: {
        // 微拟态与轻盈拟物化阴影
        "glass-light": "0 8px 32px 0 rgba(40, 53, 15, 0.06)",
        "glass-dark": "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out forwards",
        "slide-up": "slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "pulse-glowing": "pulseGlowing 2s infinite ease-in-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(12px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        pulseGlowing: {
          "0%, 100%": { opacity: "0.6", transform: "scale(0.98)" },
          "50%": { opacity: "1", transform: "scale(1.02)", filter: "brightness(1.1)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;

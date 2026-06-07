import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f7f9f0",
          100: "#ebf0d5",
          500: "#6d8a2f",
          700: "#4b6220",
          900: "#28350f",
        },
      },
    },
  },
  plugins: [],
};

export default config;

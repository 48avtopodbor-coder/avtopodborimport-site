import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Графит и оранжевый — палитра 1A
        graphite: {
          900: "#141414",
          800: "#1e1e1e",
          700: "#2a2a2a",
          600: "#3a3a3a",
          500: "#4a4a4a",
        },
        orange: {
          500: "#FF6B00",
          600: "#E55F00",
          400: "#FF8533",
        },
        // Нейтралы
        gray: {
          100: "#F5F5F5",
          200: "#E5E5E5",
          400: "#9A9A9A",
          600: "#666666",
        },
      },
      fontFamily: {
        heading: ["var(--font-unbounded)", "sans-serif"],
        body: ["var(--font-manrope)", "sans-serif"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
      },
    },
  },
  plugins: [],
};

export default config;

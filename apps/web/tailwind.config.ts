import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#182033",
        lavender: "#6658d3",
        mint: "#dff7ec",
        blush: "#fff1f5",
        sky: "#eef6ff",
      },
      boxShadow: {
        soft: "0 18px 50px rgba(25, 35, 58, 0.09)",
      },
    },
  },
  plugins: [],
};

export default config;
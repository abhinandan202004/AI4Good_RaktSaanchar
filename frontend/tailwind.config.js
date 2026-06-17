/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          light: "#DDEFF7",
          DEFAULT: "#C7E5F4",
          dark: "#10354A",
        },
        brand: {
          light: "#DDEFF7",
          DEFAULT: "#C7E5F4",
          dark: "#10354A",
          accent: "#FF5E5E",
          success: "#10B981",
          warning: "#F59E0B",
          darkBg: "#0C141C",
          darkCard: "#131E29",
        },
      },
    },
  },
  plugins: [],
}

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
          light: "#ff8a80",
          DEFAULT: "#e53935",
          dark: "#b71c1c",
        },
      },
    },
  },
  plugins: [],
}

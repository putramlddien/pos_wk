/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./template/**/*.html", "./app/**/*.py", "./static/css/input.css"],
  theme: {
    extend: {
      fontFamily: {
        poppins: ["Poppins", "sans-serif"],
        yusei: ["Yusei Magic", "sans-serif"],
      },
      colors: {
        primary: "var(--color-primary)",
        secondary: "var(--color-secondary)",
        accent: "var(--color-accent)",
        status: "var(--color-status)",
        bg: "var(--color-bg)",
      },
    },
  },
  plugins: [],
};

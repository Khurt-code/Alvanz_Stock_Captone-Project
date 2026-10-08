/** @type {import('tailwindcss').Config} */
// Scans templates for utility classes and defines design tokens used by the CSS build script.
module.exports = {
  content: ["./templates/**/*.html"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

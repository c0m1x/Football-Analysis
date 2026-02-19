/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'club-blue': '#003C71',
        'club-red': '#C41E3A',
        'club-gold': '#FFD700',
      }
    },
  },
  plugins: [],
}

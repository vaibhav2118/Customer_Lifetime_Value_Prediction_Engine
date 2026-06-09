/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f5ff',
          100: '#e0eaff',
          200: '#c7d7ff',
          300: '#a3baff',
          400: '#7a94ff',
          500: '#5368ff', // Accent brand HSL color
          600: '#3c42ff',
          700: '#2c2aff',
          800: '#2320d4',
          900: '#1d1aa5',
        },
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

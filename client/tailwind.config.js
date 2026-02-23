/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          50:  '#f0f4ff',
          100: '#e0e9ff',
          200: '#c7d7fe',
          300: '#a5bbfc',
          400: '#8193f9',
          500: '#6470f3',
          600: '#4f52e7',
          700: '#3e3fcd',
          800: '#1e2a6e',
          900: '#1a2357',
          950: '#0f1535',
        },
        slate: {
          750: '#2d3a4f',
        }
      },
    },
  },
  plugins: [],
}

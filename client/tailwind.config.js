/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eefcf6',
          100: '#d7f7e9',
          200: '#b1eed5',
          300: '#7bddb8',
          400: '#41c397',
          500: '#1ea67b',
          600: '#148562',
          700: '#136a50',
          800: '#135441',
          900: '#124537',
          950: '#05271f',
        },
        navy: {
          800: '#0f172a',
          900: '#090d16',
          950: '#04070d'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      }
    },
  },
  plugins: [],
}

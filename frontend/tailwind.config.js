/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        title: ['Outfit', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#f5f6ff',
          100: '#ebedff',
          200: '#dbe0ff',
          300: '#c2cbff',
          400: '#9faaff',
          500: '#7580ff',
          600: '#6366f1',
          700: '#4f46e5',
          800: '#3f37c9',
          900: '#1e1b4b'
        }
      }
    }
  },
  plugins: []
}

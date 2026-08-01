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
        laser: {
          50: '#fff1f2',
          100: '#ffe4e6',
          400: '#fb7185',
          500: '#f43f5e',
          600: '#e11d48',
          700: '#be123c',
        },
        lab: {
          950: '#090d16',
          900: '#0f172a',
          850: '#152035',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glow-laser': '0 0 20px -3px rgba(244, 63, 94, 0.4)',
        'glow-cyan': '0 0 20px -3px rgba(6, 182, 212, 0.4)',
        'glow-emerald': '0 0 20px -3px rgba(16, 185, 129, 0.4)',
      }
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gov: {
          900: '#0a0f1e',
          800: '#0d1526',
          700: '#111d35',
          600: '#1a2744',
          500: '#1e3a5f',
        },
        risk: {
          low:      '#22c55e',
          moderate: '#f59e0b',
          high:     '#ef4444',
          extreme:  '#7c3aed',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}

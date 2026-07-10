/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: '#090a0f',
        panelBg: 'rgba(17, 20, 31, 0.7)',
        accentBlue: '#3b82f6',
        accentCyan: '#06b6d4',
        accentEmerald: '#10b981',
      }
    },
  },
  plugins: [],
}

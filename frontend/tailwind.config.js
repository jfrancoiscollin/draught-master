/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'board-dark': '#8B4513',
        'board-light': '#FFFFFF',
        'board-selected': '#D4A017',
        'board-legal': '#A0522D',
        'board-last': '#CD853F',
        'piece-white': '#FFFFFF',
        'piece-black': '#0a0a0a',
        'gold': '#d4a017',
        'brown': {
          400: '#C26030',
          500: '#A0522D',
          600: '#8B4513',
          700: '#6B3410',
          800: '#4A240B',
          900: '#2A1306',
        },
      },
    },
  },
  plugins: [],
}

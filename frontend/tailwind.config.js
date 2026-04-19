/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'board-dark': '#2d5a1b',
        'board-light': '#f0d9b5',
        'board-selected': '#f6f669',
        'board-legal': '#5d8a3c',
        'board-last': '#cdd16f',
        'piece-white': '#f5f5f5',
        'piece-black': '#1a1a1a',
        'gold': '#d4a017',
      },
    },
  },
  plugins: [],
}

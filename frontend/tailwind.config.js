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

        // Brand accent — soft warm sand (harmonized with the cream-and-black logo)
        'gold': '#C9B88D',

        // Primary action scale — warm taupe (replaces saturated saddle-brown)
        'brown': {
          400: '#9B8868',
          500: '#7E6D52',
          600: '#65573F',
          700: '#4D4230',
          800: '#352D20',
          900: '#1F1A12',
        },

        // Override Tailwind's stock `amber` palette with softer warm-sand tones
        // so the many `amber-*` references across the UI harmonize with the logo.
        amber: {
          50:  '#FAF5E7',
          100: '#F5EDD8',
          200: '#EFE3CB',
          300: '#E8DBC0',
          400: '#D9C89F',
          500: '#C5B385',
          600: '#A89770',
          700: '#876F4F',
          800: '#5C4A33',
          900: '#3A2E1F',
          950: '#1F1810',
        },

        // Soften the `yellow` palette similarly (used by stars, lesson highlights)
        yellow: {
          300: '#E8DBC0',
          400: '#D9C89F',
          500: '#C5B385',
          600: '#A89770',
        },
      },
    },
  },
  plugins: [],
}

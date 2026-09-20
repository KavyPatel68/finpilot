/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        canvas: {
          light: '#FAFAF9',
          dark: '#0B0B0F',
        },
        surface: {
          light: '#FFFFFF',
          dark: '#131318',
        },
        hairline: {
          light: '#E7E5E4',
          dark: '#232329',
        },
        content: {
          primary: {
            light: '#1C1917',
            dark: '#EDEDEF',
          },
          muted: {
            light: '#78716C',
            dark: '#8B8B95',
          },
        },
        accent: {
          lightText: '#4F46E5',
          darkText: '#818CF8',
          fill: '#6366F1',
        },
      },
    },
  },
  plugins: [],
}

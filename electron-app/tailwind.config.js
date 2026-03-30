module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        background: '#0F111A',
        surface: '#1E212B',
        primary: '#6366F1',
        secondary: '#A855F7',
        accent: '#EC4899',
        border: '#2D313E',
        textMain: '#F8FAFC',
        textMuted: '#94A3B8'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'Menlo', 'monospace'],
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography')
  ],
}

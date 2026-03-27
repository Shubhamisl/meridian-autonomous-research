/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Manrope"', 'sans-serif'],
        serif: ['"Newsreader"', 'serif'],
      },
      colors: {
        ink: '#0F172A',
        slate: '#1E293B',
        ivory: '#F8FAFC',
        paper: '#F6F1E8',
        teal: '#0F766E',
        'teal-soft': '#CCFBF1',
        amber: '#D97706',
        blue: '#2563EB',
        fog: '#CBD5E1',
        rose: '#B91C1C',
        white: '#FFFFFF',
        background: '#F8FAFC',
        surface: 'rgba(255, 255, 255, 0.84)',
        'surface-hover': 'rgba(255, 255, 255, 0.96)',
        border: 'rgba(15, 23, 42, 0.08)',
        accent: '#0F766E',
        'accent-light': '#2563EB',
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      boxShadow: {
        panel: '0 18px 48px rgba(15, 23, 42, 0.08)',
        soft: '0 10px 30px rgba(15, 23, 42, 0.06)',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}

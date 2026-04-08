/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base': '#0A0B14',
        'bg-surface': '#111827',
        'bg-elevated': '#1A2035',
        'border-subtle': 'rgba(255,255,255,0.07)',
        'border-default': 'rgba(255,255,255,0.12)',
        primary: '#6C5CE7',
        'primary-light': '#8B7CF6',
        accent: '#00CEC9',
        'accent-warm': '#E17055',
        'text-primary': '#F0F0F5',
        'text-secondary': '#9CA3AF',
        'text-muted': '#5B6278',
        success: '#00B894',
        warning: '#FDCB6E',
        danger: '#E17055',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '12px',
        badge: '6px',
        button: '8px',
      },
      width: {
        55: '220px',
      },
      maxWidth: {
        content: '1200px',
      },
      keyframes: {
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

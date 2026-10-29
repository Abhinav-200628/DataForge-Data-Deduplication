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
        navy: {
          bg: '#080D18',
          sidebar: '#0D1423',
          card: '#111B2D',
          cardHover: '#16233B',
          border: '#1C283F',
          borderHover: '#2A3C5E',
        },
        cyan: {
          accent: '#00F0FF',
          glow: 'rgba(0, 240, 255, 0.15)',
          DEFAULT: '#06B6D4',
        },
        violet: {
          accent: '#8B5CF6',
          glow: 'rgba(139, 92, 246, 0.15)',
        },
        brand: {
          success: '#10B981',
          warning: '#F59E0B',
          error: '#EF4444',
          text: '#F8FAFC',
          muted: '#94A3B8',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px -5px rgba(0, 240, 255, 0.25)',
        glowViolet: '0 0 20px -5px rgba(139, 92, 246, 0.25)',
        card: '0 4px 20px -2px rgba(0, 0, 0, 0.5)',
      }
    },
  },
  plugins: [],
}


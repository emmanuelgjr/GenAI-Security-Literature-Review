import defaultTheme from 'tailwindcss/defaultTheme';

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Geist Variable"', ...defaultTheme.fontFamily.sans],
        serif: ['"Newsreader Variable"', 'Georgia', ...defaultTheme.fontFamily.serif],
        mono: ['"Geist Mono Variable"', ...defaultTheme.fontFamily.mono],
      },
      colors: {
        // One accent: a muted teal. 600+ meet WCAG AA on white and on paper.
        primary: {
          50: '#eef7f6',
          100: '#d5ece9',
          200: '#aad8d3',
          300: '#74bdb6',
          400: '#409c95',
          500: '#23807a',
          600: '#176a65',
          700: '#135753',
          800: '#124744',
          900: '#103b39',
          950: '#082322',
        },
        // Warm grays throughout, so neutrals never mix warm and cool.
        gray: {
          50: '#fafaf9',
          100: '#f4f3f1',
          200: '#e7e5e2',
          300: '#d6d3cf',
          400: '#a8a29d',
          500: '#76706a',
          600: '#57524d',
          700: '#443f3b',
          800: '#2b2724',
          900: '#1c1917',
          950: '#0f0d0c',
        },
        paper: '#f7f6f2',
      },
      boxShadow: {
        // Shadows tinted with the warm ink color instead of pure black
        soft: '0 1px 2px rgb(28 25 23 / 0.04), 0 4px 16px -6px rgb(28 25 23 / 0.08)',
        lift: '0 2px 4px rgb(28 25 23 / 0.04), 0 12px 28px -10px rgb(28 25 23 / 0.16)',
      },
      keyframes: {
        rise: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        rise: 'rise 600ms cubic-bezier(0.22, 1, 0.36, 1) both',
      },
    },
  },
  plugins: [],
};

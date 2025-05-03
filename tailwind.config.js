/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
    "./static/**/*.css",
  ],
  theme: {
    extend: {
      fontFamily: {
        inknut: ['var(--font-inknut)'],
      },
      colors: {
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        primary: '#F5DEB3',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}; 
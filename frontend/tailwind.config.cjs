/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        'plan-comun': '#93F6E8',
        titulo: '#9966CC',
        major: '#B3A9E4',
        minor: '#13CDB2',
        ofg: '#355484',
        otro: '#D8D8D8'
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@headlessui/tailwindcss'),
    require('@tailwindcss/typography')
  ]
}

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}'
  ],
  safelist: [
    'bg-block-PC',
    'bg-place-holder',
    'bg-block-T',
    'bg-block-M',
    'bg-block-m',
    'bg-block-FG',
    'bg-block-'
  ],
  theme: {
    extend: {
      colors: {
        'block-PC': 'var(--blockPC)',
        'place-holder': 'var(--placeHolder)',
        'block-T': 'var(--titulo)',
        'block-M': 'var(--major)',
        'block-m': 'var(--minor)',
        'block-FG': 'var(--blockFG)',
        'block-': 'var(--otro)'
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@headlessui/tailwindcss'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/line-clamp')
  ]
}

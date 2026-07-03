import type { Config } from 'tailwindcss';
export default { darkMode: 'class', content: ['./index.html', './src/**/*.{ts,tsx}'], theme: { extend: { boxShadow: { glass: '0 20px 60px rgba(15,23,42,.16)' } } }, plugins: [] } satisfies Config;

/**
 * Tailwind CSS configuration for Espresso & Amber Bronze Theme.
 * School slug: acumen
 * Location: static/schools/acumen/js/tailwind.config.js
 */
tailwind.config = {
    darkMode: 'class',
    theme: {
        extend: {
            fontFamily: {
                sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
                mono: ['"JetBrains Mono"', 'monospace'],
            },
            colors: {
                brand: {
                    '50': '#fdf8f4',
                    '100': '#faeee4',
                    '200': '#f3d8c3',
                    '500': '#8a4f26',
                    '600': '#5c3317',
                    '700': '#46250f'
                },
                accent: {
                    '50': '#fffbeb',
                    '500': '#c27828',
                    '600': '#9a5b19'
                }
            },
            boxShadow: {
                soft: '0 4px 20px -2px rgba(15, 23, 42, 0.06)',
                hover: '0 12px 30px -4px rgba(15, 23, 42, 0.12)',
                glow: '0 0 25px -5px #5c331755',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(6px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideInRight: {
                    '0%': { opacity: '0', transform: 'translateX(24px)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                }
            },
            animation: {
                'fade-in': 'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
                'slide-in': 'slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
            }
        }
    }
};

/**
 * Tailwind CSS configuration for Royal Navy & Crimson Theme.
 * School slug: blale-international-school
 * Location: static/schools/blale-international-school/js/tailwind.config.js
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
                    '50': '#f0f7ff',
                    '100': '#e0effe',
                    '200': '#b9ddfd',
                    '500': '#2563eb',
                    '600': '#1e3a8a',
                    '700': '#172554'
                },
                accent: {
                    '50': '#fff1f2',
                    '500': '#f43f5e',
                    '600': '#e11d48'
                }
            },
            boxShadow: {
                soft: '0 4px 20px -2px rgba(15, 23, 42, 0.06)',
                hover: '0 12px 30px -4px rgba(15, 23, 42, 0.12)',
                glow: '0 0 25px -5px #1e3a8a55',
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

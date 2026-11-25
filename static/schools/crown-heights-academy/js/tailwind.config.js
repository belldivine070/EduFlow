/**
 * Tailwind CSS configuration for Sapphire Blue & Amber Theme.
 * School slug: crown-heights-academy
 * Location: static/schools/crown-heights-academy/js/tailwind.config.js
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
                    '50': '#eff6ff',
                    '100': '#dbeafe',
                    '200': '#bfdbfe',
                    '500': '#3b82f6',
                    '600': '#2563eb',
                    '700': '#1d4ed8'
                },
                accent: {
                    '50': '#fffbeb',
                    '500': '#f59e0b',
                    '600': '#d97706'
                }
            },
            boxShadow: {
                soft: '0 4px 20px -2px rgba(15, 23, 42, 0.06)',
                hover: '0 12px 30px -4px rgba(15, 23, 42, 0.12)',
                glow: '0 0 25px -5px #2563eb55',
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

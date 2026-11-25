/**
 * Tailwind CSS configuration for Forest Emerald & Gold Theme.
 * School slug: heritage-school
 * Location: static/schools/heritage-school/js/tailwind.config.js
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
                    '50': '#f0fdf4',
                    '100': '#dcfce7',
                    '200': '#bbf7d0',
                    '500': '#10b981',
                    '600': '#065f46',
                    '700': '#064e3b'
                },
                accent: {
                    '50': '#fefce8',
                    '500': '#eab308',
                    '600': '#d97706'
                }
            },
            boxShadow: {
                soft: '0 4px 20px -2px rgba(15, 23, 42, 0.06)',
                hover: '0 12px 30px -4px rgba(15, 23, 42, 0.12)',
                glow: '0 0 25px -5px #065f4655',
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

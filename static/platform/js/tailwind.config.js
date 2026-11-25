/**
 * Tailwind CSS configuration for the Platform Developer Control Plane.
 * Location: static/platform/js/tailwind.config.js
 *
 * Must be loaded AFTER the Tailwind CDN script.
 * Extends Tailwind with platform-specific design tokens:
 * - Custom font families (Plus Jakarta Sans, JetBrains Mono)
 * - Platform glow shadow (blue)
 */
tailwind.config = {
    darkMode: 'class',
    theme: {
        extend: {
            fontFamily: {
                sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
                mono: ['"JetBrains Mono"', 'monospace'],
            },
            boxShadow: {
                glow: '0 0 25px -5px rgba(59, 130, 246, 0.4)',
            },
        },
    },
};

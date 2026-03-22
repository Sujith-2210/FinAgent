/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Black & White Base
                black: '#000000',
                white: '#FFFFFF',

                // Neutral grays for subtle elements only
                neutral: {
                    50: '#FAFAFA',
                    100: '#F5F5F5',
                    200: '#E5E5E5',
                    300: '#D4D4D4',
                    400: '#A3A3A3',
                    500: '#737373',
                    600: '#525252',
                    700: '#404040',
                    800: '#262626',
                    900: '#171717',
                },

                // Teal Accent
                primary: {
                    50: '#F0FDFA',
                    100: '#CCFBF1',
                    200: '#99F6E4',
                    300: '#5EEAD4',
                    400: '#2DD4BF',
                    500: '#14B8A6',
                    600: '#0D9488',
                    700: '#0F766E',
                    800: '#115E59',
                    900: '#134E4A',
                },

                // Status
                success: '#22C55E',
                warning: '#EAB308',
                danger: '#EF4444',
                info: '#0D9488',
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
            boxShadow: {
                'brutal': '4px 4px 0px #000000',
                'brutal-lg': '8px 8px 0px #000000',
                'brutal-accent': '4px 4px 0px #0D9488',
            },
            animation: {
                'fade-in': 'fadeIn 0.25s ease-out',
                'spin': 'spin 0.8s linear infinite',
            },
            keyframes: {
                fadeIn: {
                    from: { opacity: '0', transform: 'translateY(10px)' },
                    to: { opacity: '1', transform: 'translateY(0)' },
                },
            },
        },
    },
    plugins: [],
}

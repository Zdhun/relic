import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                terminal: {
                    bg: "#0a0a0a",
                    text: "#e5e5e5",
                    accent: "#00ff9d",
                    dim: "#404040",
                    border: "#262626"
                }
            },
            fontFamily: {
                mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
            }
        },
    },
    plugins: [],
};
export default config;

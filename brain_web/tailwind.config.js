/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        aperture: {
          bg: "#0d0f12",
          panel: "#151920",
          border: "#2a3140",
          orange: "#c17a3a",
          blue: "#4a7fa5",
          text: "#c8d0dc",
          muted: "#6b7585",
        },
        hud: {
          bg: "#030810",
          cyan: "#3dd6ff",
          glow: "#1a8cff",
          grid: "#0a1a2e",
          panel: "rgba(6, 20, 40, 0.75)",
        },
      },
      boxShadow: {
        glow: "0 0 24px rgba(193, 122, 58, 0.25)",
        glowBlue: "0 0 24px rgba(74, 127, 165, 0.25)",
      },
    },
  },
  plugins: [],
};

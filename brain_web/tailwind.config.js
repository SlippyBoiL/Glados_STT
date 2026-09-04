/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        aperture: {
          bg: "#00050b",
          panel: "#001220",
          border: "#0a3a55",
          orange: "#c17a3a",
          blue: "#00F0FF",
          text: "#B8F4FF",
          muted: "#3a6a80",
        },
        hud: {
          bg: "#00050b",
          cyan: "#00F0FF",
          glow: "#3D9EFF",
          grid: "#001220",
          panel: "rgba(0, 18, 32, 0.72)",
        },
        jarvis: {
          bg: "#00050b",
          deep: "#001220",
          cyan: "#00F0FF",
          blue: "#3D9EFF",
          glass: "rgba(0, 18, 32, 0.55)",
        },
      },
      boxShadow: {
        glow: "0 0 24px rgba(193, 122, 58, 0.25)",
        glowBlue: "0 0 28px rgba(0, 240, 255, 0.35)",
        jarvis: "0 0 40px rgba(0, 240, 255, 0.12), inset 0 0 30px rgba(0, 240, 255, 0.04)",
      },
    },
  },
  plugins: [],
};

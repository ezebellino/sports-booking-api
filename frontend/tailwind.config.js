/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0F172A",
        mist: "#E2E8F0",
        panel: "#F8FAFC",
        accent: "#F97316",
        ocean: "#0F766E",
        skyline: "#0EA5E9"
      },
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      boxShadow: {
        soft: "0 12px 40px rgba(15, 23, 42, 0.12)"
      },
      backgroundImage: {
        hero: "radial-gradient(circle at top left, rgba(14,165,233,0.35), transparent 35%), radial-gradient(circle at top right, rgba(249,115,22,0.22), transparent 25%), linear-gradient(180deg, #f8fafc 0%, #eff6ff 100%)"
      }
    }
  },
  plugins: []
};

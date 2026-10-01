export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        space: {
          900: "#030712",
          800: "#050B14",
        },
        neon: {
          cyan: "#00f0ff",
          blue: "#00a8ff",
          amber: "#ffb703",
          red: "#ff003c",
        },
      },
      boxShadow: {
        glow: "0 0 15px rgba(0, 240, 255, 0.3)",
        "glow-lg": "0 0 25px rgba(0, 240, 255, 0.4)",
      },
      backdropBlur: {
        glass: "10px",
      },
    },
  },
  plugins: [],
};

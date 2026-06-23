import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RSMeans Cost Assistant",
  description:
    "Ask construction cost questions in plain language or by RSMeans line number.",
};

// Runs before first paint to set the `dark` class from the saved preference (or
// the OS setting), so there's no flash of the wrong theme on load.
const themeInit = `
(function () {
  try {
    var t = localStorage.getItem("theme");
    var dark = t === "dark" || (!t && window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (dark) document.documentElement.classList.add("dark");
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

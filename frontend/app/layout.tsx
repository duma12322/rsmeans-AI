import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RSMeans Cost Assistant",
  description:
    "Ask construction cost questions in plain language or by RSMeans line number.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

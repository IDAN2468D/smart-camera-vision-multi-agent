import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart Camera Vision Recognition | Multi-Agent AI",
  description: "Autonomous Multi-Agent Computer Vision System powered by Gemini 3.5 Flash Lite & MongoDB Atlas",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#070b14] text-slate-100 antialiased selection:bg-cyan-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}

import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agent Experts - Personal AI Business Agent",
  description: "Your personal AI business agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

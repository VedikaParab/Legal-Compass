import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LegalCompass Assistant",
  description: "Understand which criminal law applies to your situation — old IPC or new BNS — and what to do next.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Quorum — Production Incident Prevention",
  description: "AI memory layer that always knows your last agreed-upon safe state.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}

import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const title = "Zero Slop | Remove the AI accent from your writing";
const description =
  "Zero Slop is an open-source AI writing humanizer and anti-slop checker that scores machine-like writing patterns, rewrites drafts, and verifies factual fidelity.";

export const metadata: Metadata = {
  metadataBase: new URL("https://zero-slop.ai"),
  title,
  description,
  keywords: [
    "AI slop detector",
    "AI writing humanizer",
    "anti-slop writing tool",
    "remove AI writing patterns",
    "humanize AI content",
    "AI prose checker",
    "Zero Slop",
  ],
  applicationName: "Zero Slop",
  authors: [{ name: "Zero Slop contributors", url: "https://github.com/manavmishra/ZeroSlop" }],
  creator: "Zero Slop contributors",
  publisher: "Zero Slop",
  category: "writing software",
  alternates: { canonical: "/" },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "Zero Slop",
    title,
    description,
    images: [
      {
        url: "/og.png",
        width: 1731,
        height: 909,
        alt: "Zero Slop. Make AI writing sound like you.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: ["/og.png"],
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f3f4ef" },
    { media: "(prefers-color-scheme: dark)", color: "#111511" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );
}

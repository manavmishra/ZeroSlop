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

const title = "Zero Slop: AI Writing Humanizer & Anti-Slop Checker";
const description =
  "Score and rewrite AI-sounding prose without losing facts. Zero Slop is a free, open-source humanizer with local scoring and fidelity checks.";
const socialTitle = "Zero Slop: Remove the AI accent. Keep every fact.";
const socialDescription =
  "A free, open-source writing tool that scores AI-like patterns, rewrites the draft, and checks figures, names, quotes, and links.";

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
  referrer: "origin-when-cross-origin",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
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
    locale: "en_US",
    url: "/",
    siteName: "Zero Slop",
    title: socialTitle,
    description: socialDescription,
    images: [
      {
        url: "/og.jpg",
        width: 1200,
        height: 630,
        type: "image/jpeg",
        alt: "Zero Slop. Make AI writing sound like you.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: socialTitle,
    description: socialDescription,
    images: ["/og.jpg"],
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
      <head>
        <link
          rel="preload"
          as="image"
          href="/demo-384.avif"
          type="image/avif"
          media="(max-width: 767px)"
          fetchPriority="high"
        />
        <link
          rel="preload"
          as="image"
          href="/demo.avif"
          type="image/avif"
          media="(min-width: 768px)"
          fetchPriority="high"
        />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );
}

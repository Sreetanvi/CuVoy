import type { Metadata } from "next";
import {
  Caveat,
  Homemade_Apple,
  Permanent_Marker,
  Rock_Salt,
  Source_Sans_3,
  Special_Elite,
} from "next/font/google";

import { AppProviders } from "@/components/providers/AppProviders";
import "./globals.css";

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source-sans",
});

const permanentMarker = Permanent_Marker({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-permanent-marker",
});

const caveat = Caveat({
  subsets: ["latin"],
  variable: "--font-caveat",
});

const specialElite = Special_Elite({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-special-elite",
});

const homemadeApple = Homemade_Apple({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-homemade-apple",
});

const rockSalt = Rock_Salt({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-rock-salt",
});

export const metadata: Metadata = {
  title: "CuVoy — Curating One's Voyage",
  description:
    "Global AI travel planner. Natural-language request to a feasible, costed, explainable day-by-day itinerary.",
  metadataBase: new URL("https://cuvoy.vercel.app"),
  icons: {
    icon: [{ url: "/logo.png", type: "image/png" }],
    apple: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${sourceSans.variable} ${permanentMarker.variable} ${caveat.variable} ${specialElite.variable} ${homemadeApple.variable} ${rockSalt.variable}`}
    >
      <body className="min-h-dvh antialiased">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}

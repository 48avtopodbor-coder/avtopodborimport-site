import type { Metadata } from "next";
import { Unbounded, Manrope } from "next/font/google";
import "./globals.css";

const unbounded = Unbounded({
  subsets: ["latin", "cyrillic"],
  variable: "--font-unbounded",
  display: "swap",
});

const manrope = Manrope({
  subsets: ["latin", "cyrillic"],
  variable: "--font-manrope",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AVTOPODBOR IMPORT — Авто из Китая под ключ",
  description:
    "Подбор и ввоз новых автомобилей и авто с пробегом из Китая. Офисы во Владивостоке, Москве и Липецке. Цена под ключ с доставкой и растаможкой.",
  keywords: "авто из Китая, ввоз авто, автоподбор, Китай, пробег, новые авто",
  openGraph: {
    siteName: "AVTOPODBOR IMPORT",
    locale: "ru_RU",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ru"
      className={`${unbounded.variable} ${manrope.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}

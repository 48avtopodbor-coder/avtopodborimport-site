import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="ru">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Unbounded:wght@200..900&family=Manrope:wght@200..800&display=swap&subset=cyrillic,latin"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}

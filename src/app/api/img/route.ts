import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");

  if (!url) {
    return new NextResponse("Missing url parameter", { status: 400 });
  }

  // Разрешаем только che168 и связанные домены
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return new NextResponse("Invalid URL", { status: 400 });
  }

  const allowedHosts = [
    "che168.com",
    "img.che168.com",
    "imgcdn.che168.com",
    "pic.che168.com",
  ];
  const isAllowed = allowedHosts.some(
    (h) => parsed.hostname === h || parsed.hostname.endsWith("." + h)
  );

  if (!isAllowed) {
    return new NextResponse("URL not allowed", { status: 403 });
  }

  try {
    const response = await fetch(url, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        Referer: "https://www.che168.com/",
        Accept: "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
      },
      // 10 секунд таймаут
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      return new NextResponse("Failed to fetch image", {
        status: response.status,
      });
    }

    const contentType = response.headers.get("content-type") || "image/jpeg";
    const buffer = await response.arrayBuffer();

    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=86400", // кешируем в браузере на сутки
        "CDN-Cache-Control": "public, max-age=86400",
      },
    });
  } catch {
    return new NextResponse("Error fetching image", { status: 502 });
  }
}

import { NextRequest, NextResponse } from "next/server";

const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const IMAGE_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
  "image/avif",
  "image/apng",
]);

async function readBoundedImage(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  let size = 0;
  const chunks: Uint8Array[] = [];
  try {
    while (true) {
      const result = await reader.read();
      if (result.done) break;
      size += result.value.byteLength;
      if (size > MAX_IMAGE_BYTES) {
        await reader.cancel();
        return null;
      }
      chunks.push(result.value);
    }
  } finally {
    reader.releaseLock();
  }

  const image = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    image.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return image;
}

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");

  if (!url) {
    return new NextResponse("Missing url parameter", { status: 400 });
  }

  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return new NextResponse("Invalid URL", { status: 400 });
  }

  const allowedHosts = ["che168.com", "autoimg.cn"];
  const allowedHost = allowedHosts.some(
    (h) => parsed.hostname === h || parsed.hostname.endsWith("." + h),
  );

  if (
    !allowedHost ||
    parsed.protocol !== "https:" ||
    parsed.username ||
    parsed.password ||
    parsed.port
  ) {
    return new NextResponse("URL not allowed", { status: 403 });
  }

  try {
    const response = await fetch(parsed, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        Referer: "https://www.che168.com/",
        Accept: "image/avif,image/webp,image/apng,image/*;q=0.8",
      },
      redirect: "error",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(10_000)]),
    });

    if (!response.ok || !response.body) {
      await response.body?.cancel();
      return new NextResponse("Failed to fetch image", {
        status: response.status >= 400 ? response.status : 502,
      });
    }

    const contentType = response.headers.get("content-type")?.split(";")[0].trim().toLowerCase();
    if (!contentType || !IMAGE_TYPES.has(contentType)) {
      await response.body.cancel();
      return new NextResponse("Unsupported image type", { status: 415 });
    }
    if (Number(response.headers.get("content-length")) > MAX_IMAGE_BYTES) {
      await response.body.cancel();
      return new NextResponse("Image is too large", { status: 413 });
    }
    const image = await readBoundedImage(response.body);
    if (!image) return new NextResponse("Image is too large", { status: 413 });
    if (!image.byteLength) return new NextResponse("Empty image", { status: 502 });

    return new NextResponse(image, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=86400",
        "CDN-Cache-Control": "public, max-age=86400",
      },
    });
  } catch {
    return new NextResponse("Error fetching image", { status: 502 });
  }
}

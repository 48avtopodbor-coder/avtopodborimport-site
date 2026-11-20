"use client";

import { useState } from "react";

export default function ArrivalPhoto({ src, alt }: { src: string | null; alt: string }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  if (!src || src === failedSrc) {
    return (
      <div className="absolute inset-0 flex items-center justify-center text-gray-400 font-body text-sm">
        Нет фото
      </div>
    );
  }

  return (
    <img
      ref={(image) => {
        if (image?.complete && image.naturalWidth === 0) setFailedSrc(src);
      }}
      src={src}
      alt={alt}
      className="w-full h-full object-cover"
      onError={() => setFailedSrc(src)}
    />
  );
}

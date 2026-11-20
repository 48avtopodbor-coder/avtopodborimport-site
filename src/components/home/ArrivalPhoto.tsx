"use client";

import { useState } from "react";
import Link from "next/link";
import type { ReactNode } from "react";

export default function ArrivalPhoto({
  src,
  alt,
  href,
  fuel,
  children,
}: {
  src: string;
  alt: string;
  href: string;
  fuel: string | null;
  children: ReactNode;
}) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  if (src === failedSrc) return null;

  return (
    <Link
      href={href}
      className="group min-w-0 bg-graphite-800 rounded-xl overflow-hidden border border-white/5 hover:border-orange-500/20 transition-all duration-200"
    >
      <div className="aspect-[4/3] bg-graphite-700 relative overflow-hidden">
        <img
          ref={(image) => {
            if (image?.complete && image.naturalWidth === 0) setFailedSrc(src);
          }}
          src={src}
          alt={alt}
          className="w-full h-full object-cover"
          onError={() => setFailedSrc(src)}
        />
        {fuel && (
          <div className="absolute top-2 left-2">
            <span className="bg-graphite-900/80 text-gray-300 font-body text-xs px-2 py-1 rounded-full backdrop-blur">
              {fuel}
            </span>
          </div>
        )}
      </div>
      {children}
    </Link>
  );
}

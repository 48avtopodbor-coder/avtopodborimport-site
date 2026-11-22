"use client";

import { useState } from "react";

export default function BrandLogo({ name, path }: { name: string; path: string | null }) {
  const [broken, setBroken] = useState(false);
  return (
    <span className="flex size-11 shrink-0 items-center justify-center rounded-[10px] bg-white p-[7px] sm:size-16 sm:rounded-xl sm:p-2.5">
      {path && !broken ? (
        <img
          src={path}
          alt=""
          width={44}
          height={44}
          loading="eager"
          onError={() => setBroken(true)}
          className="size-full object-contain"
        />
      ) : (
        <span aria-hidden="true" className="font-heading text-2xl font-bold text-graphite-900">
          {name.charAt(0).toUpperCase()}
        </span>
      )}
    </span>
  );
}

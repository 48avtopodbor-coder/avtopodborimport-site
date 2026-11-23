"use client";
import { useState } from "react";
import Image from "next/image";
import type { Facet } from "@/lib/catalog-data";
export default function CatalogBrandLogo({ brand }: { brand: Facet }) {
  const [broken, setBroken] = useState(false);
  return (
    <span className="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-gray-100 p-1 text-xs font-bold text-graphite-900">
      {brand.logo && !broken ? (
        <Image
          src={brand.logo}
          width={24}
          height={24}
          alt={`Логотип ${brand.name}`}
          className="size-full object-contain"
          onError={() => setBroken(true)}
        />
      ) : (
        <span aria-label={`Марка ${brand.name}`}>{brand.name.slice(0, 1)}</span>
      )}
    </span>
  );
}

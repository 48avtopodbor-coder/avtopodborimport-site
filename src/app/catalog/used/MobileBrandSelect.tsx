"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

export default function MobileBrandSelect({
  value,
  children,
}: {
  value: string;
  children: ReactNode;
}) {
  const router = useRouter();

  return (
    <label className="mb-4 block lg:hidden">
      <span className="mb-2 block font-body text-sm text-gray-400">Марка автомобиля</span>
      <select
        key={value}
        defaultValue={value}
        onChange={(event) => router.push(event.currentTarget.value)}
        className="min-h-11 w-full rounded-xl border border-white/10 bg-graphite-800 px-3 py-2 font-body text-white focus-visible:outline-orange-400"
      >
        {children}
      </select>
    </label>
  );
}

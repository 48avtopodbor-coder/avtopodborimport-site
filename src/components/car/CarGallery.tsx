"use client";

import { useState } from "react";

interface CarGalleryProps {
  photos: string[];
  alt: string;
}

export default function CarGallery({ photos, alt }: CarGalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const activePhoto = photos[activeIndex];

  return (
    <section aria-label="Фотографии автомобиля">
      <div className="relative mb-3 aspect-[4/3] overflow-hidden rounded-xl bg-graphite-800">
        {activePhoto ? (
          <img
            key={activePhoto}
            src={activePhoto}
            alt={`${alt} — фото ${activeIndex + 1}`}
            className="h-full w-full object-cover"
            loading="eager"
            fetchPriority={activeIndex === 0 ? "high" : "auto"}
            decoding="async"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-600">
            <svg className="h-20 w-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        )}
      </div>

      {photos.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1" aria-label="Выбрать фото">
          {photos.map((src, index) => (
            <button
              key={src}
              type="button"
              aria-label={`Показать фото ${index + 1}`}
              aria-pressed={activeIndex === index}
              onClick={() => setActiveIndex(index)}
              className={`h-16 w-20 shrink-0 overflow-hidden rounded-lg border-2 bg-graphite-800 transition-opacity ${
                activeIndex === index
                  ? "border-orange-400 opacity-100"
                  : "border-transparent opacity-70 hover:opacity-100"
              }`}
            >
              <img
                src={src}
                alt=""
                className="h-full w-full object-cover"
                loading="lazy"
                decoding="async"
              />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

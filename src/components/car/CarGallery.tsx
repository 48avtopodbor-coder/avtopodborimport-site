"use client";

import { useRef, useState } from "react";
import Image from "next/image";
import PhotoLightbox from "./PhotoLightbox";

interface CarGalleryProps {
  photos: string[];
  alt: string;
}

export default function CarGallery({ photos, alt }: CarGalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const openerRef = useRef<HTMLButtonElement | null>(null);
  const activePhoto = photos[activeIndex];

  function openLightbox(index: number, opener: HTMLButtonElement) {
    openerRef.current = opener;
    setLightboxIndex(index);
  }

  function closeLightbox() {
    setLightboxIndex(null);
    requestAnimationFrame(() => openerRef.current?.focus());
  }

  return (
    <section aria-label="Фотографии автомобиля">
      <div className="relative mb-3 aspect-[4/3] overflow-hidden rounded-xl bg-graphite-800">
        {activePhoto ? (
          <>
            <button
              type="button"
              aria-label={`Открыть фото ${activeIndex + 1} на весь экран`}
              onClick={(event) => openLightbox(activeIndex, event.currentTarget)}
              className="relative block h-full w-full cursor-zoom-in"
            >
              <Image
                key={activePhoto}
                src={activePhoto}
                alt={`${alt} — фото ${activeIndex + 1}`}
                fill
                sizes="(max-width: 1024px) 100vw, 50vw"
                unoptimized
                className="object-cover"
                loading={activeIndex === 0 ? "eager" : "lazy"}
                fetchPriority={activeIndex === 0 ? "high" : "auto"}
              />
            </button>
            <button
              type="button"
              onClick={(event) => openLightbox(0, event.currentTarget)}
              className="absolute bottom-3 right-3 z-10 flex min-h-11 items-center rounded-full bg-black/75 px-4 text-sm font-semibold text-white backdrop-blur-sm hover:bg-black/90"
            >
              Все фото · {photos.length}
            </button>
          </>
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-500">
            Фото пока нет
          </div>
        )}
      </div>

      {photos.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1" aria-label="Выбрать фото">
          {photos.map((src, index) => (
            <button
              key={`${src}-${index}`}
              type="button"
              aria-label={`Открыть фото ${index + 1} на весь экран`}
              aria-current={activeIndex === index ? "true" : undefined}
              onClick={(event) => {
                setActiveIndex(index);
                openLightbox(index, event.currentTarget);
              }}
              className={`relative h-16 w-20 shrink-0 overflow-hidden rounded-lg border-2 bg-graphite-800 transition-opacity ${
                activeIndex === index
                  ? "border-orange-400 opacity-100"
                  : "border-transparent opacity-70 hover:opacity-100"
              }`}
            >
              <Image src={src} alt="" fill sizes="80px" unoptimized className="object-cover" />
            </button>
          ))}
        </div>
      )}

      {lightboxIndex !== null && (
        <PhotoLightbox
          photos={photos}
          initialIndex={lightboxIndex}
          title={alt}
          onClose={closeLightbox}
        />
      )}
    </section>
  );
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import Lightbox, { type ZoomRef } from "yet-another-react-lightbox";
import Zoom from "yet-another-react-lightbox/plugins/zoom";
import "yet-another-react-lightbox/styles.css";
import styles from "./PhotoLightbox.module.css";

interface PhotoLightboxProps {
  photos: string[];
  initialIndex: number;
  title: string;
  onClose: () => void;
}

export default function PhotoLightbox({
  photos,
  initialIndex,
  title,
  onClose,
}: PhotoLightboxProps) {
  const [index, setIndex] = useState(initialIndex);
  const [zoomed, setZoomed] = useState(false);
  const zoomRef = useRef<ZoomRef>(null);
  const [thumbnailsVisible, setThumbnailsVisible] = useState(true);
  const stripRef = useRef<HTMLDivElement>(null);
  const selectedRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const strip = stripRef.current;
    const selected = selectedRef.current;
    if (strip && selected)
      strip.scrollTo({
        left: selected.offsetLeft - (strip.clientWidth - selected.clientWidth) / 2,
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
      });
  }, [index, thumbnailsVisible]);
  const slides = useMemo(
    () => photos.map((src, photoIndex) => ({ src, alt: `${title} — фото ${photoIndex + 1}` })),
    [photos, title],
  );

  if (!photos.length) return null;

  return (
    <Lightbox
      open
      close={onClose}
      index={index}
      slides={slides}
      plugins={[Zoom]}
      className={styles.viewer}
      portal={{ container: { "aria-label": `Фотографии автомобиля ${title}` } }}
      carousel={{
        preload: 1,
        padding: 0,
        spacing: "12%",
        imageFit: "contain",
        imageProps: { decoding: "async" },
      }}
      controller={{ aria: true, closeOnPullDown: !zoomed, closeOnBackdropClick: false }}
      zoom={{ ref: zoomRef, maxZoomPixelRatio: 2, zoomInMultiplier: 2, scrollToZoom: true }}
      animation={{ fade: 180, swipe: 300, zoom: 250 }}
      labels={{
        "Photo gallery": "Фотогалерея",
        Slide: "Снимок",
        Carousel: "Галерея",
        Lightbox: `Фотографии автомобиля ${title}`,
        "{index} of {total}": "{index} из {total}",
        Close: "Закрыть",
        Next: "Вперёд",
        Previous: "Назад",
        "Zoom in": "Приблизить",
        "Zoom out": "Отдалить",
      }}
      toolbar={{
        buttons: [
          <div key="title" className={styles.titleBlock}>
            <strong className={styles.title} title={title}>
              {title}
            </strong>
          </div>,
          <span key="counter" className={styles.counter} aria-live="polite">
            {index + 1} / {photos.length}
          </span>,
          "close",
        ],
      }}
      render={{
        buttonPrev: photos.length < 2 ? () => null : undefined,
        buttonNext: photos.length < 2 ? () => null : undefined,
        iconError: () => <span className={styles.error}>Не удалось загрузить фото</span>,
        controls: () => (
          <>
            <p className={styles.hint}>
              <span className={styles.desktopHint}>Двойной клик — приблизить</span>
              <span className={styles.mobileHint}>
                Два пальца — приблизить · касание — миниатюры
              </span>
            </p>
            {photos.length > 1 && (
              <div
                ref={stripRef}
                className={`${styles.strip} ${thumbnailsVisible ? "" : styles.hiddenStrip}`}
                aria-label="Миниатюры фотографий"
              >
                {photos.map((src, photoIndex) => (
                  <button
                    key={`${src}-${photoIndex}`}
                    ref={index === photoIndex ? selectedRef : undefined}
                    type="button"
                    aria-label={`Показать фото ${photoIndex + 1}`}
                    aria-current={index === photoIndex ? "true" : undefined}
                    className={`${styles.thumbnail} ${index === photoIndex ? styles.selected : ""}`}
                    onClick={() => setIndex(photoIndex)}
                  >
                    <Image
                      src={src}
                      alt=""
                      fill
                      sizes="84px"
                      unoptimized
                      loading={photoIndex < 4 ? "eager" : "lazy"}
                      decoding="async"
                      className={styles.thumbImage}
                    />
                  </button>
                ))}
              </div>
            )}
          </>
        ),
      }}
      on={{
        entered: () => {
          const strip = stripRef.current;
          const selected = selectedRef.current;
          if (strip && selected)
            strip.scrollTo({
              left: selected.offsetLeft - (strip.clientWidth - selected.clientWidth) / 2,
            });
        },
        view: ({ index: current }) => setIndex(current),
        zoom: ({ zoom }) => setZoomed(zoom > 1.01),
        click: () => {
          if (
            window.matchMedia("(max-width: 600px)").matches &&
            (zoomRef.current?.zoom ?? 1) <= 1.01
          ) {
            setThumbnailsVisible((visible) => !visible);
          }
        },
      }}
    />
  );
}

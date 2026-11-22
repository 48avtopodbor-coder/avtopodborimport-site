"use client";

import Image from "next/image";
import { useEffect, useRef, useState, useSyncExternalStore, type PointerEvent } from "react";
import { createPortal } from "react-dom";
import styles from "./PhotoLightbox.module.css";

interface PhotoLightboxProps {
  photos: string[];
  initialIndex: number;
  title: string;
  onClose: () => void;
}

interface Gesture {
  pointerId: number;
  x: number;
  y: number;
  direction: "horizontal" | "vertical" | null;
}

export default function PhotoLightbox({
  photos,
  initialIndex,
  title,
  onClose,
}: PhotoLightboxProps) {
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const [index, setIndex] = useState(initialIndex);
  const [controlsVisible, setControlsVisible] = useState(true);
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const stripRef = useRef<HTMLDivElement>(null);
  const thumbnailRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const gestureRef = useRef<Gesture | null>(null);

  useEffect(() => {
    const scrollY = window.scrollY;
    const previous = {
      position: document.body.style.position,
      top: document.body.style.top,
      left: document.body.style.left,
      right: document.body.style.right,
      width: document.body.style.width,
    };
    document.body.style.position = "fixed";
    document.body.style.top = `-${scrollY}px`;
    document.body.style.left = "0";
    document.body.style.right = "0";
    document.body.style.width = "100%";
    requestAnimationFrame(() => dialogRef.current?.focus());

    return () => {
      Object.assign(document.body.style, previous);
      window.scrollTo(0, scrollY);
    };
  }, []);

  useEffect(() => {
    if (photos.length < 2) return;
    const previous = (index - 1 + photos.length) % photos.length;
    const next = (index + 1) % photos.length;
    for (const neighbor of [previous, next]) {
      const preload = new window.Image();
      preload.src = photos[neighbor];
    }
  }, [index, photos]);

  useEffect(() => {
    const strip = stripRef.current;
    const thumbnail = thumbnailRefs.current[index];
    if (!strip || !thumbnail) return;
    strip.scrollTo({
      left:
        thumbnail.offsetLeft - strip.offsetLeft - (strip.clientWidth - thumbnail.clientWidth) / 2,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
  }, [index, mounted, controlsVisible]);

  function move(step: number) {
    setIndex((current) => (current + step + photos.length) % photos.length);
    setFailedSource(null);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    } else if (event.key === "ArrowLeft" && photos.length > 1) {
      event.preventDefault();
      move(-1);
    } else if (event.key === "ArrowRight" && photos.length > 1) {
      event.preventDefault();
      move(1);
    } else if (event.key === "Home") {
      event.preventDefault();
      setIndex(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setIndex(photos.length - 1);
    } else if (event.key === "Tab") {
      const buttons = Array.from(
        dialogRef.current?.querySelectorAll<HTMLButtonElement>("button") ?? [],
      ).filter(
        (button) =>
          button.getClientRects().length > 0 && getComputedStyle(button).visibility === "visible",
      );
      const first = buttons[0];
      const last = buttons.at(-1);
      if (
        event.shiftKey &&
        (document.activeElement === first || document.activeElement === dialogRef.current)
      ) {
        event.preventDefault();
        last?.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last || document.activeElement === dialogRef.current)
      ) {
        event.preventDefault();
        first?.focus();
      }
    }
  }

  function handlePointerDown(event: PointerEvent<HTMLButtonElement>) {
    if (event.pointerType === "mouse") return;
    gestureRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      direction: null,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<HTMLButtonElement>) {
    const start = gestureRef.current;
    if (!start || start.pointerId !== event.pointerId || start.direction) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (Math.max(Math.abs(dx), Math.abs(dy)) > 12) {
      start.direction = Math.abs(dx) > Math.abs(dy) ? "horizontal" : "vertical";
    }
  }

  function handlePointerUp(event: PointerEvent<HTMLButtonElement>) {
    const start = gestureRef.current;
    gestureRef.current = null;
    if (!start || start.pointerId !== event.pointerId) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 45) {
      setControlsVisible((visible) => !visible);
      return;
    }
    if (start.direction === "horizontal") {
      if (photos.length > 1) move(dx < 0 ? 1 : -1);
    } else if (start.direction === "vertical" && dy > 90) {
      onClose();
    }
  }

  if (!mounted || photos.length === 0) return null;
  const source = photos[index];

  return createPortal(
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-label={`Фотографии автомобиля ${title}`}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
      className={styles.dialog}
    >
      <header className={`${styles.header} ${controlsVisible ? "" : styles.mobileHidden}`}>
        <div className={styles.titleBlock}>
          <strong className={styles.title} title={title}>
            {title}
          </strong>
          <span className={styles.mobileCount}>
            {index + 1} / {photos.length}
          </span>
        </div>
        <div className={styles.headerActions}>
          <span className={styles.desktopCount}>
            {index + 1} / {photos.length}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className={styles.roundButton}
          >
            <span aria-hidden="true">×</span>
          </button>
        </div>
      </header>

      <div className={styles.photoArea}>
        {photos.length > 1 && (
          <button
            type="button"
            onClick={() => move(-1)}
            aria-label="Назад"
            className={`${styles.roundButton} ${styles.previous}`}
          >
            <span aria-hidden="true">‹</span>
          </button>
        )}
        <button
          type="button"
          aria-label="Показать или скрыть панель фотографий"
          className={styles.photoButton}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={() => {
            gestureRef.current = null;
          }}
        >
          {failedSource === source ? (
            <span className={styles.failed}>Не удалось загрузить фото</span>
          ) : (
            <Image
              key={source}
              src={source}
              alt={`${title} — фото ${index + 1}`}
              fill
              sizes="100vw"
              unoptimized={source.includes("/photos/")}
              loading="eager"
              fetchPriority="high"
              className={styles.photo}
              onError={() => setFailedSource(source)}
            />
          )}
        </button>
        {photos.length > 1 && (
          <button
            type="button"
            onClick={() => move(1)}
            aria-label="Вперёд"
            className={`${styles.roundButton} ${styles.next}`}
          >
            <span aria-hidden="true">›</span>
          </button>
        )}
      </div>

      {photos.length > 1 && (
        <div
          className={`${styles.strip} ${controlsVisible ? "" : styles.mobileHidden}`}
          ref={stripRef}
          aria-label="Миниатюры фотографий"
        >
          {photos.map((src, photoIndex) => (
            <button
              key={`${src}-${photoIndex}`}
              ref={(element) => {
                thumbnailRefs.current[photoIndex] = element;
              }}
              type="button"
              aria-label={`Показать фото ${photoIndex + 1}`}
              aria-current={index === photoIndex ? "true" : undefined}
              onClick={() => {
                setIndex(photoIndex);
                setFailedSource(null);
              }}
              className={`${styles.thumbnail} ${index === photoIndex ? styles.selected : ""}`}
            >
              <Image
                src={src}
                alt=""
                fill
                sizes="84px"
                unoptimized={src.includes("/photos/")}
                loading="lazy"
                className={styles.thumbImage}
              />
            </button>
          ))}
        </div>
      )}
    </div>,
    document.body,
  );
}

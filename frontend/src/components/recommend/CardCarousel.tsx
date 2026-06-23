"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type KeyboardEvent,
} from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface Props<T> {
  items: T[];
  getItemKey: (item: T, index: number) => string;
  /** When this value changes, carousel resets to the first slide. */
  resetToken?: string | number;
  dimmed?: boolean;
  /** Sync carousel position from parent (e.g. map click). */
  externalActiveIndex?: number;
  onActiveIndexChange?: (index: number) => void;
  renderItem: (item: T, index: number, isActive: boolean) => ReactNode;
  className?: string;
}

export default function CardCarousel<T>({
  items,
  getItemKey,
  resetToken,
  dimmed = false,
  externalActiveIndex,
  onActiveIndexChange,
  renderItem,
  className = "",
}: Props<T>) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const slideRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const scrollRafRef = useRef<number | null>(null);

  const clampIndex = useCallback(
    (index: number) => Math.max(0, Math.min(items.length - 1, index)),
    [items.length]
  );

  const scrollToIndex = useCallback(
    (index: number, behavior: ScrollBehavior = "smooth") => {
      const clamped = clampIndex(index);
      const slide = slideRefs.current[clamped];
      if (slide) {
        slide.scrollIntoView({ behavior, inline: "center", block: "nearest" });
      }
      setActiveIndex(clamped);
      onActiveIndexChange?.(clamped);
    },
    [clampIndex, onActiveIndexChange]
  );

  const goPrev = useCallback(() => {
    scrollToIndex(activeIndex - 1);
  }, [activeIndex, scrollToIndex]);

  const goNext = useCallback(() => {
    scrollToIndex(activeIndex + 1);
  }, [activeIndex, scrollToIndex]);

  const syncActiveFromScroll = useCallback(() => {
    const container = scrollRef.current;
    if (!container || items.length === 0) return;

    const center = container.scrollLeft + container.clientWidth / 2;
    let closest = 0;
    let minDist = Infinity;

    slideRefs.current.forEach((slide, index) => {
      if (!slide) return;
      const slideCenter = slide.offsetLeft + slide.offsetWidth / 2;
      const dist = Math.abs(slideCenter - center);
      if (dist < minDist) {
        minDist = dist;
        closest = index;
      }
    });

    setActiveIndex(closest);
    onActiveIndexChange?.(closest);
  }, [items.length, onActiveIndexChange]);

  const handleScroll = useCallback(() => {
    if (scrollRafRef.current != null) return;
    scrollRafRef.current = window.requestAnimationFrame(() => {
      scrollRafRef.current = null;
      syncActiveFromScroll();
    });
  }, [syncActiveFromScroll]);

  useEffect(() => {
    return () => {
      if (scrollRafRef.current != null) {
        window.cancelAnimationFrame(scrollRafRef.current);
      }
    };
  }, []);

  useEffect(() => {
    slideRefs.current = slideRefs.current.slice(0, items.length);
    setActiveIndex(0);
    const container = scrollRef.current;
    if (container) {
      container.scrollTo({ left: 0, behavior: "auto" });
    }
  }, [resetToken, items.length]);

  useEffect(() => {
    if (items.length === 0) {
      setActiveIndex(0);
      return;
    }
    if (activeIndex > items.length - 1) {
      scrollToIndex(items.length - 1, "auto");
    }
  }, [activeIndex, items.length, scrollToIndex]);

  useEffect(() => {
    if (
      externalActiveIndex == null ||
      externalActiveIndex < 0 ||
      externalActiveIndex >= items.length
    ) {
      return;
    }
    if (externalActiveIndex !== activeIndex) {
      scrollToIndex(externalActiveIndex);
    }
  }, [externalActiveIndex, activeIndex, items.length, scrollToIndex]);

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      goPrev();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      goNext();
    }
  };

  if (items.length === 0) return null;

  const canGoPrev = activeIndex > 0;
  const canGoNext = activeIndex < items.length - 1;

  return (
    <div
      className={`flex flex-col gap-3 min-h-0 ${className}`}
      role="region"
      aria-roledescription="carousel"
      aria-label="推荐卡片"
    >
      <div className="relative flex-1 min-h-[280px] flex items-center">
        <div
          ref={scrollRef}
          tabIndex={0}
          onKeyDown={handleKeyDown}
          onScroll={handleScroll}
          className={`card-carousel-track flex h-full w-full overflow-x-auto overflow-y-hidden snap-x snap-mandatory scroll-smooth outline-none ${
            dimmed ? "opacity-70 pointer-events-none" : ""
          }`}
          aria-live="polite"
        >
          {items.map((item, index) => {
            const isActive = index === activeIndex;
            return (
              <div
                key={getItemKey(item, index)}
                ref={(el) => {
                  slideRefs.current[index] = el;
                }}
                className={`card-carousel-slide snap-center shrink-0 flex items-stretch ${
                  items.length === 1 ? "!w-full !max-w-[420px] !mx-auto" : ""
                }`}
                aria-hidden={!isActive}
              >
                <div
                  className={`card-carousel-card w-full transition-all duration-300 ease-out ${
                    isActive
                      ? "scale-100 opacity-100"
                      : "scale-[0.92] opacity-55"
                  }`}
                >
                  {renderItem(item, index, isActive)}
                </div>
              </div>
            );
          })}
        </div>

        {items.length > 1 && (
          <>
            <button
              type="button"
              onClick={goPrev}
              disabled={!canGoPrev || dimmed}
              aria-label="上一张"
              className="absolute left-1 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full flex items-center justify-center shadow-md transition-opacity disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90"
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={goNext}
              disabled={!canGoNext || dimmed}
              aria-label="下一张"
              className="absolute right-1 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full flex items-center justify-center shadow-md transition-opacity disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90"
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                color: "var(--text-secondary)",
              }}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </>
        )}
      </div>

      {items.length > 1 && (
        <div className="flex flex-col items-center gap-2 shrink-0 pb-1">
          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            {activeIndex + 1} / {items.length}
          </span>
          <div className="flex items-center gap-1.5" role="tablist" aria-label="卡片指示器">
            {items.map((item, index) => (
              <button
                key={getItemKey(item, index)}
                type="button"
                role="tab"
                aria-selected={index === activeIndex}
                aria-label={`第 ${index + 1} 张卡片`}
                onClick={() => scrollToIndex(index)}
                disabled={dimmed}
                className="rounded-full transition-all disabled:opacity-40"
                style={{
                  width: index === activeIndex ? 16 : 6,
                  height: 6,
                  background:
                    index === activeIndex ? "var(--accent)" : "var(--border)",
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

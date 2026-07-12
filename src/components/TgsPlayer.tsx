import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import pakoUrl from '../lib/tgsticker/pako-inflate.min.js?url';
import tgstickerUrl from '../lib/tgsticker/tgsticker.js?url';
import rlottieRuntimeUrl from '../lib/tgsticker/rlottie-wasm.js?url';
import rlottieWasmUrl from '../lib/tgsticker/rlottie-wasm.wasm?url';
import tgstickerWorkerUrl from '../lib/tgsticker/tgsticker-worker.js?url';

declare global {
  interface Window {
    RLottie?: {
      init: (el: HTMLElement, opts?: Record<string, unknown>) => void;
      destroy: (el: HTMLElement) => void;
    };
    RLottieWorkerUrl?: string;
  }
}

type TgsPictureElement = HTMLPictureElement & { rlPlayer?: unknown };

let rlottiePromise: Promise<void> | null = null;
const ANIMATION_FALLBACK_TIMEOUT_MS = 5000;

function loadRLottie(): Promise<void> {
  if (window.RLottie) return Promise.resolve();

  if (!rlottiePromise) {
    rlottiePromise = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      const workerParams = new URLSearchParams({
        runtime: rlottieRuntimeUrl,
        wasm: rlottieWasmUrl,
        pako: pakoUrl,
      });
      window.RLottieWorkerUrl = `${tgstickerWorkerUrl}?${workerParams}`;
      script.src = tgstickerUrl;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('RLottie load failed'));
      document.head.appendChild(script);
    });
  }

  return rlottiePromise;
}

export interface TgsHandle {
  playAnimation(src: string): Promise<void>;
  clearAnimation(): void;
}

function syncPlayerCanvas(picture: HTMLPictureElement) {
  const canvas = picture.querySelector('canvas');
  if (!canvas) return;

  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.display = 'block';
  canvas.style.position = 'absolute';
  canvas.style.inset = '0';
}

function resetPlayer(picture: TgsPictureElement) {
  window.RLottie?.destroy(picture);
  picture.querySelectorAll('canvas').forEach((canvas) => canvas.remove());
  delete picture.rlPlayer;
}

function waitForAnimationEnd(picture: HTMLPictureElement): Promise<void> {
  return new Promise<void>((resolve) => {
    let finished = false;

    const finish = () => {
      if (finished) return;
      finished = true;
      picture.removeEventListener('tg:pause', onPause);
      window.clearTimeout(timeoutId);
      resolve();
    };

    const onPause = () => {
      finish();
    };

    const timeoutId = window.setTimeout(finish, ANIMATION_FALLBACK_TIMEOUT_MS);
    picture.addEventListener('tg:pause', onPause, { once: true });
  });
}

export const TgsPlayer = forwardRef<TgsHandle, { size?: number }>(({ size }, ref) => {
  const pictureRef = useRef<HTMLPictureElement>(null);
  const sourceRef = useRef<HTMLSourceElement>(null);

  useImperativeHandle(ref, () => ({
    clearAnimation(): void {
      const picture = pictureRef.current;
      const source = sourceRef.current;
      if (!picture || !source) return;

      resetPlayer(picture);
      source.setAttribute('srcset', '');
    },
    async playAnimation(src: string): Promise<void> {
      await loadRLottie();
      const picture = pictureRef.current;
      const source = sourceRef.current;
      if (!picture || !source || !window.RLottie) return;

      resetPlayer(picture);
      source.setAttribute('srcset', src);

      const animationEnd = waitForAnimationEnd(picture);
      window.RLottie!.init(picture, { playUntilEnd: true });
      requestAnimationFrame(() => syncPlayerCanvas(picture));
      await animationEnd;
    },
  }), []);

  useEffect(() => {
    const picture = pictureRef.current;
    if (!picture) return;

    const observer = new MutationObserver(() => syncPlayerCanvas(picture));
    observer.observe(picture, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      resetPlayer(picture);
    };
  }, []);

  return (
    <picture
      ref={pictureRef}
      style={{
        width: size ?? '100%',
        height: size ?? '100%',
        display: 'block',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <source ref={sourceRef} type="application/x-tgsticker" srcSet="" />
      <img alt="" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==" style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', opacity: 0 }} />
    </picture>
  );
});

TgsPlayer.displayName = 'TgsPlayer';

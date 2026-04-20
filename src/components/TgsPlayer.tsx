import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';

declare global {
  interface Window {
    RLottie?: {
      init: (el: HTMLElement, opts?: Record<string, unknown>) => void;
      destroy: (el: HTMLElement) => void;
    };
  }
}

let rlottiePromise: Promise<void> | null = null;

function loadRLottie(): Promise<void> {
  if (window.RLottie) return Promise.resolve();

  if (!rlottiePromise) {
    rlottiePromise = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = '/tgsticker/tgsticker.js';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('RLottie load failed'));
      document.head.appendChild(script);
    });
  }

  return rlottiePromise;
}

export interface TgsHandle {
  playAnimation(src: string): Promise<void>;
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

export const TgsPlayer = forwardRef<TgsHandle, { size?: number }>(({ size = 180 }, ref) => {
  const pictureRef = useRef<HTMLPictureElement>(null);
  const sourceRef = useRef<HTMLSourceElement>(null);

  useImperativeHandle(ref, () => ({
    async playAnimation(src: string): Promise<void> {
      await loadRLottie();
      const picture = pictureRef.current;
      const source = sourceRef.current;
      if (!picture || !source || !window.RLottie) return;

      window.RLottie.destroy(picture);
      source.setAttribute('srcset', src);

      await new Promise<void>((resolve) => {
        const onPause = () => {
          picture.removeEventListener('tg:pause', onPause);
          resolve();
        };

        picture.addEventListener('tg:pause', onPause);
        window.RLottie!.init(picture, { playUntilEnd: true });
        requestAnimationFrame(() => syncPlayerCanvas(picture));
      });
    },
  }), []);

  useEffect(() => {
    const picture = pictureRef.current;
    if (!picture) return;

    const observer = new MutationObserver(() => syncPlayerCanvas(picture));
    observer.observe(picture, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      if (window.RLottie) {
        window.RLottie.destroy(picture);
      }
    };
  }, []);

  return (
    <picture
      ref={pictureRef}
      style={{
        width: size,
        height: size,
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

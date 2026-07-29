import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from 'react';
import pakoUrl from '../lib/tgsticker/pako-inflate.min.js?url';
import tgstickerUrl from '../lib/tgsticker/tgsticker.js?url';
import rlottieRuntimeUrl from '../lib/tgsticker/rlottie-wasm.js?url';
import rlottieWasmUrl from '../lib/tgsticker/rlottie-wasm.wasm?url';
import tgstickerWorkerUrl from '../lib/tgsticker/tgsticker-worker.js?url';
import { preferredTgsFps } from '@/lib/motion';

declare global {
  interface Window {
    RLottie?: {
      init: (el: HTMLElement, opts?: Record<string, unknown>) => void;
      destroy: (el: HTMLElement) => void;
      play: (el: HTMLElement, reset?: boolean) => void;
      pause: (el: HTMLElement) => void;
      destroyWorkers?: () => void;
    };
    RLottieWorkerUrl?: string;
  }
}

type TgsPictureElement = HTMLPictureElement & { rlPlayer?: unknown };

let rlottiePromise: Promise<void> | null = null;
let mountedTgsPlayers = 0;
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

function nextFrame(): Promise<void> {
  return new Promise(resolve => requestAnimationFrame(() => resolve()));
}

function waitForCanvas(picture: HTMLPictureElement, timeoutMs = 1200): Promise<boolean> {
  return new Promise(resolve => {
    const deadline = performance.now() + timeoutMs;
    const check = () => {
      if (picture.querySelector('canvas')) {
        syncPlayerCanvas(picture);
        resolve(true);
        return;
      }
      if (performance.now() >= deadline) {
        resolve(false);
        return;
      }
      requestAnimationFrame(check);
    };
    check();
  });
}

export const TgsPlayer = forwardRef<TgsHandle, { size?: number; src?: string; loop?: boolean }>(({ size, src, loop = false }, ref) => {
  const pictureRef = useRef<TgsPictureElement>(null);
  const sourceRef = useRef<HTMLSourceElement>(null);
  const playbackAllowedRef = useRef(true);

  const playAnimation = useCallback(async (src: string): Promise<void> => {
    await loadRLottie();
    const picture = pictureRef.current;
    const source = sourceRef.current;
    if (!picture || !source || !window.RLottie) return;

    resetPlayer(picture);
    source.setAttribute('srcset', src);

    const animationEnd = loop ? null : waitForAnimationEnd(picture);
    // A TGS player can be remounted inside a page when returning from a
    // subpage. When RLottie is already loaded, initializing in the same frame
    // as the new <picture> can leave a blank avatar, so give the browser a
    // frame and retry once if no canvas appears.
    await nextFrame();
    if (pictureRef.current !== picture || sourceRef.current !== source) return;
    const playbackOptions = {
      ...(loop ? {} : { playUntilEnd: true }),
      maxDeviceRatio: document.documentElement.classList.contains('motion-quality-low') ? 1.5 : 2,
      maxFps: preferredTgsFps(),
    };
    window.RLottie!.init(picture, playbackOptions);
    if (!(await waitForCanvas(picture))) {
      resetPlayer(picture);
      source.setAttribute('srcset', src);
      await nextFrame();
      if (pictureRef.current !== picture || sourceRef.current !== source) return;
      window.RLottie!.init(picture, playbackOptions);
      await waitForCanvas(picture);
    }
    if (loop && !playbackAllowedRef.current) window.RLottie.pause(picture);
    if (animationEnd) await animationEnd;
  }, [loop]);

  useImperativeHandle(ref, () => ({
    clearAnimation(): void {
      const picture = pictureRef.current;
      const source = sourceRef.current;
      if (!picture || !source) return;

      resetPlayer(picture);
      source.setAttribute('srcset', '');
    },
    playAnimation,
  }), [playAnimation]);

  useEffect(() => {
    if (src) void playAnimation(src);
  }, [playAnimation, src]);

  useEffect(() => {
    const picture = pictureRef.current;
    if (!picture) return;
    mountedTgsPlayers += 1;

    const observer = new MutationObserver(() => syncPlayerCanvas(picture));
    observer.observe(picture, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      resetPlayer(picture);
      mountedTgsPlayers = Math.max(0, mountedTgsPlayers - 1);
      // RLottie workers are shared by every sticker on the page. Only tear down
      // the pool after the last player leaves; destroying it when a profile modal
      // closes freezes the stickers that remain in the leaderboard underneath.
      if (mountedTgsPlayers === 0) window.RLottie?.destroyWorkers?.();
    };
  }, []);

  useEffect(() => {
    const picture = pictureRef.current;
    if (!picture || !loop) return;
    let inViewport = true;
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const syncPlayback = () => {
      const allowed = inViewport && !document.hidden && !reducedMotion?.matches;
      playbackAllowedRef.current = allowed;
      if (!picture.rlPlayer || !window.RLottie) return;
      if (allowed) window.RLottie.play(picture);
      else window.RLottie.pause(picture);
    };
    const observer = new IntersectionObserver(entries => {
      inViewport = entries.some(entry => entry.isIntersecting);
      syncPlayback();
    }, { rootMargin: '80px' });
    observer.observe(picture);
    document.addEventListener('visibilitychange', syncPlayback);
    reducedMotion?.addEventListener?.('change', syncPlayback);
    syncPlayback();
    return () => {
      observer.disconnect();
      document.removeEventListener('visibilitychange', syncPlayback);
      reducedMotion?.removeEventListener?.('change', syncPlayback);
    };
  }, [loop]);

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

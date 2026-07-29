const LOW_MOTION_CLASS = 'motion-quality-low';
const HIDDEN_MOTION_CLASS = 'motion-page-hidden';
const motionElements = new Map<HTMLElement, boolean>();
let motionObserver: IntersectionObserver | null = null;
let motionVisibilityListening = false;

type NavigatorWithMemory = Navigator & { deviceMemory?: number };

/** Preserve the authored TGS cadence, including on constrained devices. */
export function preferredTgsFps(): number {
  return 60;
}

/**
 * Pick a cheaper motion cadence on constrained or visibly struggling devices. The visual
 * effects remain enabled; only their sampling rate changes. The short frame probe stops
 * after calibration, so the detector itself does not become another permanent animation.
 */
export function initAdaptiveMotion(): () => void {
  const root = document.documentElement;
  const nav = navigator as NavigatorWithMemory;
  const constrained = (nav.hardwareConcurrency > 0 && nav.hardwareConcurrency <= 4)
    || (typeof nav.deviceMemory === 'number' && nav.deviceMemory <= 4)
    || window.matchMedia?.('(update: slow)').matches;
  if (constrained) root.classList.add(LOW_MOTION_CLASS);

  const syncVisibility = () => root.classList.toggle(HIDDEN_MOTION_CLASS, document.hidden);
  document.addEventListener('visibilitychange', syncVisibility);
  syncVisibility();

  let frame = 0;
  let previous = performance.now();
  let samples = 0;
  let slowFrames = 0;
  const sample = (now: number) => {
    const elapsed = now - previous;
    previous = now;
    if (elapsed > 24 && elapsed < 250) slowFrames += 1;
    samples += 1;
    if (samples < 120 && !document.hidden) {
      frame = requestAnimationFrame(sample);
    } else if (samples >= 60 && slowFrames / samples > 0.22) {
      root.classList.add(LOW_MOTION_CLASS);
    }
  };
  frame = requestAnimationFrame(sample);

  return () => {
    cancelAnimationFrame(frame);
    document.removeEventListener('visibilitychange', syncVisibility);
    root.classList.remove(HIDDEN_MOTION_CLASS);
  };
}

function syncMotionElement(element: HTMLElement): void {
  element.dataset.motionState = motionElements.get(element) && !document.hidden ? 'running' : 'paused';
}

function syncAllMotionElements(): void {
  motionElements.forEach((_visible, element) => syncMotionElement(element));
}

function ensureMotionObserver(): void {
  if (!motionObserver) {
    motionObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const element = entry.target as HTMLElement;
        if (!motionElements.has(element)) return;
        motionElements.set(element, entry.isIntersecting);
        syncMotionElement(element);
      });
    }, { rootMargin: '80px' });
  }
  if (!motionVisibilityListening) {
    document.addEventListener('visibilitychange', syncAllMotionElements);
    motionVisibilityListening = true;
  }
}

/** Pause CSS animations when their whole visual is outside the viewport. */
export function observeMotionElement(element: HTMLElement): () => void {
  ensureMotionObserver();
  motionElements.set(element, true);
  motionObserver!.observe(element);
  syncMotionElement(element);
  return () => {
    motionObserver?.unobserve(element);
    motionElements.delete(element);
    delete element.dataset.motionState;
    if (motionElements.size === 0) {
      motionObserver?.disconnect();
      motionObserver = null;
      if (motionVisibilityListening) {
        document.removeEventListener('visibilitychange', syncAllMotionElements);
        motionVisibilityListening = false;
      }
    }
  };
}

import { useCallback } from 'react';
import { hapticImpact, hapticNotification } from '@/lib/tma';

type HapticStyle = 'light' | 'medium' | 'heavy';

export function useHaptics() {
  const impact = useCallback((style: HapticStyle = 'light') => {
    hapticImpact(style);
  }, []);

  const success = useCallback(() => {
    hapticNotification('success');
  }, []);

  const warning = useCallback(() => {
    hapticNotification('warning');
  }, []);

  const error = useCallback(() => {
    hapticNotification('error');
  }, []);

  return { impact, success, warning, error };
}
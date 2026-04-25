import { useCallback } from 'react';
import { useZooStore } from '@/store';
import { hapticImpact, hapticNotification } from '@/lib/tma';

interface ShopActionsOptions {
  showToast: (kind: 'ok' | 'err', text: string) => void;
}

export function useShopActions({ showToast }: ShopActionsOptions) {
  const buyAviaryInStore = useZooStore(s => s.buyAviary);
  const buyAnimalInStore = useZooStore(s => s.buyAnimal);

  const buyAviary = useCallback(async (aviaryId: string) => {
    hapticImpact('medium');
    try {
      const res = await buyAviaryInStore(aviaryId);
      if (!res) return;
      if (!res.ok) {
        hapticNotification('error');
        showToast('err', 'Не удалось купить вольер');
        return;
      }

      hapticNotification('success');
      showToast('ok', 'Вольер куплен!');
    } catch (e) {
      hapticNotification('error');
      showToast('err', e instanceof Error ? e.message : 'Ошибка покупки');
    }
  }, [buyAviaryInStore, showToast]);

  const buyAnimal = useCallback(async (animalId: string, quantity: number) => {
    hapticImpact('medium');
    try {
      const res = await buyAnimalInStore(animalId, quantity);
      if (!res) return;
      if (!res.ok) {
        hapticNotification('error');
        showToast('err', res.message ?? 'Не удалось купить животное');
        return;
      }

      hapticNotification('success');
      showToast('ok', 'Животное куплено!');
    } catch (e) {
      hapticNotification('error');
      showToast('err', e instanceof Error ? e.message : 'Ошибка покупки');
    }
  }, [buyAnimalInStore, showToast]);

  return { buyAnimal, buyAviary };
}

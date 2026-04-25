import { useCallback, useEffect, useState } from 'react';
import type { RootTab } from '@/components/TabBar';

const ROOT_TABS: RootTab[] = ['zoo', 'shop', 'lab', 'games', 'more'];

function hashPath(): string {
  return window.location.hash.replace(/^#/, '') || '/zoo';
}

export function getRootTabFromHash(): RootTab {
  const root = hashPath().split('/').filter(Boolean)[0];
  return ROOT_TABS.includes(root as RootTab) ? root as RootTab : 'zoo';
}

export function setHashPath(path: string) {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  if (window.location.hash !== `#${normalized}`) {
    window.location.hash = normalized;
  }
}

export function useHashTab() {
  const [tab, setTabState] = useState<RootTab>(() => getRootTabFromHash());

  useEffect(() => {
    const onHashChange = () => setTabState(getRootTabFromHash());
    window.addEventListener('hashchange', onHashChange);
    onHashChange();
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const setTab = useCallback((nextTab: RootTab) => {
    setHashPath(`/${nextTab}`);
    setTabState(nextTab);
  }, []);

  return [tab, setTab] as const;
}

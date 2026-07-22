export const PROFILE_ACHIEVEMENT_PREFIX = 'achievement:';

export const ACHIEVEMENT_TGS: Record<string, string> = {
  first_beast: '/nft_BunnyMuffin-20044.tgs',
  growing_zoo: '/nft_JollyChimp-1.tgs',
  collector: '/nft_RareBird-1.tgs',
  first_baby: '/nft_KissedFrog-9639.tgs',
  geneticist: '/nft_MagicPotion-1.tgs',
  first_expedition: '/nft_StellarRocket-1.tgs',
  pathfinder: '/nft_HeroicHelmet-2751.tgs',
  architect: '/nft_ArtisanBrick-4828.tgs',
  blacksmith: '/nft_MightyArm-1.tgs',
  arena_winner: '/nft_UFCStrike-2254.tgs',
  endgame_zoo: '/nft_BigYear-9228.tgs',
  endgame_collector: '/nft_TimelessBook-56334.tgs',
  endgame_geneticist: '/nft_IonGem-2553.tgs',
  endgame_explorer: '/nft_VictoryMedal-10059.tgs',
  endgame_empire: '/nft_MoneyPot-1.tgs',
  perfect_fifty: '/nft_DiamondRing-5.tgs',
};

export function profileAchievementValue(id: string): string {
  return `${PROFILE_ACHIEVEMENT_PREFIX}${id}`;
}

export function customAchievementImage(id: string): string | null {
  return id.startsWith('custom_') ? `/api/achievements/${id}/image` : null;
}

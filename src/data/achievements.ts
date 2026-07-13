export const PROFILE_ACHIEVEMENT_PREFIX = 'achievement:';

export const ACHIEVEMENT_TGS: Record<string, string> = {
  first_beast: '/nft_ScaredCat-15455.tgs',
  growing_zoo: '/nft_KhabibsPapakha-28085.tgs',
  collector: '/nft_CrystalBall-9406.tgs',
  first_baby: '/nft_HypnoLollipop-9514.tgs',
  geneticist: '/nft_AstralShard-3155.tgs',
  first_expedition: '/nft_StellarRocket-31355.tgs',
  pathfinder: '/nft_HeroicHelmet-611.tgs',
  architect: '/nft_ArtisanBrick-2928.tgs',
  blacksmith: '/nft_SwissWatch-6567.tgs',
  arena_winner: '/nft_MiniOscar-1300.tgs',
};

export function profileAchievementValue(id: string): string {
  return `${PROFILE_ACHIEVEMENT_PREFIX}${id}`;
}

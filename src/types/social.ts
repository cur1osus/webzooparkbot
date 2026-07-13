export interface TopEntry {
  rank: number;
  tg_id: number;
  nickname: string;
  nickname_color: string;
  profile_emoji: string | null;
  profile_frame: string;
  income_rub_per_min: number;
  is_me: boolean;
}

export interface TopResponse {
  entries: TopEntry[];
  my_rank: number | null;
}

export interface PublicProfileSpecies {
  name: string;
  emoji: string;
  count: number;
}

export interface PublicProfile {
  tg_id: number;
  nickname: string;
  nickname_color: string;
  profile_emoji: string | null;
  profile_frame: string;
  profile_wallpaper: string;
  rank: number;
  income_rub_per_min: number;
  upkeep_rub_per_min: number;
  animals_count: number;
  species_count: number;
  localities_count: number;
  locality_levels: number;
  achievements_completed: number;
  achievements_total: number;
  vet_level: number;
  genetics_level: number;
  registered_at: string;
  clan: {
    name: string;
    level: number;
    member_count: number;
    role: 'owner' | 'member';
  } | null;
  species: PublicProfileSpecies[];
}

export interface ClanOut {
  id: number;
  name: string;
  level: number;
  member_count: number;
  owner_nickname: string;
}

export interface ClanListResponse {
  clans: ClanOut[];
  my_clan: ClanOut | null;
  my_role: 'owner' | 'member' | null;
}

export interface ClanMember {
  tg_id: number;
  nickname: string;
  role: 'owner' | 'member';
  income_rub_per_min: number;
}

export interface ClanMembersResponse {
  members: ClanMember[];
}

export interface ReferralResponse {
  code: string;
  total: number;
  signup_reward_usd: number;
  referred: string[];
}

export interface TransferOut {
  code: string;
  total_rub: number;
  rub_per_claim: number;
  max_claims: number;
  claims: number;
  active: boolean;
  created_at: string;
  expires_at: string;
}

export interface TransferCreateResponse {
  code: string;
  total_rub: number;
  new_rub: number;
}

export interface TransferClaimResponse {
  ok: boolean;
  rub_received: number;
  new_rub: number;
}

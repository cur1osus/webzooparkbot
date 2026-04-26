export interface TopEntry {
  rank: number;
  tg_id: number;
  nickname: string;
  income_rub_per_min: number;
  name_color: string | null;
  is_me: boolean;
}

export interface TopResponse {
  entries: TopEntry[];
  my_rank: number | null;
}

export interface ClanOut {
  idpk: number;
  name: string;
  level: number;
  member_count: number;
  specialty: string | null;
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
  reward_usd_per_ref: number;
  referred: string[];
}

export interface TransferOut {
  key: string;
  total_rub: number;
  rub_per_claim: number;
  max_claims: number;
  claims: number;
  active: boolean;
  created_at: string;
}

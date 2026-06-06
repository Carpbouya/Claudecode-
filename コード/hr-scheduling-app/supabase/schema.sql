-- ============================================================
-- HR Scheduling App - Supabase Schema
-- ============================================================

-- 拡張機能
create extension if not exists "uuid-ossp";

-- ============================================================
-- テーブル 1: companies (クライアント企業)
-- ============================================================
create table public.companies (
  id            uuid primary key default uuid_generate_v4(),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  -- 表示情報
  name          text not null,                    -- 企業名 (例: 株式会社サンプル)
  slug          text not null unique,             -- URLパス (例: sample-corp)
  logo_url      text,                             -- ロゴ画像URL
  theme_color   text not null default '#2563EB',  -- テーマカラー (hex)
  greeting_text text,                             -- 候補者向け案内文

  -- Google Calendar連携
  calendar_id   text not null,                    -- 対象のGoogle Calendar ID
  -- (例: xxxxx@group.calendar.google.com)

  -- メール送信者名 (候補者に見える差出人名)
  sender_name   text not null,                    -- 例: 株式会社サンプル 採用事務局
  sender_email  text not null,                    -- 例: recruit@sample-corp.jp

  -- 面接枠設定
  slot_duration_minutes int not null default 30,  -- 30 or 60分
  buffer_minutes        int not null default 10,  -- 前後バッファ (分)
  available_days_ahead  int not null default 14,  -- 何日先まで表示するか

  is_active     boolean not null default true
);

comment on table public.companies is 'クライアント企業マスタ。各企業がマルチテナントの1ユニット。';
comment on column public.companies.slug is 'URLの /booking/[slug] に使用。英数字・ハイフンのみ。';
comment on column public.companies.calendar_id is 'この企業専用のGoogle Calendar ID。Service Accountで操作。';

-- ============================================================
-- テーブル 2: bookings (予約・面接履歴)
-- ============================================================
create table public.bookings (
  id            uuid primary key default uuid_generate_v4(),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  -- どの企業の予約か
  company_id    uuid not null references public.companies(id) on delete restrict,

  -- 候補者情報
  candidate_name  text not null,
  candidate_email text not null,
  candidate_phone text,
  source_medium   text,           -- 応募媒体 (Indeed, etc.)

  -- 面接日時
  interview_start_at  timestamptz not null,
  interview_end_at    timestamptz not null,

  -- Google連携
  google_calendar_event_id  text,     -- 作成したGoogleカレンダーイベントID
  google_meet_url           text,     -- 自動生成したMeet URL

  -- ステータス
  -- pending: 候補者が選択完了・処理中
  -- confirmed: カレンダー登録・メール送信完了
  -- cancelled: キャンセル済み
  -- rescheduled: 日程変更済み
  status  text not null default 'pending'
            check (status in ('pending', 'confirmed', 'cancelled', 'rescheduled')),

  -- メモ (管理者用)
  admin_notes text
);

comment on table public.bookings is '候補者が確定した面接予約。Google Calendar + メール送信のトランザクションレコード。';

-- ============================================================
-- テーブル 3: booking_notifications (メール送信ログ)
-- ============================================================
create table public.booking_notifications (
  id          uuid primary key default uuid_generate_v4(),
  created_at  timestamptz not null default now(),

  booking_id  uuid not null references public.bookings(id) on delete cascade,

  -- sent: 送信成功 / failed: 送信失敗
  status      text not null check (status in ('sent', 'failed')),
  recipient   text not null,   -- 送信先メールアドレス
  subject     text not null,
  body        text not null,
  error_msg   text             -- 失敗時のエラーメッセージ
);

comment on table public.booking_notifications is '候補者へのメール送信ログ。再送時の確認に使用。';

-- ============================================================
-- インデックス
-- ============================================================
create index idx_companies_slug          on public.companies(slug);
create index idx_companies_is_active     on public.companies(is_active);
create index idx_bookings_company_id     on public.bookings(company_id);
create index idx_bookings_status         on public.bookings(status);
create index idx_bookings_interview_start on public.bookings(interview_start_at);
create index idx_bookings_candidate_email on public.bookings(candidate_email);
create index idx_notifications_booking_id on public.booking_notifications(booking_id);

-- ============================================================
-- updated_at 自動更新トリガー
-- ============================================================
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger trg_companies_updated_at
  before update on public.companies
  for each row execute function public.set_updated_at();

create trigger trg_bookings_updated_at
  before update on public.bookings
  for each row execute function public.set_updated_at();

-- ============================================================
-- Row Level Security (RLS)
-- ============================================================
-- 管理者はSupabase Auth経由でサービスロールキーを使うためRLSは
-- anon / authenticated に絞る。候補者側は特定のRPC経由のみ許可。

alter table public.companies            enable row level security;
alter table public.bookings             enable row level security;
alter table public.booking_notifications enable row level security;

-- 候補者 (未認証) は companies を slug で1件だけ読める (表示用)
create policy "anon can read active company by slug"
  on public.companies for select
  to anon
  using (is_active = true);

-- 候補者 (未認証) は bookings を insert のみ可能
create policy "anon can insert booking"
  on public.bookings for insert
  to anon
  with check (true);

-- 管理者 (authenticated) はすべて操作可能
create policy "authenticated full access companies"
  on public.companies for all
  to authenticated using (true) with check (true);

create policy "authenticated full access bookings"
  on public.bookings for all
  to authenticated using (true) with check (true);

create policy "authenticated full access notifications"
  on public.booking_notifications for all
  to authenticated using (true) with check (true);

-- ============================================================
-- サンプルデータ
-- ============================================================
insert into public.companies (
  name, slug, logo_url, theme_color, greeting_text,
  calendar_id, sender_name, sender_email,
  slot_duration_minutes, buffer_minutes, available_days_ahead
) values (
  '株式会社サンプル',
  'sample-corp',
  'https://example.com/logo.png',
  '#1D4ED8',
  'この度はご応募いただきありがとうございます。以下より面接日程をお選びください。',
  'sample@group.calendar.google.com',
  '株式会社サンプル 採用事務局',
  'recruit@sample-corp.jp',
  30, 10, 14
);

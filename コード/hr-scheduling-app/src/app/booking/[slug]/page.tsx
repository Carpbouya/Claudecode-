import { notFound } from 'next/navigation';
import { createClient } from '@supabase/supabase-js';
import BookingFlow from '@/components/booking/BookingFlow';
import type { Company } from '@/types';

interface Props {
  params: { slug: string };
}

async function getCompany(slug: string): Promise<Company | null> {
  // サーバーコンポーネントではサービスロールキーは使わず anon キーで取得
  // (RLS で anon は active な企業のみ読み取り可能)
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  const { data } = await supabase
    .from('companies')
    .select('*')
    .eq('slug', slug)
    .eq('is_active', true)
    .single();

  return data;
}

export default async function BookingPage({ params }: Props) {
  const company = await getCompany(params.slug);
  if (!company) notFound();

  return (
    <main
      className="min-h-screen bg-gray-50"
      style={{ '--brand': company.theme_color } as React.CSSProperties}
    >
      <BookingFlow company={company} />
    </main>
  );
}

export async function generateMetadata({ params }: Props) {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
  const { data } = await supabase
    .from('companies')
    .select('name')
    .eq('slug', params.slug)
    .single();

  return {
    title: data ? `${data.name} 面接日程のご確認` : '面接日程のご確認',
  };
}

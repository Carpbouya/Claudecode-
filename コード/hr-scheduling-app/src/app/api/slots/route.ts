import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { google } from 'googleapis';
import { addDays, startOfDay } from 'date-fns';
import { buildAvailableSlots } from '@/lib/calendar';

// Service Account を使って Google Calendar API を初期化
function getGoogleCalendarClient() {
  const auth = new google.auth.GoogleAuth({
    credentials: {
      client_email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL!,
      private_key: process.env.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY!.replace(/\\n/g, '\n'),
    },
    scopes: ['https://www.googleapis.com/auth/calendar'],
  });
  return google.calendar({ version: 'v3', auth });
}

export async function GET(req: NextRequest) {
  const companyId = req.nextUrl.searchParams.get('companyId');
  if (!companyId) {
    return NextResponse.json({ error: 'companyId required' }, { status: 400 });
  }

  // Supabase から企業情報を取得
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  const { data: company, error } = await supabase
    .from('companies')
    .select('calendar_id, slot_duration_minutes, buffer_minutes, available_days_ahead')
    .eq('id', companyId)
    .eq('is_active', true)
    .single();

  if (error || !company) {
    return NextResponse.json({ error: 'Company not found' }, { status: 404 });
  }

  // Google Calendar から freebusy を取得
  const calendar = getGoogleCalendarClient();
  const now = new Date();
  const timeMax = addDays(startOfDay(now), company.available_days_ahead + 1);

  const { data: freeBusyData } = await calendar.freebusy.query({
    requestBody: {
      timeMin: now.toISOString(),
      timeMax: timeMax.toISOString(),
      timeZone: 'Asia/Tokyo',
      items: [{ id: company.calendar_id }],
    },
  });

  const busyTimes =
    freeBusyData.calendars?.[company.calendar_id]?.busy ?? [];

  // 空きスロットを計算
  const slots = buildAvailableSlots(
    busyTimes as { start: string; end: string }[],
    company.slot_duration_minutes,
    company.buffer_minutes,
    company.available_days_ahead
  );

  return NextResponse.json(slots);
}

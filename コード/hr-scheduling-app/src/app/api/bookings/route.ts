import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { google } from 'googleapis';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';

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

export async function POST(req: NextRequest) {
  const body = await req.json();
  const {
    companyId,
    slotStart,
    slotEnd,
    candidateName,
    candidateEmail,
    candidatePhone,
    sourceMedium,
  } = body;

  if (!companyId || !slotStart || !slotEnd || !candidateName || !candidateEmail) {
    return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
  }

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  const { data: company } = await supabase
    .from('companies')
    .select('*')
    .eq('id', companyId)
    .eq('is_active', true)
    .single();

  if (!company) {
    return NextResponse.json({ error: 'Company not found' }, { status: 404 });
  }

  // 1. Google Calendar にイベントを作成（ゲスト招待なし・Meet URL自動生成）
  const calendar = getGoogleCalendarClient();
  const startDate = new Date(slotStart);
  const endDate = new Date(slotEnd);

  const eventTitle = `【${company.name}面接】${candidateName}様`;
  const eventDescription = [
    `■ 候補者情報`,
    `氏名: ${candidateName}`,
    `メール: ${candidateEmail}`,
    candidatePhone ? `電話: ${candidatePhone}` : null,
    sourceMedium ? `応募媒体: ${sourceMedium}` : null,
    '',
    `■ 面接詳細`,
    `日時: ${format(startDate, 'yyyy年M月d日(EEE) HH:mm', { locale: ja })} 〜 ${format(endDate, 'HH:mm')}`,
  ]
    .filter((l) => l !== null)
    .join('\n');

  const { data: event } = await calendar.events.insert({
    calendarId: company.calendar_id,
    conferenceDataVersion: 1, // Google Meet URLを自動生成
    requestBody: {
      summary: eventTitle,
      description: eventDescription,
      start: { dateTime: startDate.toISOString(), timeZone: 'Asia/Tokyo' },
      end:   { dateTime: endDate.toISOString(),   timeZone: 'Asia/Tokyo' },
      // ※ attendees を設定しない → ゲスト招待なし（ステルス要件）
      conferenceData: {
        createRequest: {
          requestId: `${companyId}-${Date.now()}`,
          conferenceSolutionKey: { type: 'hangoutsMeet' },
        },
      },
    },
  });

  const meetUrl =
    event.conferenceData?.entryPoints?.find((e) => e.entryPointType === 'video')?.uri ?? '';

  // 2. Supabase に予約レコードを作成
  const { data: booking } = await supabase
    .from('bookings')
    .insert({
      company_id: companyId,
      candidate_name: candidateName,
      candidate_email: candidateEmail,
      candidate_phone: candidatePhone || null,
      source_medium: sourceMedium || null,
      interview_start_at: startDate.toISOString(),
      interview_end_at: endDate.toISOString(),
      google_calendar_event_id: event.id,
      google_meet_url: meetUrl,
      status: 'confirmed',
    })
    .select()
    .single();

  // 3. 候補者へ確定メールを送信
  await sendConfirmationEmail({
    company,
    candidateName,
    candidateEmail,
    startDate,
    endDate,
    meetUrl,
    bookingId: booking?.id ?? '',
    supabase,
  });

  return NextResponse.json({ success: true, meetUrl, bookingId: booking?.id });
}

async function sendConfirmationEmail({
  company,
  candidateName,
  candidateEmail,
  startDate,
  endDate,
  meetUrl,
  bookingId,
  supabase,
}: {
  company: any;
  candidateName: string;
  candidateEmail: string;
  startDate: Date;
  endDate: Date;
  meetUrl: string;
  bookingId: string;
  supabase: any;
}) {
  const subject = `【面接日程確定のご連絡】${company.name}`;
  const body = `
${candidateName} 様

この度は${company.name}へご応募いただき、誠にありがとうございます。
以下の日時で面接の日程が確定いたしましたのでご連絡申し上げます。

━━━━━━━━━━━━━━━━━━━━━━
■ 面接日時
${format(startDate, 'yyyy年M月d日(EEE) HH:mm', { locale: ja })} 〜 ${format(endDate, 'HH:mm')}

■ 面接形式
オンライン面接（Google Meet）

■ 参加URL
${meetUrl}
━━━━━━━━━━━━━━━━━━━━━━

当日は上記URLよりご参加ください。
ご不明な点がございましたら、本メールへの返信にてお問い合わせください。

${company.sender_name}
${company.sender_email}
`.trim();

  // メール送信: Resend / SendGrid / Nodemailer 等に差し替え可能
  // ここでは Resend API を使った例
  try {
    const resendRes = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: `${company.sender_name} <${company.sender_email}>`,
        to: [candidateEmail],
        subject,
        text: body,
      }),
    });

    await supabase.from('booking_notifications').insert({
      booking_id: bookingId,
      status: resendRes.ok ? 'sent' : 'failed',
      recipient: candidateEmail,
      subject,
      body,
      error_msg: resendRes.ok ? null : await resendRes.text(),
    });
  } catch (err) {
    await supabase.from('booking_notifications').insert({
      booking_id: bookingId,
      status: 'failed',
      recipient: candidateEmail,
      subject,
      body,
      error_msg: String(err),
    });
  }
}

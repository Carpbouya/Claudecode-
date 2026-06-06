'use client';

import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import type { Company, TimeSlot, BookingFormData } from '@/types';

interface Props {
  company: Company;
  slot: TimeSlot;
  formData: BookingFormData;
  meetUrl: string;
}

export default function CompleteView({ company, slot, formData, meetUrl }: Props) {
  return (
    <div className="text-center py-4">
      {/* 完了アイコン */}
      <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <h2 className="text-xl font-bold text-gray-800 mb-2">
        日程が確定しました
      </h2>
      <p className="text-sm text-gray-500 mb-6">
        {formData.candidateEmail} 宛に確定メールをお送りしました。
      </p>

      {/* 予約サマリー */}
      <div className="bg-gray-50 rounded-xl p-5 text-left text-sm space-y-3 mb-6">
        <div className="flex gap-3">
          <span className="text-gray-400 w-20">日時</span>
          <span className="font-semibold text-gray-800">
            {format(slot.start, 'yyyy年M月d日(EEE) HH:mm', { locale: ja })} 〜{' '}
            {format(slot.end, 'HH:mm')}
          </span>
        </div>
        <div className="flex gap-3">
          <span className="text-gray-400 w-20">形式</span>
          <span className="text-gray-800">オンライン（Google Meet）</span>
        </div>
        {meetUrl && (
          <div className="flex gap-3 items-start">
            <span className="text-gray-400 w-20">URL</span>
            <a
              href={meetUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 underline break-all"
            >
              {meetUrl}
            </a>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400">
        ご不明な点がございましたら、{company.sender_email} までご連絡ください。
      </p>
    </div>
  );
}

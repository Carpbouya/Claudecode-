'use client';

import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import type { Company, TimeSlot, BookingFormData } from '@/types';

interface Props {
  company: Company;
  slot: TimeSlot;
  formData: BookingFormData;
  brandColor: string;
  isSubmitting: boolean;
  onConfirm: () => void;
  onBack: () => void;
}

export default function ConfirmView({
  company,
  slot,
  formData,
  brandColor,
  isSubmitting,
  onConfirm,
  onBack,
}: Props) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-6">
        以下の内容でよろしいですか？
      </h2>

      <div className="space-y-4 text-sm">
        <ConfirmRow label="企業名" value={company.name} />
        <ConfirmRow
          label="面接日時"
          value={`${format(slot.start, 'yyyy年M月d日(EEE) HH:mm', { locale: ja })} 〜 ${format(slot.end, 'HH:mm')}`}
          highlight
          brandColor={brandColor}
        />
        <ConfirmRow label="お名前" value={formData.candidateName} />
        <ConfirmRow label="メールアドレス" value={formData.candidateEmail} />
        {formData.candidatePhone && (
          <ConfirmRow label="電話番号" value={formData.candidatePhone} />
        )}
      </div>

      <p className="mt-6 text-xs text-gray-400 leading-relaxed">
        「確定する」を押すと、ご入力のメールアドレス宛に確定メールをお送りします。
        面接はオンライン（Google Meet）で実施いたします。
      </p>

      <div className="flex gap-3 mt-6">
        <button
          type="button"
          onClick={onBack}
          disabled={isSubmitting}
          className="flex-1 py-3 rounded-xl border-2 border-gray-300 text-gray-600 text-sm font-semibold hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          ← 修正する
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={isSubmitting}
          className="flex-1 py-3 rounded-xl text-white text-sm font-semibold transition-opacity hover:opacity-90 disabled:opacity-60 flex items-center justify-center gap-2"
          style={{ backgroundColor: brandColor }}
        >
          {isSubmitting && (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          )}
          {isSubmitting ? '処理中…' : '確定する'}
        </button>
      </div>
    </div>
  );
}

function ConfirmRow({
  label,
  value,
  highlight,
  brandColor,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  brandColor?: string;
}) {
  return (
    <div className="flex gap-4 py-3 border-b border-gray-100 last:border-0">
      <span className="w-28 flex-shrink-0 text-gray-500">{label}</span>
      <span
        className={highlight ? 'font-bold text-base' : 'text-gray-800 font-medium'}
        style={highlight && brandColor ? { color: brandColor } : {}}
      >
        {value}
      </span>
    </div>
  );
}

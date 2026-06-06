'use client';

import { useState } from 'react';
import { format } from 'date-fns';
import { ja } from 'date-fns/locale';
import type { TimeSlot, BookingFormData } from '@/types';

interface Props {
  slot: TimeSlot;
  brandColor: string;
  initialData: BookingFormData;
  onSubmit: (data: BookingFormData) => void;
  onBack: () => void;
}

export default function CandidateForm({
  slot,
  brandColor,
  initialData,
  onSubmit,
  onBack,
}: Props) {
  const [form, setForm] = useState<BookingFormData>(initialData);
  const [errors, setErrors] = useState<Partial<BookingFormData>>({});

  const validate = (): boolean => {
    const e: Partial<BookingFormData> = {};
    if (!form.candidateName.trim()) e.candidateName = 'お名前を入力してください';
    if (!form.candidateEmail.trim()) {
      e.candidateEmail = 'メールアドレスを入力してください';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.candidateEmail)) {
      e.candidateEmail = '正しいメールアドレスを入力してください';
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) onSubmit(form);
  };

  return (
    <div>
      {/* 選択日時の確認 */}
      <div
        className="rounded-xl p-4 mb-6 text-sm"
        style={{ backgroundColor: `${brandColor}15`, borderLeft: `4px solid ${brandColor}` }}
      >
        <p className="font-semibold text-gray-700">選択中の日時</p>
        <p className="mt-1 text-gray-800 text-base font-bold">
          {format(slot.start, 'yyyy年M月d日(EEE) HH:mm', { locale: ja })} 〜{' '}
          {format(slot.end, 'HH:mm')}
        </p>
      </div>

      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        お客様情報の入力
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Field
          label="お名前"
          required
          error={errors.candidateName}
          brandColor={brandColor}
        >
          <input
            type="text"
            placeholder="山田 太郎"
            value={form.candidateName}
            onChange={(e) => setForm({ ...form, candidateName: e.target.value })}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 transition-all"
            style={{ '--tw-ring-color': brandColor } as React.CSSProperties}
          />
        </Field>

        <Field
          label="メールアドレス"
          required
          error={errors.candidateEmail}
          brandColor={brandColor}
        >
          <input
            type="email"
            placeholder="taro.yamada@example.com"
            value={form.candidateEmail}
            onChange={(e) => setForm({ ...form, candidateEmail: e.target.value })}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 transition-all"
          />
          <p className="mt-1 text-xs text-gray-400">
            ※ 確定メールをこちらのアドレスへお送りします
          </p>
        </Field>

        <Field
          label="電話番号"
          brandColor={brandColor}
        >
          <input
            type="tel"
            placeholder="090-0000-0000"
            value={form.candidatePhone}
            onChange={(e) => setForm({ ...form, candidatePhone: e.target.value })}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 transition-all"
          />
        </Field>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onBack}
            className="flex-1 py-3 rounded-xl border-2 border-gray-300 text-gray-600 text-sm font-semibold hover:bg-gray-50 transition-colors"
          >
            ← 戻る
          </button>
          <button
            type="submit"
            className="flex-1 py-3 rounded-xl text-white text-sm font-semibold transition-opacity hover:opacity-90"
            style={{ backgroundColor: brandColor }}
          >
            次へ →
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  required,
  error,
  brandColor,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  brandColor: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && (
          <span className="ml-1 text-xs font-normal" style={{ color: brandColor }}>
            必須
          </span>
        )}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  );
}

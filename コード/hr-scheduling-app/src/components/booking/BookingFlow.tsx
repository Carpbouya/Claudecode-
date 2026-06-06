'use client';

import { useState } from 'react';
import type { Company, TimeSlot, BookingFormData, BookingStep } from '@/types';
import SlotPicker from './SlotPicker';
import CandidateForm from './CandidateForm';
import ConfirmView from './ConfirmView';
import CompleteView from './CompleteView';

interface Props {
  company: Company;
}

export default function BookingFlow({ company }: Props) {
  const [step, setStep] = useState<BookingStep>('select-slot');
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
  const [formData, setFormData] = useState<BookingFormData>({
    candidateName: '',
    candidateEmail: '',
    candidatePhone: '',
    sourceMedium: '',
  });
  const [meetUrl, setMeetUrl] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const brandColor = company.theme_color;

  const handleSlotSelect = (slot: TimeSlot) => {
    setSelectedSlot(slot);
    setStep('enter-info');
  };

  const handleFormSubmit = (data: BookingFormData) => {
    setFormData(data);
    setStep('confirm');
  };

  const handleConfirm = async () => {
    if (!selectedSlot) return;
    setIsSubmitting(true);

    try {
      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          companyId: company.id,
          companySlug: company.slug,
          slotStart: selectedSlot.start.toISOString(),
          slotEnd: selectedSlot.end.toISOString(),
          ...formData,
        }),
      });

      if (!res.ok) throw new Error('予約処理に失敗しました');
      const json = await res.json();
      setMeetUrl(json.meetUrl ?? '');
      setStep('complete');
    } catch (err) {
      alert('エラーが発生しました。お手数ですが、再度お試しください。');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* ヘッダー */}
      <header className="mb-8 text-center">
        {company.logo_url && (
          <img
            src={company.logo_url}
            alt={company.name}
            className="h-14 mx-auto mb-4 object-contain"
          />
        )}
        <h1 className="text-2xl font-bold text-gray-800">{company.name}</h1>
        {company.greeting_text && (
          <p className="mt-2 text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
            {company.greeting_text}
          </p>
        )}
      </header>

      {/* ステップインジケーター */}
      <StepIndicator current={step} brandColor={brandColor} />

      {/* メインコンテンツ */}
      <div className="mt-6 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        {step === 'select-slot' && (
          <SlotPicker
            company={company}
            brandColor={brandColor}
            onSelect={handleSlotSelect}
          />
        )}
        {step === 'enter-info' && selectedSlot && (
          <CandidateForm
            slot={selectedSlot}
            brandColor={brandColor}
            initialData={formData}
            onSubmit={handleFormSubmit}
            onBack={() => setStep('select-slot')}
          />
        )}
        {step === 'confirm' && selectedSlot && (
          <ConfirmView
            company={company}
            slot={selectedSlot}
            formData={formData}
            brandColor={brandColor}
            isSubmitting={isSubmitting}
            onConfirm={handleConfirm}
            onBack={() => setStep('enter-info')}
          />
        )}
        {step === 'complete' && selectedSlot && (
          <CompleteView
            company={company}
            slot={selectedSlot}
            formData={formData}
            meetUrl={meetUrl}
          />
        )}
      </div>
    </div>
  );
}

// ─── ステップインジケーター ──────────────────────────────────
const STEPS: { key: BookingStep; label: string }[] = [
  { key: 'select-slot', label: '日程選択' },
  { key: 'enter-info',  label: '情報入力' },
  { key: 'confirm',     label: '確認' },
  { key: 'complete',    label: '完了' },
];

function StepIndicator({
  current,
  brandColor,
}: {
  current: BookingStep;
  brandColor: string;
}) {
  const currentIndex = STEPS.findIndex((s) => s.key === current);

  return (
    <div className="flex items-center justify-center gap-0">
      {STEPS.map((step, i) => {
        const done = i < currentIndex;
        const active = i === currentIndex;
        return (
          <div key={step.key} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors"
                style={{
                  backgroundColor: done || active ? brandColor : '#E5E7EB',
                  color: done || active ? '#fff' : '#9CA3AF',
                }}
              >
                {done ? '✓' : i + 1}
              </div>
              <span
                className="mt-1 text-xs font-medium"
                style={{ color: active ? brandColor : '#9CA3AF' }}
              >
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className="w-12 h-0.5 mx-1 mb-4 transition-colors"
                style={{ backgroundColor: done ? brandColor : '#E5E7EB' }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

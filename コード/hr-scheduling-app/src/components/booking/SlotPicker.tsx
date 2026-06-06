'use client';

import { useEffect, useState } from 'react';
import { format, isSameDay } from 'date-fns';
import { ja } from 'date-fns/locale';
import type { Company, TimeSlot, DaySlots } from '@/types';

interface Props {
  company: Company;
  brandColor: string;
  onSelect: (slot: TimeSlot) => void;
}

export default function SlotPicker({ company, brandColor, onSelect }: Props) {
  const [daySlots, setDaySlots] = useState<DaySlots[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(
          `/api/slots?companyId=${company.id}`
        );
        if (!res.ok) throw new Error();
        const data: DaySlots[] = await res.json();
        // Date文字列をDateオブジェクトに変換
        const parsed = data.map((d) => ({
          ...d,
          date: new Date(d.date),
          slots: d.slots.map((s) => ({
            ...s,
            start: new Date(s.start),
            end: new Date(s.end),
          })),
        }));
        setDaySlots(parsed);
        if (parsed.length > 0) setSelectedDate(parsed[0].date);
      } catch {
        setError('空き時間の取得に失敗しました。ページを再読み込みしてください。');
      } finally {
        setLoading(false);
      }
    })();
  }, [company.id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center py-16 gap-3">
        <div
          className="w-8 h-8 rounded-full border-4 border-t-transparent animate-spin"
          style={{ borderColor: `${brandColor} transparent transparent transparent` }}
        />
        <p className="text-sm text-gray-500">空き時間を確認しています…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-12 text-center text-sm text-red-500">{error}</div>
    );
  }

  if (daySlots.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-gray-500">
        現在ご案内できる日程がございません。<br />
        後日改めてご確認ください。
      </div>
    );
  }

  const currentDaySlots = daySlots.find(
    (d) => selectedDate && isSameDay(d.date, selectedDate)
  );

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        面接日程を選択してください
      </h2>

      {/* 日付タブ */}
      <div className="flex gap-2 overflow-x-auto pb-2 mb-6 scrollbar-hide">
        {daySlots.map((d) => {
          const isSelected = selectedDate && isSameDay(d.date, selectedDate);
          return (
            <button
              key={d.date.toISOString()}
              onClick={() => setSelectedDate(d.date)}
              className="flex-shrink-0 flex flex-col items-center px-4 py-2 rounded-xl border-2 transition-all text-sm font-medium"
              style={{
                borderColor: isSelected ? brandColor : '#E5E7EB',
                backgroundColor: isSelected ? brandColor : '#fff',
                color: isSelected ? '#fff' : '#374151',
              }}
            >
              <span className="text-xs opacity-80">
                {format(d.date, 'M/d', { locale: ja })}
              </span>
              <span>
                {format(d.date, 'EEE', { locale: ja })}
              </span>
            </button>
          );
        })}
      </div>

      {/* 時間スロット */}
      {currentDaySlots && (
        <div>
          <p className="text-sm text-gray-500 mb-3">
            {format(currentDaySlots.date, 'yyyy年M月d日(EEE)', { locale: ja })}
            の空き時間
          </p>
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
            {currentDaySlots.slots.map((slot) => (
              <SlotButton
                key={slot.start.toISOString()}
                slot={slot}
                brandColor={brandColor}
                onClick={() => slot.available && onSelect(slot)}
              />
            ))}
          </div>
        </div>
      )}

      <p className="mt-6 text-xs text-gray-400 text-center">
        ※ 日程は{company.slot_duration_minutes}分単位でご案内しています
      </p>
    </div>
  );
}

function SlotButton({
  slot,
  brandColor,
  onClick,
}: {
  slot: TimeSlot;
  brandColor: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={!slot.available}
      className="py-2.5 rounded-lg text-sm font-medium border-2 transition-all"
      style={
        slot.available
          ? {
              borderColor: brandColor,
              color: brandColor,
              backgroundColor: '#fff',
            }
          : {
              borderColor: '#E5E7EB',
              color: '#D1D5DB',
              backgroundColor: '#F9FAFB',
              cursor: 'not-allowed',
            }
      }
      onMouseEnter={(e) => {
        if (slot.available) {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = brandColor;
          (e.currentTarget as HTMLButtonElement).style.color = '#fff';
        }
      }}
      onMouseLeave={(e) => {
        if (slot.available) {
          (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#fff';
          (e.currentTarget as HTMLButtonElement).style.color = brandColor;
        }
      }}
    >
      {format(slot.start, 'HH:mm')}
    </button>
  );
}

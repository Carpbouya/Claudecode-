import { TimeSlot, DaySlots } from '@/types';
import { addDays, startOfDay, setHours, setMinutes, isBefore, isAfter } from 'date-fns';

// Google Calendar API から取得したバイジー時間帯の型
export interface FreeBusyEntry {
  start: string; // ISO 8601
  end: string;
}

// 営業時間設定
const WORK_HOURS = { start: 9, end: 18 }; // 9:00 ~ 18:00

/**
 * 指定期間の全スロット候補を生成し、バイジー時間帯を除外して返す。
 */
export function buildAvailableSlots(
  busyTimes: FreeBusyEntry[],
  slotDurationMinutes: number,
  bufferMinutes: number,
  daysAhead: number
): DaySlots[] {
  const now = new Date();
  const result: DaySlots[] = [];

  for (let d = 1; d <= daysAhead; d++) {
    const day = addDays(startOfDay(now), d);
    const dayOfWeek = day.getDay();

    // 土日はスキップ
    if (dayOfWeek === 0 || dayOfWeek === 6) continue;

    const slots: TimeSlot[] = [];
    let cursor = setMinutes(setHours(day, WORK_HOURS.start), 0);
    const dayEnd = setMinutes(setHours(day, WORK_HOURS.end), 0);

    while (isBefore(cursor, dayEnd)) {
      const slotEnd = new Date(cursor.getTime() + slotDurationMinutes * 60 * 1000);
      if (isAfter(slotEnd, dayEnd)) break;

      // バッファを含めた実際のブロック時間
      const blockStart = new Date(cursor.getTime() - bufferMinutes * 60 * 1000);
      const blockEnd = new Date(slotEnd.getTime() + bufferMinutes * 60 * 1000);

      const isAvailable = !busyTimes.some((busy) => {
        const busyStart = new Date(busy.start);
        const busyEnd = new Date(busy.end);
        return isBefore(blockStart, busyEnd) && isAfter(blockEnd, busyStart);
      });

      slots.push({ start: cursor, end: slotEnd, available: isAvailable });

      cursor = new Date(cursor.getTime() + slotDurationMinutes * 60 * 1000);
    }

    if (slots.some((s) => s.available)) {
      result.push({ date: day, slots });
    }
  }

  return result;
}

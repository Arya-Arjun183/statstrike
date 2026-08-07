/**
 * Utility for converting UK Premier League kickoff dates and times 
 * into the user's local browser timezone.
 */

export interface LocalMatchTime {
  formattedDate: string;
  formattedTime: string;
  fullLocalDisplay: string;
}

export function formatMatchDateTime(dateStr: string, timeStr?: string | null): LocalMatchTime {
  if (!dateStr) {
    return {
      formattedDate: '',
      formattedTime: timeStr || '',
      fullLocalDisplay: timeStr || '',
    };
  }

  // Parse date: support DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY
  let day = 1;
  let month = 1;
  let year = 2026;

  if (dateStr.includes('/')) {
    const parts = dateStr.split('/');
    if (parts.length === 3) {
      if (parts[0].length === 4) {
        // YYYY/MM/DD
        year = parseInt(parts[0], 10);
        month = parseInt(parts[1], 10);
        day = parseInt(parts[2], 10);
      } else {
        // DD/MM/YYYY
        day = parseInt(parts[0], 10);
        month = parseInt(parts[1], 10);
        year = parseInt(parts[2], 10);
      }
    }
  } else if (dateStr.includes('-')) {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      if (parts[0].length === 4) {
        // YYYY-MM-DD
        year = parseInt(parts[0], 10);
        month = parseInt(parts[1], 10);
        day = parseInt(parts[2], 10);
      } else {
        // DD-MM-YYYY
        day = parseInt(parts[0], 10);
        month = parseInt(parts[1], 10);
        year = parseInt(parts[2], 10);
      }
    }
  }

  // Parse time (default 15:00 UK if not provided)
  let hour = 15;
  let minute = 0;
  if (timeStr && timeStr.includes(':')) {
    const timeParts = timeStr.trim().split(':');
    hour = parseInt(timeParts[0], 10) || 15;
    minute = parseInt(timeParts[1], 10) || 0;
  }

  // Determine if date falls in British Summer Time (BST = UTC+1)
  // In the UK: BST starts on last Sunday of March (01:00 UTC) and ends on last Sunday of October (01:00 UTC)
  const isBST = (() => {
    const lastSunMarch = new Date(Date.UTC(year, 2, 31));
    lastSunMarch.setUTCDate(31 - lastSunMarch.getUTCDay());
    lastSunMarch.setUTCHours(1, 0, 0, 0);

    const lastSunOct = new Date(Date.UTC(year, 9, 31));
    lastSunOct.setUTCDate(31 - lastSunOct.getUTCDay());
    lastSunOct.setUTCHours(1, 0, 0, 0);

    const matchUtc = new Date(Date.UTC(year, month - 1, day, hour, minute, 0));
    return matchUtc >= lastSunMarch && matchUtc < lastSunOct;
  })();

  const offset = isBST ? '+01:00' : '+00:00';
  const isoString = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}T${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:00${offset}`;

  const dateObj = new Date(isoString);

  if (isNaN(dateObj.getTime())) {
    return {
      formattedDate: dateStr,
      formattedTime: timeStr || '',
      fullLocalDisplay: timeStr ? `${dateStr} • ${timeStr}` : dateStr,
    };
  }

  // Format in user's browser local timezone
  const formattedDate = dateObj.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  const formattedTime = dateObj.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  });

  return {
    formattedDate,
    formattedTime,
    fullLocalDisplay: `${formattedDate} • ${formattedTime}`,
  };
}

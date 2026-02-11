from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
import secrets

def pick_random_send_at_utc(now_utc, user_tz, min_days, max_days):
    tz = ZoneInfo(user_tz)
    now_local = now_utc.astimezone(tz)

    # 随机天数（CSPRNG）
    day_span = max_days - min_days + 1
    day_offset = min_days + secrets.randbelow(day_span)

    target_date = now_local.date() + timedelta(days=day_offset)

    # 09:00–21:00
    start_minutes = 9 * 60
    end_minutes = 21 * 60

    minute_of_day = start_minutes + secrets.randbelow(end_minutes - start_minutes)

    hh = minute_of_day // 60
    mm = minute_of_day % 60

    local_dt = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        hh,
        mm,
        tzinfo=tz,
    )

    return local_dt.astimezone(timezone.utc)

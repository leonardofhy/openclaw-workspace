#!/usr/bin/env python3
import sys
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'lib'))
from common import now as _now, MEMORY

# Config
CONFIG_PATH = MEMORY / 'weather_config.json'
DEFAULT_LOCATION = 'Taipei' # Coordinates: 25.0330, 121.5654

# Email: use shared utility (credentials in secrets/email_ops.env)
sys.path.insert(0, str(Path(__file__).parent))
from email_utils import send_email as _send_email_util

# Coordinates mapping (simple for now)
COORDS = {
    'Taipei': {'lat': 25.0330, 'lon': 121.5654},
    # Add more if needed
}

def get_location():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                data = json.load(f)
                return data.get('location', DEFAULT_LOCATION)
        except (IOError, json.JSONDecodeError, KeyError):
            pass
    return DEFAULT_LOCATION

def get_weather_desc(code):
    """Map WMO weather code to description."""
    mapping = {
        0: "晴朗 (Clear sky)",
        1: "多雲 (Mainly clear)",
        2: "多雲 (Partly cloudy)",
        3: "陰天 (Overcast)",
        45: "有霧 (Fog)",
        48: "有霧 (Fog)",
        51: "毛毛雨 (Drizzle)", 53: "毛毛雨 (Drizzle)", 55: "毛毛雨 (Drizzle)",
        61: "小雨 (Slight rain)", 63: "中雨 (Moderate rain)", 65: "大雨 (Heavy rain)",
        80: "陣雨 (Showers)", 81: "陣雨 (Showers)", 82: "暴雨 (Violent showers)",
        95: "雷雨 (Thunderstorm)", 96: "雷雨 (Thunderstorm)", 99: "雷雨 (Thunderstorm)"
    }
    return mapping.get(code, "未知天氣")

def get_weather(location):
    # Get coords
    coords = COORDS.get(location, COORDS['Taipei'])
    lat, lon = coords['lat'], coords['lon']
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max&timezone=Asia%2FTaipei"
    
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error fetching weather from Open-Meteo: {e}")
        return None

def analyze_weekend(weather_data):
    """Analyze if weekend weather is good."""
    if not weather_data or 'daily' not in weather_data:
        return None
        
    daily = weather_data['daily']
    times = daily.get('time', [])
    
    # We need to find Saturday and Sunday.
    # Assuming the script runs on Friday, Saturday is index 1, Sunday is index 2.
    # But let's be safer: parse dates.
    
    today_str = _now().strftime('%Y-%m-%d')
    try:
        today_idx = times.index(today_str)
    except ValueError:
        # If running late/timezone diff, fallback to 0=Today
        today_idx = 0
        
    # Check if we have enough data for Sat/Sun
    if len(times) <= today_idx + 2:
        return None
        
    sat_idx = today_idx + 1
    sun_idx = today_idx + 2
    
    indices = [('週六', sat_idx), ('週日', sun_idx)]
    good_days = []

    for name, idx in indices:
        rain_prob = daily['precipitation_probability_max'][idx]
        temp_max = daily['temperature_2m_max'][idx]
        temp_min = daily['temperature_2m_min'][idx]
        code = daily['weathercode'][idx]
        
        avg_temp = (temp_max + temp_min) / 2
        desc = get_weather_desc(code)
        
        # Criteria:
        # 1. Low rain probability (< 40%)
        # 2. Comfortable temp (15-32 C)
        is_dry = rain_prob < 40
        is_comfy = 15 <= avg_temp <= 32
        
        if is_dry: # Main criteria is dry weather
            good_days.append({
                'name': name,
                'desc': desc,
                'temp_range': f"{temp_min}-{temp_max}",
                'rain_prob': rain_prob
            })

    return good_days

def send_email(subject, body):
    return _send_email_util(subject, body, sender_label='Little Leo (欽天監)')

def main():
    loc = get_location()
    print(f"Checking weather for: {loc} (via Open-Meteo)...")
    
    data = get_weather(loc)
    if not data:
        print("No weather data available.")
        return

    good_days = analyze_weekend(data)
    
    if not good_days:
        print("🌧️ Weekend looks rainy or data insufficient. Staying quiet.")
        return

    # Prepare message
    subject = f"🌌 【欽天監】週末好天氣報報 ({loc})"
    body = f"Leo，週末天氣看起來不錯！\n\n"
    
    for d in good_days:
        body += f"✅ **{d['name']}**: {d['desc']}\n"
        body += f"   氣溫: {d['temp_range']}°C\n"
        body += f"   降雨機率: {d['rain_prob']}%\n\n"
        
    body += "💡 建議：\n"
    body += "- 適合去騎車兜風或去咖啡廳坐坐。\n"
    body += "- 記得把這段時間留給自己，不要只待在房間喔！\n"
    
    body += "\n-- Little Leo (欽天監) 🦁"
    
    print("Found good weather!")
    if send_email(subject, body):
        print("Notification sent successfully.")
    else:
        print("Failed to send notification.")

if __name__ == "__main__":
    main()

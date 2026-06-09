import os
import sys
import json
import requests
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event

# ==================== 1. 推广与变现配置区 (在此修改您的广告) ====================
# [广告位 A] 订阅日历的显示名称 (用户在日历列表里看到的标题，可加前缀/后缀)
CALENDAR_NAME = "2026美加墨世界杯赛程【关注公众号：球场瞭望台】"

# [广告位 B] 每个比赛详情底部的推广文案 (支持 Emoji 提升转化)
PROMO_TEXT_1 = "📺 2026世界杯高清免卡顿直播源 👉 https://yourdomain.com/live"
PROMO_TEXT_2 = "👕 官方正品球衣/观赛装备限时5折领券 👉 https://yourdomain.com/jersey"
PROMO_TEXT_3 = "✈️ 门票预订、酒店差旅全套省钱指南 👉 https://yourdomain.com/travel"

# [广告位 C] 每个事件关联的直达 URL (在 iOS 日历中可以直接点击)
PROMO_DIRECT_URL = "https://yourdomain.com/worldcup-guide"
# ==============================================================================

# 双数据源备份
PRIMARY_API = "https://worldcup26.ir/get/games"
FALLBACK_API = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.matches.json"

STADIUM_API = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.stadiums.json"

# 16个主办球场及本地时区映射
# 2026世界杯 16 个官方球场与城市的精确中文译名（含世界杯官方无赞助商命名对照）
STADIUM_INFO = {
    "1": {
        "name": "阿兹特克球场 (Estadio Azteca)",
        "city": "墨西哥城",
        "country": "墨西哥",
        "tz": "America/Mexico_City"
    },
    "2": {
        "name": "瓜达拉哈拉体育场 (Estadio Akron / Estadio Guadalajara)",
        "city": "瓜达拉哈拉",
        "country": "墨西哥",
        "tz": "America/Mexico_City"
    },
    "3": {
        "name": "蒙特雷体育场 (Estadio BBVA / Estadio Monterrey)",
        "city": "蒙特雷",
        "country": "墨西哥",
        "tz": "America/Monterrey"
    },
    "4": {
        "name": "达拉斯体育场 (AT&T Stadium / Dallas Stadium)",
        "city": "达拉斯 (阿灵顿)",
        "country": "美国",
        "tz": "America/Chicago"
    },
    "5": {
        "name": "休斯敦体育场 (NRG Stadium / Houston Stadium)",
        "city": "休斯敦",
        "country": "美国",
        "tz": "America/Chicago"
    },
    "6": {
        "name": "堪萨斯城体育场 (Arrowhead Stadium / Kansas City Stadium)",
        "city": "堪萨斯城",
        "country": "美国",
        "tz": "America/Chicago"
    },
    "7": {
        "name": "亚特兰大体育场 (Mercedes-Benz Stadium / Atlanta Stadium)",
        "city": "亚特兰大",
        "country": "美国",
        "tz": "America/New_York"
    },
    "8": {
        "name": "波士顿体育场 (Gillette Stadium / Boston Stadium)",
        "city": "波士顿 (福克斯堡)",
        "country": "美国",
        "tz": "America/New_York"
    },
    "9": {
        "name": "费城体育场 (Lincoln Financial Field / Philadelphia Stadium)",
        "city": "费城",
        "country": "美国",
        "tz": "America/New_York"
    },
    "10": {
        "name": "迈阿密体育场 (Hard Rock Stadium / Miami Stadium)",
        "city": "迈阿密",
        "country": "美国",
        "tz": "America/New_York"
    },
    "11": {
        "name": "纽约/新泽西体育场 (MetLife Stadium / New York New Jersey Stadium)",
        "city": "纽约/新泽西",
        "country": "美国",
        "tz": "America/New_York"
    },
    "12": {
        "name": "多伦多体育场 (BMO Field / Toronto Stadium)",
        "city": "多伦多",
        "country": "加拿大",
        "tz": "America/Toronto"
    },
    "13": {
        "name": "温哥华体育场 (BC Place / Vancouver Stadium)",
        "city": "温哥华",
        "country": "加拿大",
        "tz": "America/Vancouver"
    },
    "14": {
        "name": "洛杉矶体育场 (SoFi Stadium / Los Angeles Stadium)",
        "city": "洛杉矶 (因格尔伍德)",
        "country": "美国",
        "tz": "America/Los_Angeles"
    },
    "15": {
        "name": "旧金山湾区体育场 (Levi's Stadium / San Francisco Bay Area Stadium)",
        "city": "旧金山湾区 (圣克拉拉)",
        "country": "美国",
        "tz": "America/Los_Angeles"
    },
    "16": {
        "name": "西雅图体育场 (Lumen Field / Seattle Stadium)",
        "city": "西雅图",
        "country": "美国",
        "tz": "America/Los_Angeles"
    }
}

# 自动翻译字典
# 2026世界杯全部 48 支参赛球队（含常见缩写与拼写变体）中文翻译字典
TEAM_TRANSLATIONS = {
    # 主办国
    "USA": "美国",
    "United States": "美国",
    "United States of America": "美国",
    "Mexico": "墨西哥",
    "Canada": "加拿大",

    # A组
    "Korea Republic": "韩国",
    "Republic of Korea": "韩国",
    "South Korea": "韩国",
    "South Africa": "南非",
    "Czechia": "捷克",
    "Czech Republic": "捷克",

    # B组
    "Bosnia and Herzegovina": "波黑",
    "Bosnia & Herzegovina": "波黑",
    "Bosnia & Herz.": "波黑",
    "Bosnia": "波黑",
    "Qatar": "卡塔尔",
    "Switzerland": "瑞士",

    # C组
    "Brazil": "巴西",
    "Morocco": "摩洛哥",
    "Scotland": "苏格兰",
    "Haiti": "海地",

    # D组
    "Paraguay": "巴拉圭",
    "Australia": "澳大利亚",
    "Turkey": "土耳其",
    "Türkiye": "土耳其",

    # E组
    "Germany": "德国",
    "Ecuador": "厄瓜多尔",
    "Ivory Coast": "科特迪瓦",
    "Côte d'Ivoire": "科特迪瓦",
    "Curaçao": "库拉索",
    "Curacao": "库拉索",

    # F组
    "Netherlands": "荷兰",
    "Japan": "日本",
    "Sweden": "瑞典",
    "Tunisia": "突尼斯",

    # G组
    "Belgium": "比利时",
    "Egypt": "埃及",
    "Iran": "伊朗",
    "IR Iran": "伊朗",
    "Islamic Republic of Iran": "伊朗",
    "New Zealand": "新西兰",

    # H组
    "Spain": "西班牙",
    "Cape Verde": "佛得角",
    "Cabo Verde": "佛得角",
    "Saudi Arabia": "沙特阿拉伯",
    "Saudi": "沙特",
    "Uruguay": "乌拉圭",

    # I组
    "France": "法国",
    "Senegal": "塞内加尔",
    "Iraq": "伊拉克",
    "Norway": "挪威",

    # J组
    "Argentina": "阿根廷",
    "Algeria": "阿尔及利亚",
    "Austria": "奥地利",
    "Jordan": "约旦",

    # K组
    "Portugal": "葡萄牙",
    "DR Congo": "民主刚果",
    "Congo DR": "民主刚果",
    "Democratic Republic of the Congo": "民主刚果",
    "Uzbekistan": "乌兹别克斯坦",
    "Colombia": "哥伦比亚",

    # L组
    "England": "英格兰",
    "Croatia": "克罗地亚",
    "Ghana": "加纳",
    "Panama": "巴拿马"
}

STAGE_TRANSLATIONS = {
    "group": "小组赛", "r32": "1/16 决赛", "r16": "1/8 决赛", "qf": "1/4 决赛",
    "sf": "半决赛", "third": "三四名决赛", "final": "决赛"
}

def translate_team(name):
    if not name:
        return "待定"
    if name in TEAM_TRANSLATIONS:
        return TEAM_TRANSLATIONS[name]
    # 针对未确定队伍占位符进行汉化处理
    placeholders = {
        "Winner Group": "小组第一",
        "Runner-up Group": "小组第二",
        "Winner Match": "场次胜者",
        "Loser Match": "场次负者",
        "3rd Group": "小组第三",
    }
    translated = name
    for eng, chn in placeholders.items():
        translated = translated.replace(eng, chn)
    return translated

def fetch_data():
    # 尝试主数据源
    try:
        print("正在从主 API 获取比赛数据...")
        res = requests.get(PRIMARY_API, timeout=15)
        if res.status_code == 200:
            return res.json().get("games", [])
    except Exception as e:
        print(f"主 API 请求失败: {e}，正在切换至备用数据源...")
        
    # 尝试备用数据源
    try:
        res = requests.get(FALLBACK_API, timeout=15)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"备用数据源请求失败: {e}")
        sys.exit(1)

def generate_ics(matches):
    cal = Calendar()
    cal.add('prodid', '-//2026 World Cup Calendar//CN')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', CALENDAR_NAME)
    cal.add('x-wr-timezone', 'UTC')

    for match in matches:
        match_id = match.get("id")
        # 优先使用已定队伍英文名，其次使用占位符
        home_en = match.get("home_team_name_en") or match.get("home_team_label")
        away_en = match.get("away_team_name_en") or match.get("away_team_label")
        
        home_cn = translate_team(home_en)
        away_cn = translate_team(away_en)
        
        stage_raw = match.get("type", "group")
        stage_cn = STAGE_TRANSLATIONS.get(stage_raw, "世界杯比赛")
        
        # 场馆与城市解析
        stadium_id = str(match.get("stadium_id", "1"))
        venue_info = STADIUM_INFO.get(stadium_id, {"name": "美加墨体育场", "city": "主办城市", "tz": "America/New_York"})
        
        # 时间解析与 UTC 转换
        local_date_str = match.get("local_date")  # 格式: "06/11/2026 13:00"
        if not local_date_str:
            continue
            
        try:
            dt_local = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
            stadium_tz = pytz.timezone(venue_info["tz"])
            dt_localized = stadium_tz.localize(dt_local)
            dt_utc = dt_localized.astimezone(pytz.utc)
        except Exception as e:
            print(f"解析比赛时间出错 (ID: {match_id}): {e}")
            continue

        # 生成日历事件
        event = Event()
        
        # 实时状态展示：若比赛完结则直接在标题显示比分
        if match.get("finished") == "TRUE":
            score_str = f"({match.get('home_score')}:{match.get('away_score')})"
            event.add('summary', f"【已完赛】{home_cn} {score_str} {away_cn}")
        else:
            event.add('summary', f"🏆 {home_cn} vs {away_cn} | {stage_cn}")
            
        event.add('dtstart', dt_utc)
        event.add('dtend', dt_utc + timedelta(hours=2))  # 默认一场比赛时长为2小时
        event.add('dtstamp', datetime.now(pytz.utc))
        event.add('uid', f"wc2026-match-{match_id}@yourdomain.com")
        
        # 事件地点
        event.add('location', f"{venue_info['name']}, {venue_info['city']}")
        
        # 描述字段中注入变现广告链接
        description = (
            f"⚽ 世界杯对阵：{home_cn} vs {away_cn}\n"
            f"🏆 赛事阶段：{stage_cn}\n"
            f"📍 比赛场馆：{venue_info['name']} ({venue_info['city']})\n"
            f"🕒 当地开球时间：{local_date_str}\n\n"
            f"============================\n"
            f"{PROMO_TEXT_1}\n"
            f"{PROMO_TEXT_2}\n"
            f"{PROMO_TEXT_3}"
        )
        event.add('description', description)
        
        # URL 属性 (在 iOS 日历上直接可点)
        if PROMO_DIRECT_URL:
            event.add('url', PROMO_DIRECT_URL)
            
        cal.add_component(event)

    # 导出日历文件
    with open("worldcup2026.ics", "wb") as f:
        f.write(cal.to_ical())
    print("日历文件 worldcup2026.ics 生成完毕。")

if __name__ == "__main__":
    matches_data = fetch_data()
    if matches_data:
        generate_ics(matches_data)

import os
import sys
import json
import requests
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event

# ==================== 1. 推广与变现配置区 (在此修改您的广告) ====================
CALENDAR_NAME = "2026美加墨世界杯赛程"
PROMO_TEXT_1 = "📺 2026世界杯高清免卡顿直播 👉 https://tv.cctv.com/live/cctv5"
PROMO_TEXT_2 = "😋美团外卖大额红包 👉 http://dpurl.cn/PLhevzuz"
PROMO_TEXT_3 = "🧧京东618无门槛红包 👉 https://u.jd.com/7rFuhfR"
#PROMO_DIRECT_URL = "https://yourdomain.com/worldcup-guide"
# ==============================================================================

# 双数据源备份
PRIMARY_API = "https://worldcup26.ir/get/games"
FALLBACK_API = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.matches.json"
TEAMS_API = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.teams.json"

# 16个主办球场及本地时区映射
STADIUM_INFO = {
    "1": {"name": "阿兹特克球场 (Estadio Azteca)", "city": "墨西哥城", "tz": "America/Mexico_City"},
    "2": {"name": "瓜达拉哈拉体育场 (Estadio Akron / Estadio Guadalajara)", "city": "瓜达拉哈拉", "tz": "America/Mexico_City"},
    "3": {"name": "蒙特雷体育场 (Estadio BBVA / Estadio Monterrey)", "city": "蒙特雷", "tz": "America/Monterrey"},
    "4": {"name": "达拉斯体育场 (AT&T Stadium / Dallas Stadium)", "city": "达拉斯 (阿灵顿)", "tz": "America/Chicago"},
    "5": {"name": "休斯敦体育场 (NRG Stadium / Houston Stadium)", "city": "休斯敦", "tz": "America/Chicago"},
    "6": {"name": "堪萨斯城体育场 (Arrowhead Stadium / Kansas City Stadium)", "city": "堪萨斯城", "tz": "America/Chicago"},
    "7": {"name": "亚特兰大体育场 (Mercedes-Benz Stadium / Atlanta Stadium)", "city": "亚特兰大", "tz": "America/New_York"},
    "8": {"name": "波士顿体育场 (Gillette Stadium / Boston Stadium)", "city": "波士顿 (福克斯堡)", "tz": "America/New_York"},
    "9": {"name": "费城体育场 (Lincoln Financial Field / Philadelphia Stadium)", "city": "费城", "tz": "America/New_York"},
    "10": {"name": "迈阿密体育场 (Hard Rock Stadium / Miami Stadium)", "city": "迈阿密", "tz": "America/New_York"},
    "11": {"name": "纽约/新泽西体育场 (MetLife Stadium / New York New Jersey Stadium)", "city": "纽约/新泽西", "tz": "America/New_York"},
    "12": {"name": "多伦多体育场 (BMO Field / Toronto Stadium)", "city": "多伦多", "tz": "America/Toronto"},
    "13": {"name": "温哥华体育场 (BC Place / Vancouver Stadium)", "city": "温哥华", "tz": "America/Vancouver"},
    "14": {"name": "洛杉矶体育场 (SoFi Stadium / Los Angeles Stadium)", "city": "洛杉矶 (因格尔伍德)", "tz": "America/Los_Angeles"},
    "15": {"name": "旧金山湾区体育场 (Levi's Stadium / San Francisco Bay Area Stadium)", "city": "旧金山湾区 (圣克拉拉)", "tz": "America/Los_Angeles"},
    "16": {"name": "西雅图体育场 (Lumen Field / Seattle Stadium)", "city": "西雅图", "tz": "America/Los_Angeles"},
}

# 2026世界杯全部 48 支参赛球队
TEAM_TRANSLATIONS = {
    "USA": "美国", "United States": "美国", "Mexico": "墨西哥", "Canada": "加拿大",
    "Korea Republic": "韩国", "Republic of Korea": "韩国", "South Korea": "韩国",
    "South Africa": "南非", "Czechia": "捷克", "Czech Republic": "捷克",
    "Bosnia and Herzegovina": "波黑", "Bosnia & Herzegovina": "波黑", "Qatar": "卡塔尔", "Switzerland": "瑞士",
    "Brazil": "巴西", "Morocco": "摩洛哥", "Scotland": "苏格兰", "Haiti": "海地",
    "Paraguay": "巴拉圭", "Australia": "澳大利亚", "Turkey": "土耳其", "Türkiye": "土耳其",
    "Germany": "德国", "Ecuador": "厄瓜多尔", "Ivory Coast": "科特迪瓦", "Côte d'Ivoire": "科特迪瓦",
    "Curaçao": "库拉索", "Curacao": "库拉索", "Netherlands": "荷兰", "Japan": "日本", "Sweden": "瑞典", "Tunisia": "突尼斯",
    "Belgium": "比利时", "Egypt": "埃及", "Iran": "伊朗", "IR Iran": "伊朗", "New Zealand": "新西兰",
    "Spain": "西班牙", "Cape Verde": "佛得角", "Cabo Verde": "佛得角", "Saudi Arabia": "沙特", "Uruguay": "乌拉圭",
    "France": "法国", "Senegal": "塞内加尔", "Iraq": "伊拉克", "Norway": "挪威",
    "Argentina": "阿根廷", "Algeria": "阿尔及利亚", "Austria": "奥地利", "Jordan": "约旦",
    "Portugal": "葡萄牙", "DR Congo": "民主刚果", "Congo DR": "民主刚果", "Uzbekistan": "乌兹别克斯坦", "Colombia": "哥伦比亚",
    "England": "英格兰", "Croatia": "克罗地亚", "Ghana": "加纳", "Panama": "巴拿马",
    "Democratic Republic of Congo": "民主刚果", "Democratic Republic of the Congo": "民主刚果",
    "Congo, Dem. Rep.": "民主刚果", "Congo, DR": "民主刚果"
}

STAGE_TRANSLATIONS = {
    "group": "小组赛", "r32": "1/16 决赛", "r16": "1/8 决赛", "qf": "1/4 决赛",
    "sf": "半决赛", "third": "三四名决赛", "final": "决赛"
}

def translate_team(name):
    if not name:
        return "待定"
    
    name_clean = str(name).strip().lower()
    lower_translations = {k.lower(): v for k, v in TEAM_TRANSLATIONS.items()}
    
    if name_clean in lower_translations:
        return lower_translations[name_clean]
    
    placeholders = {
        "winner group": "小组第一",
        "runner-up group": "小组第二",
        "winner match": "场次胜者",
        "loser match": "场次负者",
        "3rd group": "小组第三",
    }
    translated = name
    for eng, chn in placeholders.items():
        if eng in name_clean:
            import re
            insens_re = re.compile(re.escape(eng), re.IGNORECASE)
            translated = insens_re.sub(chn, translated)
    return translated

def fetch_data():
    team_id_map = {}
    try:
        print("正在从 GitHub 预载 48 支队伍的 ID 映射...")
        res = requests.get(TEAMS_API, timeout=10)
        if res.status_code == 200:
            data = res.json()
            teams_list = data.get("teams", data) if isinstance(data, dict) else data
            for t in teams_list:
                team_id_map[str(t.get("id"))] = t.get("name_en")
            print("队伍 ID 映射加载成功！")
    except Exception as e:
        print(f"队伍映射加载失败 (程序将依靠硬编码字段): {e}")

    try:
        print("正在从主 API 获取比赛数据...")
        res = requests.get(PRIMARY_API, timeout=15)
        if res.status_code == 200:
            return res.json().get("games", []), team_id_map
    except Exception as e:
        print(f"主 API 请求失败: {e}，正在切换至备用数据源...")
        
    try:
        res = requests.get(FALLBACK_API, timeout=15)
        if res.status_code == 200:
            return res.json(), team_id_map
    except Exception as e:
        print(f"备用数据源请求失败: {e}")
        sys.exit(1)

def generate_ics(matches, team_id_map):
    cal_name = globals().get('CALENDAR_NAME', "2026美加墨世界杯赛程")
    promo_t1 = globals().get('PROMO_TEXT_1', "")
    promo_t2 = globals().get('PROMO_TEXT_2', "")
    promo_t3 = globals().get('PROMO_TEXT_3', "")
    promo_url = globals().get('PROMO_DIRECT_URL', "")

    cal = Calendar()
    cal.add('prodid', '-//2026 World Cup Calendar//CN')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', cal_name)
    cal.add('x-wr-timezone', 'UTC')

    for match in matches:
        match_id = match.get("id")
        stadium_id = str(match.get("stadium_id", "1"))
        venue_info = STADIUM_INFO.get(stadium_id, {"name": "美加墨体育场", "city": "主办城市", "tz": "America/Mexico_City"})

        # 精准组装队伍英文名
        home_en = match.get("home_team_name_en")
        if not home_en:
            home_id = str(match.get("home_team_id", ""))
            home_en = team_id_map.get(home_id) or match.get("home_team_label")
            
        away_en = match.get("away_team_name_en")
        if not away_en:
            away_id = str(match.get("away_team_id", ""))
            away_en = team_id_map.get(away_id) or match.get("away_team_label")
        
        home_cn = translate_team(home_en)
        away_cn = translate_team(away_en)
        
        # 提取分组和阶段信息
        group_letter = match.get("group")
        stage_raw = match.get("type", "group")
        stage_cn = STAGE_TRANSLATIONS.get(stage_raw, "世界杯比赛")
        
        # 动态拼装标题
        if stage_raw == "group" and group_letter:
            stage_display = f"小组赛 ({group_letter}组)"
            summary_title = f"🏆 {group_letter}组 | {home_cn} vs {away_cn}"
        else:
            stage_display = stage_cn
            summary_title = f"🏆 {stage_cn} | {home_cn} vs {away_cn}"
        
        local_date_str = match.get("local_date")
        if not local_date_str:
            continue
            
        try:
            dt_local = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
            stadium_tz = pytz.timezone(venue_info["tz"])
            dt_localized = stadium_tz.localize(dt_local)
            dt_utc = dt_localized.astimezone(pytz.utc)
        except Exception as e:
            dt_local = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
            stadium_tz = pytz.timezone("America/Mexico_City")
            dt_localized = stadium_tz.localize(dt_local)
            dt_utc = dt_localized.astimezone(pytz.utc)

        event = Event()
        
        # 🟢 【核心修复：高容错完赛判断机制】
        # 兼容处理各种数据类型：支持布尔值 (True/False)、大小写字符串 ("TRUE"/"true")、数值 (1/0)
        finished_val = match.get("finished")
        is_finished = False
        if isinstance(finished_val, bool):
            is_finished = finished_val
        elif isinstance(finished_val, str):
            is_finished = finished_val.strip().upper() in ["TRUE", "YES", "1"]
        elif isinstance(finished_val, (int, float)):
            is_finished = int(finished_val) == 1
            
        if is_finished:
            # 兼容读取比分：防止 null 字符串和空值引发格式问题
            h_score = match.get("home_score")
            a_score = match.get("away_score")
            h_score = "0" if h_score is None or str(h_score).strip().lower() == "null" else str(h_score)
            a_score = "0" if a_score is None or str(a_score).strip().lower() == "null" else str(a_score)
            
            event.add('summary', f"【已完赛】{home_cn} ({h_score}:{a_score}) {away_cn}")
        else:
            event.add('summary', summary_title)
            
        event.add('dtstart', dt_utc)
        event.add('dtend', dt_utc + timedelta(hours=2))
        event.add('dtstamp', datetime.now(pytz.utc))
        event.add('uid', f"wc2026-match-{match_id}@yourdomain.com")
        event.add('location', f"{venue_info['name']}, {venue_info['city']}")
        
        description = (
            f"⚽ 世界杯对阵：{home_cn} vs {away_cn}\n"
            f"🏆 赛事阶段：{stage_display}\n"
            f"📍 比赛场馆：{venue_info['name']} ({venue_info['city']})\n"
            f"🕒 现场开球时间：{local_date_str} (当地时间)\n\n"
            f"============================\n"
            f"{promo_t1}\n"
            f"{promo_t2}\n"
            f"{promo_t3}"
        )
        event.add('description', description)
        
        if promo_url:
            event.add('url', promo_url)
            
        cal.add_component(event)

    with open("worldcup2026.ics", "wb") as f:
        f.write(cal.to_ical())
    print("日历文件 worldcup2026.ics 生成完毕。")

if __name__ == "__main__":
    matches_data, team_id_map = fetch_data()
    if matches_data:
        generate_ics(matches_data, team_id_map)

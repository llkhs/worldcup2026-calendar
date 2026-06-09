import os
import sys
import json
import requests
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar, Event

# ==================== 1. 推广与变现配置区 ====================
CALENDAR_NAME = "2026美加墨世界杯赛程【关注公众号：球场瞭望台】"
PROMO_TEXT_1 = "📺 2026世界杯高清免卡顿直播源 👉 https://yourdomain.com/live"
PROMO_TEXT_2 = "👕 官方正品球衣/观赛装备限时5折领券 👉 https://yourdomain.com/jersey"
PROMO_TEXT_3 = "✈️ 门票预订、酒店差旅全套省钱指南 👉 https://yourdomain.com/travel"
PROMO_DIRECT_URL = "https://yourdomain.com/worldcup-guide"
# ==============================================================

# 双数据源备份
PRIMARY_API = "https://worldcup26.ir/get/games"
FALLBACK_API = "https://raw.githubusercontent.com/rezarahiminia/worldcup2026/main/football.matches.json"

# 用于容灾合并国家名字的数据源
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

# 2026世界杯全部 48 支参赛球队中文翻译字典
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
    "England": "英格兰", "Croatia": "克罗地亚", "Ghana": "加纳", "Panama": "巴拿马"
    "Democratic Republic of Congo": "民主刚果",
    "Democratic Republic of the Congo": "民主刚果",
    "Congo, Dem. Rep.": "民主刚果",
    "Congo, DR": "民主刚果",
    "DR Congo": "民主刚果",
    "Congo DR": "民主刚果"
}

STAGE_TRANSLATIONS = {
    "group": "小组赛", "r32": "1/16 决赛", "r16": "1/8 决赛", "qf": "1/4 决赛",
    "sf": "半决赛", "third": "三四名决赛", "final": "决赛"
}

# 模糊翻译匹配函数（支持大小写、多余空格自动校准）
def translate_team(name):
    if not name:
        return "待定"
    
    # 去除两端空格并转为全小写进行安全匹配
    name_clean = str(name).strip().lower()
    lower_translations = {k.lower(): v for k, v in TEAM_TRANSLATIONS.items()}
    
    if name_clean in lower_translations:
        return lower_translations[name_clean]
    
    # 针对未确定队伍占位符进行汉化处理
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
    # 1. 尝试先加载队伍名字映射
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

    # 2. 拉取主 API
    try:
        print("正在从主 API 获取比赛数据...")
        res = requests.get(PRIMARY_API, timeout=15)
        if res.status_code == 200:
            return res.json().get("games", []), team_id_map
    except Exception as e:
        print(f"主 API 请求失败: {e}，正在切换至备用数据源...")
        
    # 3. 拉取备用 API
    try:
        res = requests.get(FALLBACK_API, timeout=15)
        if res.status_code == 200:
            return res.json(), team_id_map
    except Exception as e:
        print(f"备用数据源请求失败: {e}")
        sys.exit(1)

def generate_ics(matches, team_id_map):
    cal = Calendar()
    cal.add('prodid', '-//2026 World Cup Calendar//CN')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', CALENDAR_NAME)
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
        
        stage_raw = match.get("type", "group")
        stage_cn = STAGE_TRANSLATIONS.get(stage_raw, "世界杯比赛")
        
        # 比赛时间解析
        local_date_str = match.get("local_date")  # 格式: "06/11/2026 13:00"
        if not local_date_str:
            continue
            
        try:
            dt_local = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
            stadium_tz = pytz.timezone(venue_info["tz"])
            # 本地时间实例化
            dt_localized = stadium_tz.localize(dt_local)
            # 全球统一转为标准 UTC 时间
            dt_utc = dt_localized.astimezone(pytz.utc)
            # 打印控制台日志（方便调试）
            print(f"✅ [场次 {match_id}] {home_cn} vs {away_cn} | 当地时间: {local_date_str} ({venue_info['city']}) -> 已成功校准为 UTC: {dt_utc.strftime('%Y-%m-%d %H:%M:%S')}Z")
        except Exception as e:
            # 安全防崩溃：若时区解析完全失败，默认以美加墨主时区 America/Mexico_City 进行校准
            dt_local = datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
            stadium_tz = pytz.timezone("America/Mexico_City")
            dt_localized = stadium_tz.localize(dt_local)
            dt_utc = dt_localized.astimezone(pytz.utc)
            print(f"⚠️ [场次 {match_id}] 转换发生意外，已启用安全时区校准。")

        event = Event()
        
        if match.get("finished") == "TRUE":
            score_str = f"({match.get('home_score')}:{match.get('away_score')})"
            event.add('summary', f"【已完赛】{home_cn} {score_str} {away_cn}")
        else:
            event.add('summary', f"🏆 {home_cn} vs {away_cn} | {stage_cn}")
            
        event.add('dtstart', dt_utc)
        event.add('dtend', dt_utc + timedelta(hours=2))
        event.add('dtstamp', datetime.now(pytz.utc))
        event.add('uid', f"wc2026-match-{match_id}@yourdomain.com")
        event.add('location', f"{venue_info['name']}, {venue_info['city']}")
        
        description = (
            f"⚽ 世界杯对阵：{home_cn} vs {away_cn}\n"
            f"🏆 赛事阶段：{stage_cn}\n"
            f"📍 比赛场馆：{venue_info['name']} ({venue_info['city']})\n"
            f"🕒 现场开球时间：{local_date_str} (当地时间)\n\n"
            f"============================\n"
            f"{PROMO_TEXT_1}\n"
            f"{PROMO_TEXT_2}\n"
            f"{PROMO_TEXT_3}"
        )
        event.add('description', description)
        
        if PROMO_DIRECT_URL:
            event.add('url', PROMO_DIRECT_URL)
            
        cal.add_component(event)

    with open("worldcup2026.ics", "wb") as f:
        f.write(cal.to_ical())
    print("日历文件 worldcup2026.ics 生成完毕。")

if __name__ == "__main__":
    matches_data, team_id_map = fetch_data()
    if matches_data:
        generate_ics(matches_data, team_id_map)

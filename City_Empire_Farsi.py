# -*- coding: utf-8 -*-

# City Empire - ربات شهرسازی فارسی برای بله

# نصب نیازمندی: python -m pip install requests



import os 

import sys

if hasattr(sys.stdout, "reconfigure"):

    sys.stdout.reconfigure(

        encoding="utf-8",

        errors="replace"

    )

import json

import time

import random

import threading

from pathlib import Path



import requests



# ==================================================

# تنظیمات امنیتی

# ==================================================



import os

TOKEN = os.getenv("", "1999799698:MllR_EsRqGkWqGC-eXofdSIBSufpiUmM2P4").strip()

API_BASE = (
    f"https://tapi.bale.ai/bot{TOKEN}/"
    if TOKEN else ""
)



DATA_FILE = Path(__file__).resolve().parent / "players.json"

TEMP_FILE = DATA_FILE.with_suffix(".json.tmp")

BACKUP_FILE = DATA_FILE.with_suffix(".json.bak")



WAREHOUSE_CAPACITY = 500

MAX_WORKERS = 50

ATTACK_COOLDOWN = 60

DAILY_COOLDOWN = 24 * 60 * 60

SHIELD_DURATION = 30 * 60



SAVE_LOCK = threading.RLock()

PLAYERS_LOCK = threading.RLock()

HTTP = requests.Session()



# ==================================================

# داده‌های اولیه

# ==================================================



PLAYER_DEFAULTS = {

    "name": "فرمانده",

    "gold": 300,

    "wood": 100,

    "iron": 50,

    "food": 100,

    "soldiers": 10,

    "houses": 1,

    "citizens": 10,

    "honor": 0,

    "dragons": 0,

    "xp": 0,

    "level": 1,

    "workers": {

        "woodcutter": 0,

        "miner": 0,

        "farmer": 0,

    },

    "last_daily": 0,

    "last_attack": 0,

    "shield_until": 0,

    "last_production": 0,

}



RESOURCE_NAMES = {

    "gold": "سکه",

    "wood": "چوب",

    "iron": "آهن",

    "food": "غذا",

}



MAIN_KEYBOARD = [

    ["🏙 شهر من", "📊 آمار شهر"],

    ["🪓 تولید منابع", "🏠 ساخت خانه"],

    ["🛒 فروشگاه", "🧑‍🏭 مدیریت کارگران"],

    ["⚔️ نبرد", "🐉 اژدها"],

    ["🎁 جایزه روزانه", "🏆 رتبه‌بندی"],

    ["🛡 سپر دفاعی", "❓ راهنما"],

]



SHOP_KEYBOARD = [

    ["🪵 خرید چوب", "⛓ خرید آهن"],

    ["🍞 خرید غذا", "⚔️ استخدام سرباز"],

    ["🔙 منوی اصلی"],

]



WORKER_KEYBOARD = [

    ["👷 کارگر چوب", "⛏ کارگر معدن"],

    ["🌾 کارگر مزرعه", "📋 کارگران من"],

    ["🔙 منوی اصلی"],

]



# ==================================================

# ذخیره‌سازی و بازیابی

# ==================================================



def make_default_player(name="فرمانده"):

    player = json.loads(json.dumps(PLAYER_DEFAULTS))

    player["name"] = str(name or "فرمانده")[:40]

    player["last_production"] = int(time.time())

    return player





def load_players():

    """فایل اصلی و در صورت نیاز نسخه پشتیبان را امتحان می‌کند."""

    if not DATA_FILE.exists():

        return {}



    errors = []



    for path in (DATA_FILE, BACKUP_FILE):

        if not path.exists():

            continue



        try:

            with path.open("r", encoding="utf-8") as file:

                data = json.load(file)



            if not isinstance(data, dict):

                raise ValueError("ساختار فایل باید دیکشنری باشد.")



            if path == BACKUP_FILE:

                print("هشدار: اطلاعات از نسخه پشتیبان بازیابی شدند.")



            return data



        except (OSError, ValueError, json.JSONDecodeError) as error:

            errors.append(f"{path.name}: {error}")



    raise RuntimeError(

        "فایل اطلاعات بازیکنان خراب یا غیرقابل‌خواندن است. "

        "فایل را حذف نکن؛ آن را بررسی کن یا از نسخه پشتیبان استفاده کن. "

        + " | ".join(errors)

    )





players = load_players()





def save_players():

    """ابتدا فایل موقت می‌نویسد و سپس فایل اصلی را جایگزین می‌کند."""

    with SAVE_LOCK:

        try:

            DATA_FILE.parent.mkdir(parents=True, exist_ok=True)



            with TEMP_FILE.open("w", encoding="utf-8") as file:

                json.dump(

                    players,

                    file,

                    ensure_ascii=False,

                    indent=2,

                )

                file.flush()

                os.fsync(file.fileno())



            # نسخه پشتیبان از فایل سالم قبلی

            if DATA_FILE.exists():

                try:

                    backup_temp = BACKUP_FILE.with_suffix(".bak.tmp")

                    with DATA_FILE.open("rb") as source:

                        with backup_temp.open("wb") as target:

                            while True:

                                chunk = source.read(1024 * 1024)

                                if not chunk:

                                    break

                                target.write(chunk)

                            target.flush()

                            os.fsync(target.fileno())

                    os.replace(backup_temp, BACKUP_FILE)

                except OSError as error:

                    print(f"هشدار: ساخت نسخه پشتیبان ناموفق بود: {error}")



            os.replace(TEMP_FILE, DATA_FILE)



        except (OSError, TypeError, ValueError) as error:

            print(f"خطا در ذخیره اطلاعات: {error}")

            raise





def get_player(user_id, name=""):

    key = str(user_id)



    with PLAYERS_LOCK:

        if key not in players or not isinstance(players[key], dict):

            players[key] = make_default_player(name)



        p = players[key]



        # افزودن فیلدهای جدید بدون حذف اطلاعات قدیمی

        for field, default in PLAYER_DEFAULTS.items():

            if field not in p:

                p[field] = json.loads(json.dumps(default))



        if not isinstance(p.get("workers"), dict):

            p["workers"] = {}



        for job in ("woodcutter", "miner", "farmer"):

            try:

                p["workers"][job] = max(0, int(p["workers"].get(job, 0)))

            except (TypeError, ValueError):

                p["workers"][job] = 0



        for field in (

            "gold", "wood", "iron", "food", "soldiers",

            "houses", "citizens", "honor", "dragons",

            "xp", "level", "last_daily", "last_attack",

            "shield_until", "last_production",

        ):

            try:

                p[field] = max(0, int(p[field]))

            except (TypeError, ValueError):

                p[field] = int(PLAYER_DEFAULTS[field])



        p["level"] = max(1, p["level"])



        if name:

            p["name"] = str(name)[:40]



        return p





# ==================================================

# ارتباط با API بله

# ==================================================



def api_call(method, payload=None, timeout=35):

    if not TOKEN:

        raise RuntimeError(

            "توکن تنظیم نشده است. متغیر محیطی BALE_BOT_TOKEN را تنظیم کن."

        )



    response = HTTP.post(

        API_BASE + method,

        json=payload or {},

        timeout=timeout,

    )

    response.raise_for_status()



    data = response.json()

    if not isinstance(data, dict) or not data.get("ok"):

        raise RuntimeError(

            data.get("description", "پاسخ نامعتبر از سرور بله")

            if isinstance(data, dict)

            else "پاسخ نامعتبر از سرور بله"

        )



    return data.get("result", [])





def send_message(chat_id, text, keyboard=None):

    payload = {

        "chat_id": chat_id,

        "text": str(text)[:4000],

    }



    if keyboard:

        payload["reply_markup"] = {

            "keyboard": [

                [{"text": item} for item in row]

                for row in keyboard

            ],

            "resize_keyboard": True,

        }



    try:

        api_call("sendMessage", payload)

    except (requests.RequestException, ValueError, RuntimeError) as error:

        print(f"ارسال پیام ناموفق بود: {error}")





def main_menu(chat_id, message="به امپراتوری شهر خوش آمدی!"):

    send_message(chat_id, message, MAIN_KEYBOARD)





# ==================================================

# منابع، انبار و تجربه

# ==================================================



def warehouse_used(p):

    return sum(max(0, int(p[k])) for k in ("wood", "iron", "food"))





def free_capacity(p):

    return max(0, WAREHOUSE_CAPACITY - warehouse_used(p))





def add_resource(p, resource, amount):

    amount = max(0, int(amount))



    if resource == "gold":

        p["gold"] += amount

        return amount



    actual = min(amount, free_capacity(p))

    p[resource] += actual

    return actual





def total_workers(p):

    return sum(p["workers"].values())





def update_production(p):

    now = int(time.time())

    last = int(p.get("last_production", now))

    elapsed = min(8 * 3600, max(0, now - last))

    p["last_production"] = now



    if elapsed < 3600:

        return



    hours = elapsed / 3600



    rates = {

        "woodcutter": ("wood", 5),

        "miner": ("iron", 3),

        "farmer": ("food", 6),

    }



    for job, (resource, rate) in rates.items():

        amount = int(p["workers"].get(job, 0) * rate * hours)

        add_resource(p, resource, amount)





def grant_xp(p, amount):

    p["xp"] += max(0, int(amount))

    messages = []



    while p["xp"] >= p["level"] * 100:

        p["xp"] -= p["level"] * 100

        p["level"] += 1

        p["gold"] += 50

        messages.append(

            f"🎉 سطح شهر به {p['level']} رسید؛ ۵۰ سکه جایزه گرفتی."

        )



    return "\n".join(messages)





def city_text(p):

    return (

        f"🏙 شهر: {p['name']}\n"

        f"⭐ سطح: {p['level']} | تجربه: {p['xp']}\n\n"

        f"🪙 سکه: {p['gold']}\n"

        f"🪵 چوب: {p['wood']}\n"

        f"⛓ آهن: {p['iron']}\n"

        f"🍞 غذا: {p['food']}\n"

        f"⚔️ سرباز: {p['soldiers']}\n"

        f"🏠 خانه: {p['houses']}\n"

        f"👥 شهروند: {p['citizens']}\n"

        f"🐉 اژدها: {p['dragons']}\n"

        f"🏅 افتخار: {p['honor']}\n"

        f"📦 انبار: {warehouse_used(p)}/{WAREHOUSE_CAPACITY}"

    )





# ==================================================

# کارگران

# ==================================================



def workers_text(p):

    w = p["workers"]

    return (

        "🧑‍🏭 مدیریت کارگران\n"

        f"کارگران: {total_workers(p)}/{MAX_WORKERS}\n\n"

        f"🪵 کارگر چوب: {w['woodcutter']} — هر ساعت ۵ چوب\n"

        f"⛏ کارگر معدن: {w['miner']} — هر ساعت ۳ آهن\n"

        f"🌾 کشاورز: {w['farmer']} — هر ساعت ۶ غذا\n\n"

        "استخدام هر کارگر: ۲۰ سکه"

    )





def hire_worker(chat_id, p, job):

    if total_workers(p) >= MAX_WORKERS:

        send_message(chat_id, "ظرفیت کارگران پر است.", WORKER_KEYBOARD)

        return



    if p["gold"] < 20:

        send_message(chat_id, "برای استخدام کارگر به ۲۰ سکه نیاز داری.", WORKER_KEYBOARD)

        return



    p["gold"] -= 20

    p["workers"][job] += 1

    save_players()



    send_message(chat_id, "✅ کارگر استخدام شد.\n\n" + workers_text(p), WORKER_KEYBOARD)





# ==================================================

# فروشگاه و ساخت‌وساز

# ==================================================



def buy_resource(chat_id, p, resource, amount, price):

    if p["gold"] < price:

        send_message(chat_id, f"سکه کافی نداری؛ قیمت خرید {price} سکه است.", SHOP_KEYBOARD)

        return



    actual = min(amount, free_capacity(p))

    if actual <= 0:

        send_message(chat_id, "📦 انبار پر است؛ اول از منابع استفاده کن.", SHOP_KEYBOARD)

        return



    p["gold"] -= price

    p[resource] += actual

    save_players()



    send_message(

        chat_id,

        f"✅ {actual} واحد {RESOURCE_NAMES[resource]} خریدی.\n"

        f"سکه باقی‌مانده: {p['gold']}\n"

        f"فضای خالی انبار: {free_capacity(p)}",

        SHOP_KEYBOARD,

    )





def build_house(chat_id, p):

    wood_cost = 30

    iron_cost = 10

    gold_cost = 80



    if (

        p["wood"] < wood_cost

        or p["iron"] < iron_cost

        or p["gold"] < gold_cost

    ):

        send_message(

            chat_id,

            "منابع کافی نیست.\n"

            "هزینه ساخت: ۳۰ چوب، ۱۰ آهن و ۸۰ سکه.\n\n"

            + city_text(p),

        )

        return



    p["wood"] -= wood_cost

    p["iron"] -= iron_cost

    p["gold"] -= gold_cost

    p["houses"] += 1

    p["citizens"] += random.randint(2, 5)

    p["honor"] += 2



    level_message = grant_xp(p, 25)

    save_players()



    send_message(

        chat_id,

        "🏠 خانه ساخته شد و شهروندان تازه‌ای به شهر آمدند!\n"

        + level_message + "\n\n" + city_text(p),

        MAIN_KEYBOARD,

    )





# ==================================================

# جایزه روزانه و رتبه‌بندی

# ==================================================



def daily_reward(chat_id, p):

    now = int(time.time())

    remaining = DAILY_COOLDOWN - (now - p["last_daily"])



    if remaining > 0:

        hours = remaining // 3600

        minutes = (remaining % 3600) // 60

        send_message(

            chat_id,

            f"🎁 جایزه را قبلاً گرفتی؛ {hours} ساعت و {minutes} دقیقه دیگر برگرد.",

        )

        return



    reward = random.randint(80, 140)

    p["gold"] += reward

    food_added = add_resource(p, "food", 30)

    p["last_daily"] = now

    level_message = grant_xp(p, 10)

    save_players()



    send_message(

        chat_id,

        f"🎁 جایزه روزانه: {reward} سکه و {food_added} غذا!\n"

        + level_message,

        MAIN_KEYBOARD,

    )





def show_ranking(chat_id):

    with PLAYERS_LOCK:

        ranked = sorted(

            players.items(),

            key=lambda item: (

                int(item[1].get("level", 1)),

                int(item[1].get("honor", 0)),

                int(item[1].get("gold", 0)),

            ),

            reverse=True,

        )[:10]



    if not ranked:

        send_message(chat_id, "هنوز بازیکنی در رتبه‌بندی نیست.")

        return



    lines = ["🏆 ده شهر برتر"]

    for number, (_, p) in enumerate(ranked, 1):

        lines.append(

            f"{number}. {p.get('name', 'شهر بی‌نام')} — "

            f"سطح {p.get('level', 1)} | افتخار {p.get('honor', 0)}"

        )



    send_message(chat_id, "\n".join(lines))





# ==================================================

# نبرد و اژدها

# ==================================================



def attack_player(chat_id, user_id, attacker):

    now = int(time.time())

    remaining = ATTACK_COOLDOWN - (now - attacker["last_attack"])



    if remaining > 0:

        send_message(chat_id, f"⏳ برای نبرد بعدی {remaining} ثانیه صبر کن.")

        return



    if attacker["soldiers"] < 3:

        send_message(chat_id, "برای نبرد حداقل ۳ سرباز لازم داری.")

        return



    with PLAYERS_LOCK:

        candidates = [

            (uid, p)

            for uid, p in players.items()

            if uid != str(user_id)

            and int(p.get("soldiers", 0)) >= 1

        ]



        if not candidates:

            send_message(chat_id, "فعلاً حریفی برای نبرد پیدا نشد.")

            return



        _, defender = random.choice(candidates)



        if int(defender.get("shield_until", 0)) > now:

            send_message(chat_id, "🛡 حریف انتخاب‌شده سپر دفاعی دارد؛ بعداً دوباره تلاش کن.")

            return



        attacker["last_attack"] = now

        attacker_loss = random.randint(1, min(3, attacker["soldiers"]))

        defender_loss = random.randint(1, min(4, defender["soldiers"]))



        attacker["soldiers"] -= attacker_loss

        defender["soldiers"] -= defender_loss



        loot = min(defender["gold"], random.randint(10, 40))

        defender["gold"] -= loot

        attacker["gold"] += loot

        attacker["honor"] += 5



        level_message = grant_xp(attacker, 20)

        defender_name = defender.get("name", "شهر بی‌نام")



    save_players()



    send_message(

        chat_id,

        f"⚔️ نبرد با شهر «{defender_name}» تمام شد!\n"

        f"سربازان از دست‌رفته تو: {attacker_loss}\n"

        f"سربازان از دست‌رفته حریف: {defender_loss}\n"

        f"غنیمت: {loot} سکه\n"

        f"🏅 ۵ افتخار گرفتی.\n{level_message}",

        MAIN_KEYBOARD,

    )





def dragon_fight(chat_id, p):

    if p["soldiers"] < 5 or p["food"] < 20:

        send_message(chat_id, "برای مبارزه حداقل ۵ سرباز و ۲۰ غذا لازم داری.")

        return



    p["food"] -= 20

    lost = random.randint(1, min(3, p["soldiers"]))

    p["soldiers"] -= lost



    chance = min(0.85, 0.35 + p["level"] * 0.025)



    if random.random() < chance:

        p["dragons"] += 1

        p["gold"] += 100

        p["honor"] += 10

        level_message = grant_xp(p, 35)

        result = "🐉 پیروز شدی! یک اژدها، ۱۰۰ سکه و ۱۰ افتخار گرفتی."

    else:

        level_message = ""

        result = "🐲 اژدها شکستت داد و بخشی از سربازانت را از دست دادی."



    save_players()

    send_message(

        chat_id,

        result + f"\nسربازان از دست‌رفته: {lost}\n"

        + level_message + "\n\n" + city_text(p),

        MAIN_KEYBOARD,

    )





def activate_shield(chat_id, p):

    now = int(time.time())



    if p["shield_until"] > now:

        remaining = p["shield_until"] - now

        send_message(chat_id, f"🛡 سپر فعال است؛ {remaining // 60} دقیقه باقی مانده.")

        return



    if p["gold"] < 100:

        send_message(chat_id, "برای سپر دفاعی به ۱۰۰ سکه نیاز داری.")

        return



    p["gold"] -= 100

    p["shield_until"] = now + SHIELD_DURATION

    save_players()



    send_message(chat_id, "🛡 سپر دفاعی برای ۳۰ دقیقه فعال شد.", MAIN_KEYBOARD)





# ==================================================

# راهنما و مدیریت پیام‌ها

# ==================================================



def help_text():

    return (

        "❓ راهنمای امپراتوری شهر\n\n"

        "🏙 شهر من: مشاهده وضعیت شهر\n"

        "🪓 تولید منابع: دریافت منابع کارگران\n"

        "🏠 ساخت خانه: افزایش خانه و جمعیت\n"

        "🛒 فروشگاه: خرید منابع و سرباز\n"

        "🧑‍🏭 مدیریت کارگران: استخدام کارگر\n"

        "⚔️ نبرد: حمله به شهر دیگر؛ هر ۶۰ ثانیه یک بار\n"

        "🐉 اژدها: مبارزه برای دریافت جایزه\n"

        "🎁 جایزه روزانه: هر ۲۴ ساعت یک بار\n"

        "🛡 سپر دفاعی: محافظت برای ۳۰ دقیقه\n"

        "🏆 رتبه‌بندی: مشاهده ده شهر برتر\n\n"

        "اطلاعات بازی در players.json ذخیره می‌شود."

    )





def handle_message(chat_id, user_id, text, first_name=""):

    text = (text or "").strip()

    p = get_player(user_id, first_name)



    update_production(p)



    if text in ("/start", "شروع", "سلام"):

        save_players()

        main_menu(

            chat_id,

            f"🏰 به امپراتوری شهر خوش آمدی، {p['name']}!\nامپراتوری خودت را بساز.",

        )

        return



    if text in ("🔙 منوی اصلی", "منوی اصلی", "بازگشت"):

        main_menu(chat_id)

        return



    if text in ("🏙 شهر من", "شهر من", "📊 آمار شهر", "آمار شهر"):

        send_message(chat_id, city_text(p), MAIN_KEYBOARD)



    elif text in ("🪓 تولید منابع", "تولید منابع"):

        update_production(p)

        save_players()

        send_message(chat_id, "🪓 منابع تولیدشده به انبار اضافه شد.\n\n" + city_text(p), MAIN_KEYBOARD)



    elif text in ("🏠 ساخت خانه", "ساخت خانه"):

        build_house(chat_id, p)



    elif text in ("🛒 فروشگاه", "فروشگاه"):

        send_message(

            chat_id,

            "🛒 فروشگاه\n"

            "🪵 ۲۰ چوب = ۳۰ سکه\n"

            "⛓ ۱۰ آهن = ۳۰ سکه\n"

            "🍞 ۳۰ غذا = ۲۰ سکه\n"

            "⚔️ استخدام سرباز = ۵۰ سکه و ۵ غذا",

            SHOP_KEYBOARD,

        )



    elif text in ("🪵 خرید چوب", "خرید چوب"):

        buy_resource(chat_id, p, "wood", 20, 30)



    elif text in ("⛓ خرید آهن", "خرید آهن"):

        buy_resource(chat_id, p, "iron", 10, 30)



    elif text in ("🍞 خرید غذا", "خرید غذا"):

        buy_resource(chat_id, p, "food", 30, 20)



    elif text in ("⚔️ استخدام سرباز", "استخدام سرباز"):

        if p["gold"] < 50 or p["food"] < 5:

            send_message(chat_id, "برای استخدام سرباز به ۵۰ سکه و ۵ غذا نیاز داری.", SHOP_KEYBOARD)

        else:

            p["gold"] -= 50

            p["food"] -= 5

            p["soldiers"] += 1

            save_players()

            send_message(chat_id, "⚔️ یک سرباز استخدام شد!\n\n" + city_text(p), SHOP_KEYBOARD)



    elif text in ("🧑‍🏭 مدیریت کارگران", "مدیریت کارگران"):

        send_message(chat_id, workers_text(p), WORKER_KEYBOARD)



    elif text in ("👷 کارگر چوب", "کارگر چوب"):

        hire_worker(chat_id, p, "woodcutter")



    elif text in ("⛏ کارگر معدن", "کارگر معدن"):

        hire_worker(chat_id, p, "miner")



    elif text in ("🌾 کارگر مزرعه", "کارگر مزرعه"):

        hire_worker(chat_id, p, "farmer")



    elif text in ("📋 کارگران من", "کارگران من"):

        send_message(chat_id, workers_text(p), WORKER_KEYBOARD)



    elif text in ("⚔️ نبرد", "نبرد"):

        attack_player(chat_id, user_id, p)



    elif text in ("🐉 اژدها", "مبارزه با اژدها"):

        dragon_fight(chat_id, p)



    elif text in ("🎁 جایزه روزانه", "جایزه روزانه"):

        daily_reward(chat_id, p)



    elif text in ("🏆 رتبه‌بندی", "رتبه بندی"):

        show_ranking(chat_id)



    elif text in ("🛡 سپر دفاعی", "سپر دفاعی"):

        activate_shield(chat_id, p)



    elif text in ("❓ راهنما", "راهنما", "/help"):

        send_message(chat_id, help_text(), MAIN_KEYBOARD)



    else:

        send_message(

            chat_id,

            "این گزینه را نمی‌شناسم. از دکمه‌های منو استفاده کن یا «راهنما» را بزن.",

            MAIN_KEYBOARD,

        )



    save_players()





# ==================================================

# حلقه اصلی ربات

# ==================================================



def main():

    if not TOKEN:

        print(

            "توکن تنظیم نشده است.\n"

            "در PowerShell این دستور را اجرا کن:\n"

            '$env:BALE_BOT_TOKEN="توکن_جدید_خودت"'

        )

        return



    print("ربات امپراتوری شهر اجرا شد. برای توقف Ctrl+C را بزن.")

    offset = None



    while True:

        try:

            payload = {"timeout": 25}

            if offset is not None:

                payload["offset"] = offset



            updates = api_call(

                "getUpdates",

                payload,

                timeout=35,

            )



            if not isinstance(updates, list):

                continue



            for update in updates:

                if not isinstance(update, dict):

                    continue



                try:

                    offset = int(update.get("update_id", 0)) + 1

                except (TypeError, ValueError):

                    continue



                message = update.get("message") or update.get("edited_message")

                if not isinstance(message, dict):

                    continue



                text = message.get("text")

                chat = message.get("chat") or {}

                user = message.get("from") or {}



                chat_id = chat.get("id")

                user_id = user.get("id")



                if chat_id is None or user_id is None or text is None:

                    continue



                try:

                    handle_message(

                        chat_id,

                        user_id,

                        text,

                        user.get("first_name", ""),

                    )

                except Exception as error:

                    print(f"خطای پردازش پیام: {error}")

                    send_message(chat_id, "خطایی رخ داد. دوباره تلاش کن.")



        except KeyboardInterrupt:

            print("ربات متوقف شد.")

            save_players()

            break



        except (requests.RequestException, ValueError, RuntimeError) as error:

            print(f"خطای ارتباط با بله: {error}")

            time.sleep(3)



        except Exception as error:

            print(f"خطای پیش‌بینی‌نشده: {error}")

            time.sleep(3)





if __name__ == "__main__":

    main()

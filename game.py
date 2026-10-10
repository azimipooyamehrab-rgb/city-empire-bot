import random
import time

WAREHOUSE_CAPACITY = 1_000_000
MAX_WORKERS_PER_JOB = 50
GOLD_TO_JEM = 100

# کلیدهای انگلیسی را تغییر ندهید؛ فایل main.py به آن‌ها وابسته است.
HOUSE_TYPES = {
    "HOUSE HUT": {"name": "کلبه", "wood": 50, "iron": 10, "gold": 0, "jem": 0, "people": 2},
    "HOUSE COTTAGE": {"name": "خانه روستایی", "wood": 100, "iron": 30, "gold": 0, "jem": 100, "people": 5},
    "HOUSE STONE": {"name": "خانه سنگی", "wood": 150, "iron": 100, "gold": 0, "jem": 250, "people": 8},
    "HOUSE MANOR": {"name": "عمارت", "wood": 250, "iron": 200, "gold": 5, "jem": 500, "people": 12},
    "HOUSE PALACE": {"name": "کاخ", "wood": 400, "iron": 350, "gold": 5, "jem": 1000, "people": 20},
}


def new_city():
    now = time.time()
    return {
        "jem": 500,
        "sarbaz": 100,
        "chob": 100,
        "ahan": 100,
        "khone": 10,
        "shahrvand": 50,
        "food": 100,
        "gold": 0,
        "level": 1,
        "xp": 0,
        "ete_bar": 100,
        "azhdaha": 2,
        "shield": 0,
        "shield_until": 0,
        "wins": 0,
        "losses": 0,
        "clan": "",
        "alliance": "",
        "username": "Unknown",
        "workers": {"mine": 0, "farm": 0, "woodcutter": 0},
        "warehouse_capacity": WAREHOUSE_CAPACITY,
        "production_last_at": now,
        "attack_protected_until": 0,
        "houses": {"کلبه": 10, "خانه روستایی": 0, "خانه سنگی": 0, "عمارت": 0, "کاخ": 0},
    }


def normalize_city(city):
    defaults = new_city()
    for key, value in defaults.items():
        if key not in city:
            city[key] = value.copy() if isinstance(value, (dict, list)) else value
    if not isinstance(city.get("workers"), dict):
        city["workers"] = {"mine": 0, "farm": 0, "woodcutter": 0}
    for job in ("mine", "farm", "woodcutter"):
        city["workers"].setdefault(job, 0)
        city["workers"][job] = max(0, min(MAX_WORKERS_PER_JOB, int(city["workers"][job])))
    if not isinstance(city.get("houses"), dict):
        city["houses"] = defaults["houses"].copy()
    else:
        for name, amount in defaults["houses"].items():
            city["houses"].setdefault(name, amount)
    city.setdefault("warehouse_capacity", WAREHOUSE_CAPACITY)
    city["warehouse_capacity"] = WAREHOUSE_CAPACITY
    return city


def warehouse_used(city):
    return sum(max(0, int(city.get(key, 0))) for key in ("chob", "ahan", "food", "gold"))


def add_to_warehouse(city, resource, amount):
    amount = max(0, int(amount))
    free = max(0, WAREHOUSE_CAPACITY - warehouse_used(city))
    accepted = min(amount, free)
    city[resource] = max(0, int(city.get(resource, 0))) + accepted
    return accepted, amount - accepted


def update_production(city, now=None):
    """تولید منابع را هنگام تعامل بعدی بازیکن با ربات محاسبه می‌کند."""
    normalize_city(city)
    now = time.time() if now is None else now
    last = float(city.get("production_last_at", now))
    elapsed_minutes = max(0, min(24 * 60, int((now - last) // 60)))
    if elapsed_minutes <= 0:
        return {"chob": 0, "ahan": 0, "food": 0, "gold": 0, "blocked": 0}
    city["production_last_at"] = last + elapsed_minutes * 60
    workers = city["workers"]
    rates = {
        "chob": min(100, workers["woodcutter"] * 2),
        "ahan": min(100, workers["mine"] * 2),
        "food": min(100, workers["farm"] * 2),
    }
    result = {"chob": 0, "ahan": 0, "food": 0, "gold": 0, "blocked": 0}
    for _ in range(elapsed_minutes):
        for resource, rate in rates.items():
            accepted, rejected = add_to_warehouse(city, resource, rate)
            result[resource] += accepted
            result["blocked"] += rejected
        # طلا کمیاب است؛ حتی با ۵۰ معدن‌کار، احتمال یافتنش در هر دقیقه حداکثر ۱۰٪ است.
        miners = workers["mine"]
        chance = min(10, miners * 0.2)
        if miners and random.random() * 100 < chance:
            found = random.randint(1, 2)
            accepted, rejected = add_to_warehouse(city, "gold", found)
            result["gold"] += accepted
            result["blocked"] += rejected
    return result


def show_city(city):
    normalize_city(city)
    update_production(city)
    w = city["workers"]
    shield_text = "ندارد"
    if city["shield_until"] > time.time():
        remaining = int(city["shield_until"] - time.time())
        shield_text = f'{city["shield"]} ساعت — {remaining // 3600} ساعت و {(remaining % 3600) // 60} دقیقه'
    return (
        "🏙️ وضعیت شهر شما\n\n"
        f'💎 جم: {city["jem"]}\n'
        f'⚔️ سرباز: {city["sarbaz"]}\n'
        f'🪵 چوب: {city["chob"]}\n'
        f'⛓️ آهن: {city["ahan"]}\n'
        f'🌾 غذا: {city["food"]}\n'
        f'🪙 طلا: {city["gold"]}\n'
        f'🏠 تعداد خانه‌ها: {city["khone"]}\n'
        f'👥 شهروندان: {city["shahrvand"]}\n\n'
        f'⭐ سطح: {city["level"]}\n'
        f'✨ تجربه (XP): {city["xp"]}\n'
        f'🏅 اعتبار: {city["ete_bar"]}\n'
        f'🐉 اژدهاهای شکست‌داده‌شده: {city["azhdaha"]}\n'
        f'🛡️ سپر دفاعی: {shield_text}\n\n'
        f'👷 کارگران — معدن: {w["mine"]}، مزرعه: {w["farm"]}، چوب‌بری: {w["woodcutter"]}\n'
        f'📦 انبار: {warehouse_used(city):,} از {WAREHOUSE_CAPACITY:,}\n'
        f'🔄 نرخ تبدیل طلا: هر ۱ طلا = {GOLD_TO_JEM} جم\n'
        f'🏆 برد: {city["wins"]}\n'
        f'💥 باخت: {city["losses"]}\n'
        f'🛡️ قبیله: {city["clan"] or "ندارد"}\n'
        f'🤝 اتحاد: {city["alliance"] or "ندارد"}'
    )


def mine(city):
    normalize_city(city)
    update_production(city)
    return (
        "⛏️ معدن\n\n"
        f'👷 معدن‌کاران مشغول: {city["workers"]["mine"]}\n'
        f'⛓️ آهن ذخیره‌شده: {city["ahan"]}\n'
        f'🪙 طلای ذخیره‌شده: {city["gold"]}\n\n'
        "تولید آهن می‌تواند تا ۱۰۰ واحد در دقیقه برسد.\n"
        "طلا کمیاب است و هر بار ۱ تا ۲ واحد پیدا می‌شود.\n"
        "با اختصاص کارگر، منابع به‌صورت خودکار تولید می‌شوند.\n"
        "برای تعیین تعداد معدن‌کاران، وارد بخش «کارگران» شوید."
    )


def farm(city):
    normalize_city(city)
    update_production(city)
    return (
        "🌾 مزرعه\n\n"
        f'👩‍🌾 کارگران مزرعه: {city["workers"]["farm"]}\n'
        f'🥖 غذای ذخیره‌شده: {city["food"]}\n\n'
        "تولید غذا می‌تواند تا ۱۰۰ واحد در دقیقه برسد.\n"
        "تولید به‌صورت خودکار انجام می‌شود؛ از بخش «کارگران» نیرو اختصاص دهید."
    )


def woodcutter(city):
    normalize_city(city)
    update_production(city)
    return (
        "🪵 چوب‌بری\n\n"
        f'🪓 چوب‌برها: {city["workers"]["woodcutter"]}\n'
        f'🪵 چوب ذخیره‌شده: {city["chob"]}\n\n'
        "تولید چوب می‌تواند تا ۱۰۰ واحد در دقیقه برسد.\n"
        "تولید به‌صورت خودکار انجام می‌شود؛ از بخش «کارگران» نیرو اختصاص دهید."
    )


def workers_text(city):
    normalize_city(city)
    w = city["workers"]
    total = sum(w.values())
    return (
        "👷 مدیریت کارگران\n\n"
        f'👥 شهروندان در دسترس: {city["shahrvand"]}\n'
        f'🧑‍🔧 مجموع کارگران اختصاص‌یافته: {total}\n\n'
        f'⛏️ معدن: {w["mine"]}/50\n'
        f'🌾 مزرعه: {w["farm"]}/50\n'
        f'🪵 چوب‌بری: {w["woodcutter"]}/50\n\n'
        "یک شغل را انتخاب کنید و سپس عددی بین ۰ تا ۵۰ بفرستید.\n"
        "تعداد کل کارگران نمی‌تواند از تعداد شهروندان بیشتر شود."
    )


def assign_workers(city, job, amount):
    normalize_city(city)
    if job not in city["workers"]:
        return False, "❌ شغل انتخاب‌شده معتبر نیست."
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return False, "لطفاً یک عدد صحیح بین ۰ تا ۵۰ بفرستید."
    if not 0 <= amount <= MAX_WORKERS_PER_JOB:
        return False, "برای هر شغل باید عددی بین ۰ تا ۵۰ انتخاب کنید."
    other_workers = sum(v for key, v in city["workers"].items() if key != job)
    if other_workers + amount > city["shahrvand"]:
        return False, f"❌ شهروند کافی ندارید. شغل‌های دیگر در مجموع {other_workers} کارگر دارند."
    city["workers"][job] = amount
    city["production_last_at"] = time.time()
    job_names = {"mine": "معدن", "farm": "مزرعه", "woodcutter": "چوب‌بری"}
    return True, f"✅ تعداد {amount} کارگر به بخش {job_names[job]} اختصاص یافت."


def exchange_gold(city, amount):
    normalize_city(city)
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return "تعداد طلایی را که می‌خواهید تبدیل کنید، به‌صورت عدد بفرستید."
    if amount <= 0:
        return "❌ مقدار باید بیشتر از صفر باشد."
    if city["gold"] < amount:
        return f'❌ طلای کافی ندارید. طلای فعلی شما: {city["gold"]}'
    city["gold"] -= amount
    city["jem"] += amount * GOLD_TO_JEM
    return f"✅ تبدیل انجام شد!\n\n🪙 طلای مصرف‌شده: {amount}-\n💎 جم دریافت‌شده: {amount * GOLD_TO_JEM}+"


def warehouse_text(city):
    normalize_city(city)
    update_production(city)
    used = warehouse_used(city)
    return (
        "📦 انبار شهر\n\n"
        f'🪵 چوب: {city["chob"]}\n'
        f'⛓️ آهن: {city["ahan"]}\n'
        f'🌾 غذا: {city["food"]}\n'
        f'🪙 طلا: {city["gold"]}\n\n'
        f'ظرفیت انبار: {used:,} از {WAREHOUSE_CAPACITY:,}\n'
        f'فضای خالی: {max(0, WAREHOUSE_CAPACITY - used):,}\n\n'
        "وقتی انبار پر شود، تولید منابع تا خالی‌شدن فضا متوقف می‌شود."
    )


def build_house(city, house_key="HOUSE HUT"):
    normalize_city(city)
    if house_key not in HOUSE_TYPES:
        return "❌ نوع خانه انتخاب‌شده وجود ندارد."
    house = HOUSE_TYPES[house_key]
    costs = {"chob": house["wood"], "ahan": house["iron"], "gold": house["gold"], "jem": house["jem"]}
    labels = {"chob": "چوب", "ahan": "آهن", "gold": "طلا", "jem": "جم"}
    for resource, cost in costs.items():
        if city.get(resource, 0) < cost:
            return f'❌ {labels[resource]} کافی ندارید. مقدار لازم: {cost}؛ مقدار فعلی: {city.get(resource, 0)}.'
    for resource, cost in costs.items():
        city[resource] -= cost
    city["khone"] += 1
    city["shahrvand"] += house["people"]
    city["houses"][house["name"]] = city["houses"].get(house["name"], 0) + 1
    city["xp"] += 30
    return (
        f'🏠 ساخت «{house["name"]}» با موفقیت انجام شد!\n\n'
        f'🪵 چوب مصرف‌شده: {house["wood"]}\n'
        f'⛓️ آهن مصرف‌شده: {house["iron"]}\n'
        f'🪙 طلا مصرف‌شده: {house["gold"]}\n'
        f'💎 جم مصرف‌شده: {house["jem"]}\n'
        f'👥 شهروندان جدید: {house["people"]}+\n'
        "✨ تجربه: ۳۰+"
    )

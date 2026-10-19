"""ТЯГА: shared Python domain engine for the browser demo and local server.

All records are fictional. No messages, SMS or payments leave the demo.
Only Python changes application data; the frontend renders returned snapshots.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
import re
import uuid
import difflib
import hashlib
from catalog_schema import SECTIONS, CATEGORY_GROUPS, CATEGORY_SECTIONS, CATEGORIES, FIELDS, applicable, meter_unit

VERSION = 3
STATUSES = {"active": "Активно", "pending": "На проверке", "rejected": "Нужны исправления", "draft": "Черновик", "archived": "В архиве", "sold": "Продано", "deleted": "Удалено"}
CITIES = {"Казань": [55.796, 49.109], "Набережные Челны": [55.743, 52.395], "Москва": [55.755, 37.617], "Самара": [53.195, 50.101], "Уфа": [54.735, 55.958], "Нижний Новгород": [56.327, 44.005], "Екатеринбург": [56.839, 60.606], "Санкт-Петербург": [59.934, 30.335]}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def uid(prefix):
    return prefix + uuid.uuid4().hex[:12]


class DemoError(Exception):
    def __init__(self, message, fields=None):
        super().__init__(message)
        self.fields = fields or {}


def seed():
    stamp = now()
    users = {
        "azat": {"id": "azat", "name": "Азат", "kind": "private", "city": "Казань", "phone": "+7 ••• ••• 45 67", "email": "azat@example.com", "avatar": "", "notifications": {"messages": True, "status": True, "searches": True}},
        "ilya": {"id": "ilya", "name": "Илья", "kind": "private", "city": "Казань", "phone": "+7 ••• ••• 12 34", "email": "ilya@example.com", "avatar": "", "notifications": {"messages": True, "status": True, "searches": True}},
        "marat": {"id": "marat", "name": "Марат", "kind": "private", "city": "Самара", "phone": "+7 ••• ••• 22 33", "email": "", "avatar": "", "notifications": {"messages": True, "status": True, "searches": True}},
    }
    sellers = [
        {"id": "trans", "name": "ТрансСервис", "city": "Москва", "kind": "dealer", "initials": "ТС", "about": "Грузовые автомобили и спецтехника. Осмотр на площадке по договорённости.", "hours": "Пн–сб, 09:00–18:00"},
        {"id": "volga", "name": "ВолгаТрак", "city": "Казань", "kind": "dealer", "initials": "ВТ", "about": "Тягачи и прицепы для грузоперевозок. Поможем подобрать технику из наличия.", "hours": "Пн–пт, 09:00–18:00"},
        {"id": "spec", "name": "СпецТехПарк", "city": "Самара", "kind": "dealer", "initials": "СП", "about": "Экскаваторы и погрузчики. Показ техники на площадке по предварительной записи.", "hours": "Пн–сб, 08:00–18:00"},
        {"id": "ural", "name": "УралМашТрейд", "city": "Екатеринбург", "kind": "dealer", "initials": "УМ", "about": "Грузовики для строительства и перевозок. Все представленные машины можно осмотреть.", "hours": "Пн–пт, 09:00–19:00"},
    ]
    records = [
        ("1", "azat", "Volvo", "FH 500", "tractor", 8900000, 2021, 348000, "Казань", "active", "volvo", "4×2"),
        ("2", "azat", "КАМАЗ", "54901", "tractor", 7450000, 2022, 186000, "Набережные Челны", "active", "kamaz", "4×2"),
        ("3", "azat", "CAT", "320", "excavator", 12800000, 2021, 6400, "Москва", "active", "cat", "Гусеничный"),
        ("4", "azat", "JCB", "3CX", "loader", 8600000, 2020, 5100, "Самара", "pending", "jcb", "4×4"),
        ("5", "azat", "Shacman", "X3000", "dump", None, 2023, 78000, "Уфа", "draft", "shacman", "6×4"),
        ("6", "azat", "MAN", "TGX 18.440", "tractor", 6850000, 2019, 520000, "Нижний Новгород", "archived", "man", "4×2"),
        ("7", "trans", "Volvo", "FH 500", "tractor", 8750000, 2020, 390000, "Москва", "active", "volvo", "4×2"),
        ("8", "volga", "КАМАЗ", "54901", "tractor", 7650000, 2022, 142000, "Казань", "active", "kamaz", "4×2"),
        ("9", "spec", "JCB", "3CX", "loader", 8500000, 2020, 4700, "Самара", "active", "jcb", "4×4"),
        ("10", "ural", "Shacman", "X3000", "dump", 8950000, 2023, 78000, "Екатеринбург", "active", "shacman", "6×4"),
        ("11", "trans", "MAN", "TGX 18.440", "tractor", 6850000, 2019, 520000, "Москва", "active", "man", "4×2"),
        ("12", "spec", "CAT", "320", "excavator", 11900000, 2020, 7800, "Самара", "active", "cat", "Гусеничный"),
        ("13", "volga", "Schmitz", "S01", "trailer", 2950000, 2022, 0, "Казань", "active", "trailer", "3 оси"),
        ("14", "ural", "КАМАЗ", "54901", "tractor", 10900000, 2025, 0, "Екатеринбург", "active", "kamaz", "4×2"),
        ("15", "trans", "MAN", "TGX 18.440", "tractor", 6500000, 2018, 610000, "Москва", "sold", "man", "4×2"),
        ("16", "ilya", "Shacman", "X3000", "dump", 8200000, 2021, 198000, "Уфа", "active", "shacman", "6×4"),
    ]
    ads = []
    for i, (ad_id, owner, brand, model, category, price, year, mileage, city, status, asset, wheels) in enumerate(records):
        ads.append({"id": ad_id, "owner": owner, "brand": brand, "model": model, "title": brand + " " + model,
                    "category": category, "price": price, "year": year, "mileage": mileage,
                    "city": city, "status": status, "photos": ["/assets/" + asset + ".webp"], "asset": asset,
                    "wheels": wheels, "gearbox": "Автомат" if category in ("tractor", "dump") else "Не указано",
                    "power": 500 if brand == "Volvo" else 440 if brand == "MAN" else 450 if brand == "КАМАЗ" else None,
                    "condition": "new" if year == 2025 else "used", "vat": "yes" if owner in ("trans", "ural") else "no",
                    "description": "Техника в рабочем состоянии. Осмотр в городе " + city + " по договорённости. Можно проверить основные узлы и документы на площадке.",
                    "created": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=i * 3)).isoformat(timespec="seconds"),
                    "updated": stamp, "rejection": "", "fuel": "Дизель" if category != "trailer" else "—"})
    state = {"version": 1, "user_id": "azat", "users": users, "sellers": sellers, "ads": ads,
            "favorites": {"azat": ["11", "7", "9", "10", "12", "13", "8", "14"], "ilya": ["1", "2"]},
            "compare": ["11", "7"], "searches": {"azat": [
                {"id": "s1", "name": "Тягачи до 9 млн ₽", "filters": {"category": "tractor", "max_price": 9000000}, "notify": True, "frequency": "daily", "seen": []},
                {"id": "s2", "name": "Экскаваторы в Татарстане", "filters": {"category": "excavator", "city": "Казань", "radius": 250}, "notify": True, "frequency": "daily", "seen": []}]},
            "conversations": [
                {"id": "c1", "ad_id": "1", "participants": ["azat", "ilya"], "unread": {"azat": 2, "ilya": 0}, "messages": [
                    {"id": "m1", "sender": "ilya", "text": "Можно посмотреть завтра?", "time": stamp, "attachment": None},
                    {"id": "m2", "sender": "ilya", "text": "Могу подъехать после 15:00.", "time": stamp, "attachment": None}]},
                {"id": "c2", "ad_id": "2", "participants": ["azat", "marat"], "unread": {"azat": 1, "marat": 0}, "messages": [
                    {"id": "m3", "sender": "marat", "text": "Здравствуйте! КАМАЗ ещё в продаже?", "time": stamp, "attachment": None}]}],
            "tickets": [], "notices": [{"id": "n1", "user": "azat", "title": "JCB 3CX на проверке", "text": "Проверяем фотографии и описание.", "ad_id": "4", "read": False, "time": stamp}],
            "sessions": {"azat": [{"id": "current", "name": "Этот браузер", "current": True}, {"id": "other", "name": "MacBook · тестовый сеанс", "current": False}]},
            "challenge": None}
    return migrate(state)


def migrate(state):
    """Add new data once; never replace the user's saved listings or messages."""
    if state.get("version", 1) < 2:
        state["users"].setdefault("moderator", {"id": "moderator", "name": "Анна", "role": "moderator", "kind": "staff", "city": "Казань", "phone": "Демо", "email": "moderator@example.com", "avatar": "", "notifications": {"messages": True, "status": True, "searches": True}})
        state.setdefault("moderation_log", [])
        samples = [
            ("101", "ilya", "Toyota", "Camry 2.5", "car", 3250000, 2021, 68000, "Казань", "active", "car", {"body": "Седан", "fuel": "Бензин", "gearbox": "Автомат", "drive": "Передний", "engine_cc": 2487, "power": 200, "owners": 1, "seats": 5, "steering": "Левый", "taxi": "Нет", "color": "Серебристый"}),
            ("102", "trans", "Toyota", "Camry 2.0", "car", 2890000, 2020, 91000, "Москва", "active", "car", {"body": "Седан", "fuel": "Бензин", "gearbox": "Автомат", "drive": "Передний", "engine_cc": 1987, "power": 150, "owners": 2, "seats": 5, "steering": "Левый", "taxi": "Нет"}),
            ("103", "ilya", "Toyota", "Camry 2.5", "car", 3690000, 2022, 42000, "Самара", "pending", "car", {"body": "Седан", "fuel": "Бензин", "gearbox": "Автомат", "power": 200, "engine_cc": 2487}),
            ("201", "marat", "Yamaha", "MT-07", "motorcycle", 890000, 2022, 14000, "Самара", "active", "moto", {"vehicle_class": "Дорожный", "fuel": "Бензин", "engine_cc": 689, "power": 73, "gearbox": "Механика", "abs": "Есть", "seat_height": 805}),
            ("202", "ilya", "Yamaha", "MT-07", "motorcycle", 790000, 2021, 21000, "Казань", "active", "moto", {"vehicle_class": "Дорожный", "fuel": "Бензин", "engine_cc": 689, "power": 73, "abs": "Есть"}),
            ("203", "marat", "Yamaha", "MT-07", "motorcycle", 970000, 2023, 8000, "Москва", "pending", "moto", {"fuel": "Бензин", "engine_cc": 689, "power": 73, "vehicle_class": "Дорожный"}),
            ("301", "volga", "Volzhanka", "Open 6.0", "motorboat", 2450000, 2022, 180, "Казань", "active", "boat", {"hull": "Алюминий", "length": 6, "width": 2.3, "seats": 6, "motor_included": "Да", "motor_type": "Подвесной", "motor_power": 150, "max_motor_power": 175, "motors": 1, "trailer_included": "Нет"}),
            ("302", "trans", "Volzhanka", "Open 6.0", "motorboat", 2290000, 2021, 260, "Нижний Новгород", "active", "boat", {"hull": "Алюминий", "length": 6, "width": 2.3, "seats": 6, "motor_included": "Да", "motor_power": 115, "motors": 1, "trailer_included": "Да"}),
            ("303", "volga", "Volzhanka", "Open 6.0", "motorboat", 2590000, 2023, 95, "Казань", "pending", "boat", {"hull": "Алюминий", "length": 6, "motor_included": "Да", "motor_power": 150, "seats": 6}),
        ]
        existing = {a["id"] for a in state["ads"]}
        for i, (aid, owner, brand, model, category, price, year, meter, city, status, asset, details) in enumerate(samples):
            if aid in existing:
                continue
            stamp = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=8+i)).isoformat(timespec="seconds")
            a = {"id": aid, "owner": owner, "brand": brand, "model": model, "title": brand + " " + model, "category": category, "price": price, "year": year, "mileage": meter, "city": city, "status": status, "asset": asset, "photos": ["/assets/" + asset + ".webp"], "condition": "used", "vat": "no", "wheels": "", "gearbox": "", "fuel": "", "power": None, "description": "Демонстрационное объявление. Транспорт в рабочем состоянии, осмотр по договорённости. Фотография иллюстративная; все данные вымышлены.", "created": stamp, "updated": stamp, "rejection": "", **details}
            state["ads"].append(a)
        for a in state["ads"]:
            a["section"] = CATEGORY_SECTIONS[a["category"]]
            if meter_unit(a["category"]) == "hours":
                a["hours"], a["mileage"] = a.get("mileage"), None
            elif meter_unit(a["category"]) is None:
                a["mileage"] = None
            a.setdefault("availability", "stock")
            a.setdefault("revision", 1)
            if a["status"] == "pending":
                a.setdefault("submitted", a["updated"])
        state["version"] = 2
    if state.get("version") == 2:
        state.setdefault("moderation_work", {})
        state["version"] = 3
    if state.get("version") != VERSION:
        raise DemoError("Эта версия данных новее приложения. Обновите страницу.")
    return state


def user_id(state):
    value = state.get("user_id")
    if not value or value not in state["users"]:
        raise DemoError("Войдите в аккаунт, чтобы продолжить", {"auth": "required"})
    return value


def ad_by_id(state, ad_id, owned=False):
    ad = next((x for x in state["ads"] if x["id"] == str(ad_id) and x["status"] != "deleted"), None)
    if not ad:
        raise DemoError("Объявление не найдено")
    if owned and ad["owner"] != user_id(state):
        raise DemoError("Можно изменять только свои объявления")
    return ad


def integer(value, label, minimum=0, maximum=10**12, optional=True):
    if value is None or value == "":
        if optional:
            return None
        raise DemoError("Заполните поле «" + label + "»", {label: "Обязательное поле"})
    cleaned = re.sub(r"[\s\u00a0]", "", str(value))
    if not re.fullmatch(r"\d+", cleaned):
        raise DemoError("В поле «" + label + "» нужно целое число")
    number = int(cleaned)
    if not minimum <= number <= maximum:
        raise DemoError("Проверьте значение поля «" + label + "»")
    return number


def photo_list(photos):
    if not isinstance(photos, list) or len(photos) > 8:
        raise DemoError("Можно добавить до 8 фотографий")
    for photo in photos:
        if not isinstance(photo, str):
            raise DemoError("Не удалось прочитать фотографию")
        if re.fullmatch(r"/assets/[a-z0-9_-]+\.webp", photo):
            continue
        if len(photo) > 3_000_000 or not re.match(r"^data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$", photo):
            raise DemoError("Поддерживаются JPG, PNG и WebP до 2 МБ")
    return photos


def normalize_filters(data):
    data = dict(data)
    q = str(data.get("q", "")).strip()[:200]
    budget = re.search(r"\b(до|от)\s+(\d+(?:[.,]\d+)?)\s*(млн|миллион(?:а|ов)?|тыс(?:яч)?)\b", q, re.I)
    if budget:
        key = "max_price" if budget[1].lower() == "до" else "min_price"
        data.setdefault(key, round(float(budget[2].replace(",", ".")) * (10**6 if budget[3].lower().startswith("м") else 1000)))
        q = (q[:budget.start()] + q[budget.end():]).strip()
    data["q"] = q
    f = {k: str(data[k]).strip() for k in ("q", "section", "category", "city", "condition", "vat", "sort", "availability", "seller_kind") if data.get(k) not in (None, "", "all")}
    if f.get("section") and f["section"] not in SECTIONS:
        raise DemoError("Выберите раздел каталога")
    if f.get("category"):
        if f["category"] not in CATEGORIES:
            raise DemoError("Выберите категорию каталога")
        section = CATEGORY_SECTIONS[f["category"]]
        if f.get("section", section) != section:
            raise DemoError("Выбранная категория относится к другому разделу")
        f["section"] = section
    for k in ("brand", "model"):
        values = data.get(k, "")
        if isinstance(values, str): values = values.split(",")
        if values: f[k] = ",".join(dict.fromkeys(str(v).strip()[:80] for v in values if str(v).strip()))
    nums = {"min_price": "Цена от", "max_price": "Цена до", "year_from": "Год от", "year_to": "Год до", "max_mileage": "Пробег до", "max_hours": "Наработка до", "radius": "Радиус", "age_days": "Давность"}
    ranges = [("min_price", "max_price"), ("year_from", "year_to")]
    for field in FIELDS:
        k = field["key"]
        if field["type"] == "select":
            if data.get(k) not in (None, "", "all"):
                choices = str(data[k]).split(",")
                if any(v not in field["options"] for v in choices): raise DemoError("Проверьте фильтр «" + field["label"] + "»")
                f[k] = ",".join(dict.fromkeys(choices))
        else:
            nums["min_"+k], nums["max_"+k] = field["label"]+" от", field["label"]+" до"
            ranges.append(("min_"+k, "max_"+k))
    for k, label in nums.items():
        value = number(data.get(k), label)
        if value is not None: f[k] = value
    for low, high in ranges:
        if low in f and high in f and f[low] > f[high]: raise DemoError("Значение «от» должно быть меньше значения «до»")
    for k in ("only_photo", "include_unknown"):
        if data.get(k) in (True, "true", "1", "on"): f[k] = True
    if f.get("sort", "new") not in ("new", "price_asc", "price_desc", "year", "distance", "mileage", "hours", "relevance"):
        raise DemoError("Выберите способ сортировки")
    if f.get("sort") == "distance" and not f.get("city"):
        raise DemoError("Для сортировки по расстоянию выберите город")
    return f


def number(value, label, maximum=10**12):
    if value in (None, ""): return None
    try:
        v = float(re.sub(r"\s", "", str(value)).replace(",", "."))
    except (ValueError, TypeError):
        raise DemoError("В поле «" + label + "» нужно число")
    if not math.isfinite(v) or v < 0 or v > maximum:
        raise DemoError("Проверьте поле «" + label + "»")
    return int(v) if v.is_integer() else v


ALIASES = {"камаз": "kamaz", "вольво": "volvo", "волво": "volvo", "ман": "man", "шакман": "shacman", "шахман": "shacman", "тойота": "toyota", "тойёта": "toyota", "камри": "camry", "ямаха": "yamaha", "ямaха": "yamaha", "волжанка": "volzhanka", "катерпиллер": "cat", "джисиби": "jcb", "самосвалы": "самосвал", "экскаваторы": "экскаватор", "тягачи": "тягач", "погрузчики": "погрузчик", "мотоциклы": "мотоцикл", "лодки": "лодка", "катера": "катер", "яхты": "яхта", "автомобили": "автомобиль"}


def words(text):
    return [ALIASES.get(w, w) for w in re.findall(r"[\w]+", str(text).casefold().replace("ё", "е"))]


def matches(ad, q):
    tokens = words(q)
    haystack = words(" ".join(str(ad.get(k, "")) for k in ("title", "city", "body", "cargo_body", "vehicle_class")) + " " + CATEGORIES[ad["category"]])
    return all(any(t in w for w in haystack) or (len(t) > 4 and bool(difflib.get_close_matches(t, haystack, n=1, cutoff=.84))) for t in tokens)


def distance(a, b):
    if a == b:
        return 0
    if a not in CITIES or b not in CITIES:
        return 999999
    x1, y1 = map(math.radians, CITIES[a]); x2, y2 = map(math.radians, CITIES[b])
    v = math.sin((x2 - x1) / 2) ** 2 + math.cos(x1) * math.cos(x2) * math.sin((y2 - y1) / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(v)))


def query(state, filters=None, owner=None):
    f = normalize_filters(filters or {})
    rows = [a for a in state["ads"] if a["status"] == "active" and (not owner or a["owner"] == owner)]
    for key in ("section", "category", "brand", "model", "condition", "vat", "availability") + tuple(x["key"] for x in FIELDS if x["type"] == "select"):
        if f.get(key):
            choices = {v.casefold() for v in f[key].split(",")}
            rows = [a for a in rows if str(a.get(key, "")).casefold() in choices]
    if f.get("q"):
        rows = [a for a in rows if matches(a, f["q"])]
    numeric_filters = [("price", "min", "min_price"), ("price", "max", "max_price"), ("year", "min", "year_from"), ("year", "max", "year_to"), ("mileage", "max", "max_mileage"), ("hours", "max", "max_hours")]
    numeric_filters += [(x["key"], op, op+"_"+x["key"]) for x in FIELDS if x["type"] == "number" for op in ("min", "max")]
    for field, op, key in numeric_filters:
        if key in f:
            rows = [a for a in rows if (f.get("include_unknown", False) if a.get(field) is None else (a[field] >= f[key] if op == "min" else a[field] <= f[key]))]
    if f.get("city"):
        rows = [a for a in rows if distance(a["city"], f["city"]) <= f.get("radius", 0)]
    if f.get("only_photo"):
        rows = [a for a in rows if a["photos"]]
    if f.get("seller_kind"):
        people = {**state["users"], **{s["id"]: s for s in state["sellers"]}}
        rows = [a for a in rows if ("private" if people[a["owner"]]["kind"] == "private" else "company") == f["seller_kind"]]
    if f.get("age_days"):
        cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=f["age_days"])).isoformat()
        rows = [a for a in rows if a["created"] >= cutoff]
    sort = f.get("sort", "new")
    if sort == "distance": rows.sort(key=lambda a: distance(a["city"], f["city"]))
    elif sort in ("mileage", "hours"): rows.sort(key=lambda a: (a.get(sort) is None, a.get(sort) or 0))
    elif sort.startswith("price"):
        rows.sort(key=lambda a: (a.get("price") is None, -(a.get("price") or 0) if sort == "price_desc" else (a.get("price") or 0)))
    elif sort == "year": rows.sort(key=lambda a: a.get("year") or 0, reverse=True)
    else: rows.sort(key=lambda a: a["created"], reverse=True)
    if sort == "relevance" and f.get("q"):
        rows.sort(key=lambda a: sum(t in words(a["title"]) for t in words(f["q"])), reverse=True)
    return rows


def overview(state):
    u = state.get("user_id")
    own = [a for a in state["ads"] if a["owner"] == u and a["status"] != "deleted"]
    counts = {"all": len(own), "active": 0, "pending": 0, "draft": 0, "archived": 0}
    for a in own:
        k = "pending" if a["status"] == "rejected" else "archived" if a["status"] == "sold" else a["status"]
        counts[k] = counts.get(k, 0) + 1
    return {"counts": counts, "unread": sum(c["unread"].get(u, 0) for c in state["conversations"] if u in c["participants"]),
            "favorites": len(state["favorites"].get(u, [])), "public_count": len(query(state)),
            "notices": sum(1 for n in state["notices"] if n["user"] == u and not n["read"]),
            "search_new": {s["id"]: len([a for a in query(state, s["filters"]) if a["id"] not in s.get("seen", [])]) for s in state["searches"].get(u, [])}}


def notice(state, title, body, ad_id=None, recipient=None):
    state["notices"].insert(0, {"id": uid("n"), "user": recipient or state.get("user_id"), "title": title, "text": body, "ad_id": ad_id, "read": False, "time": now()})


def review_snapshot(ad):
    keys = {"title", "category", "price", "year", "city", "description", "condition", "mileage", "hours", "availability", "vat", "brand", "model"} | {f["key"] for f in FIELDS}
    result = {k: ad.get(k) for k in keys}
    result["photos"] = {"count": len(ad["photos"]), "hash": hashlib.sha256(json.dumps(ad["photos"]).encode()).hexdigest()}
    return result


def review_info(state, ad):
    work = state["moderation_work"].get(ad["id"], {})
    history = [x for x in state["moderation_log"] if x["ad_id"] == ad["id"]]
    last = next((x for x in history if x["decision"] in ("approve", "return", "remove")), None)
    snapshot = review_snapshot(ad)
    changes = [{"key": k, "before": last["snapshot"].get(k), "after": v} for k, v in snapshot.items() if last and last.get("snapshot") and last["snapshot"].get(k) != v]
    flags = []
    for k, label in (("price", "Не указана цена"), ("year", "Не указан год"), ("city", "Не указан город"), ("photos", "Нет фотографий")):
        if not ad.get(k): flags.append({"label": label, "level": "error"})
    if len(ad.get("description", "")) < 60: flags.append({"label": "Короткое описание: проверьте, достаточно ли сведений", "level": "warning"})
    unit = meter_unit(ad["category"])
    if unit and ad.get("hours" if unit == "hours" else "mileage") is None:
        flags.append({"label": "Не указана наработка" if unit == "hours" else "Не указан пробег", "level": "warning"})
    duplicates = [a["id"] for a in state["ads"] if a["id"] != ad["id"] and a["status"] in ("pending", "active") and all(a.get(k) == ad.get(k) for k in ("owner", "brand", "model", "year", "city"))]
    if duplicates: flags.append({"label": "Похожие объявления этого продавца: " + ", ".join("№"+i for i in duplicates), "level": "warning"})
    submitted = dt.datetime.fromisoformat(ad.get("submitted", ad["updated"]))
    wait_hours = max(0, (dt.datetime.now(dt.timezone.utc)-submitted).total_seconds()/3600)
    return {"priority": work.get("priority", "normal"), "deferred_until": work.get("deferred_until"), "notes": work.get("notes", []), "wait_hours": round(wait_hours, 1), "repeat": bool(last and last["decision"] in ("return", "remove") and ad["status"] == "pending"), "flags": flags, "changes": changes, "last_decision": last, "history": history}


def review_audit(state, ad, action, reason="", **extra):
    u = user_id(state)
    entry = {"id": uid("audit"), "ad_id": ad["id"], "title": ad["title"], "section": ad["section"], "moderator": u, "moderator_name": state["users"][u]["name"], "decision": action, "reason": reason, "before": ad["status"], "after": ad["status"], "time": now(), "revision": ad.get("revision", 1), **extra}
    state["moderation_log"].insert(0, entry)
    return entry


def review_queue(state, data):
    tab = data.get("status", "pending")
    if tab not in ("pending", "deferred", "active", "rejected", "history"): raise DemoError("Выберите очередь")
    stamp = now()
    infos = {a["id"]: review_info(state, a) for a in state["ads"] if a["status"] in ("pending", "active", "rejected")}
    def queue_status(a):
        work = state["moderation_work"].get(a["id"], {})
        return "deferred" if a["status"] == "pending" and (work.get("deferred_until") or "") > stamp else a["status"]
    counts = {s: sum(queue_status(a) == s for a in state["ads"]) for s in ("pending", "deferred", "active", "rejected")}
    counts["history"] = len(state["moderation_log"])
    moscow = dt.timezone(dt.timedelta(hours=3))
    today = dt.datetime.now(moscow).date()
    stats = {"today": sum(dt.datetime.fromisoformat(x["time"]).astimezone(moscow).date() == today and x["decision"] in ("approve", "return", "remove") for x in state["moderation_log"]), "overdue": sum(queue_status(a) == "pending" and infos[a["id"]]["wait_hours"] >= 24 for a in state["ads"]), "priority": sum(queue_status(a) == "pending" and infos[a["id"]]["priority"] == "high" for a in state["ads"])}
    q = str(data.get("q", "")).strip().casefold().removeprefix("№")
    people = {**state["users"], **{s["id"]: s for s in state["sellers"]}}
    def selected(a):
        info = infos[a["id"]]
        if data.get("section") and a["section"] != data["section"]: return False
        if data.get("seller_kind") and ("private" if people[a["owner"]]["kind"] == "private" else "company") != data["seller_kind"]: return False
        if q and q not in (a["id"] + " " + people[a["owner"]]["name"]).casefold() and not matches(a, q): return False
        flag = data.get("focus")
        return not flag or (flag == "high" and info["priority"] == "high") or (flag == "repeat" and info["repeat"]) or (flag == "flags" and bool(info["flags"])) or (flag == "overdue" and info["wait_hours"] >= 24)
    rows = [a for a in state["ads"] if queue_status(a) == tab and selected(a)] if tab != "history" else []
    sort = data.get("sort", "priority")
    if sort not in ("priority", "oldest", "newest"): raise DemoError("Выберите порядок очереди")
    rows.sort(key=lambda a: a.get("submitted", a["updated"]), reverse=sort == "newest")
    if sort == "priority": rows.sort(key=lambda a: infos[a["id"]]["priority"] != "high")
    for key in ("date_from", "date_to"):
        if data.get(key):
            try: dt.date.fromisoformat(data[key])
            except ValueError: raise DemoError("Проверьте период истории")
    if data.get("date_from") and data.get("date_to") and data["date_from"] > data["date_to"]: raise DemoError("Начало периода позже окончания")
    log = [x for x in state["moderation_log"] if (not data.get("section") or x["section"] == data["section"]) and (not q or q in (x["title"]+" "+x["ad_id"]+" "+x["reason"]+" "+x["moderator_name"]).casefold()) and (not data.get("decision") or x["decision"] == data["decision"]) and (not data.get("date_from") or x["time"][:10] >= data["date_from"]) and (not data.get("date_to") or x["time"][:10] <= data["date_to"])]
    return {"ids": [a["id"] for a in rows], "counts": counts, "history": log, "info": infos, "stats": stats}


def dispatch(state, action, data):
    if action == "bootstrap":
        return {"categories": CATEGORIES, "cities": CITIES, "statuses": STATUSES, "sections": SECTIONS, "category_groups": CATEGORY_GROUPS, "category_sections": CATEGORY_SECTIONS, "fields": FIELDS}
    if action == "catalog":
        filters = normalize_filters(data.get("filters", data))
        return {"ids": [a["id"] for a in query(state, filters, data.get("owner"))], "filters": filters}
    if action == "search_suggest":
        q = str(data.get("q", ""))[:100].strip()
        if not q: return {"items": []}
        section = data.get("section")
        candidates = [a for a in state["ads"] if a["status"] == "active" and (not section or a["section"] == section) and matches(a, q)]
        items, seen = [], set()
        for a in candidates:
            key = (a["title"], a["category"])
            if key in seen: continue
            seen.add(key)
            items.append({"label": a["title"], "hint": CATEGORIES[a["category"]], "q": a["title"], "section": a["section"], "category": a["category"]})
        return {"items": items[:6]}
    if action in ("moderation_queue", "moderate", "moderation_note", "moderation_priority", "moderation_defer", "moderation_resume"):
        u = user_id(state)
        if state["users"][u].get("role") != "moderator":
            raise DemoError("Кабинет доступен только модератору")
        if action == "moderation_queue":
            return review_queue(state, data)
        a = ad_by_id(state, data.get("id"))
        if data.get("revision") != a.get("revision", 1): raise DemoError("Объявление изменилось. Обновите очередь и проверьте его снова")
        work = state["moderation_work"].setdefault(a["id"], {})
        if action == "moderation_note":
            text = str(data.get("text", "")).strip()
            if not 3 <= len(text) <= 2000: raise DemoError("Заметка должна содержать от 3 до 2 000 символов")
            entry = review_audit(state, a, "note", text)
            work.setdefault("notes", []).insert(0, {"text": text, "author": entry["moderator_name"], "time": entry["time"]})
            return {"message": "Служебная заметка сохранена"}
        if action == "moderation_priority":
            priority = data.get("priority")
            if priority not in ("normal", "high"): raise DemoError("Выберите приоритет")
            if work.get("priority", "normal") != priority:
                work["priority"] = priority
                review_audit(state, a, "priority", "Высокий приоритет" if priority == "high" else "Обычный приоритет")
            return {"message": "Приоритет обновлён"}
        if action in ("moderation_defer", "moderation_resume"):
            if a["status"] != "pending": raise DemoError("Отложить можно только объявление на проверке")
            if action == "moderation_defer":
                minutes = integer(data.get("minutes"), "Время")
                if minutes not in (15, 60, 1440): raise DemoError("Выберите срок: 15 минут, час или сутки")
                reason = str(data.get("reason", "")).strip()
                if len(reason) > 1000: raise DemoError("Комментарий должен быть короче 1 000 символов")
                work["deferred_until"] = (dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=minutes)).isoformat(timespec="seconds")
                review_audit(state, a, "defer", reason or "Отложено на " + str(minutes) + " мин.", deferred_until=work["deferred_until"])
                return {"message": "Проверка отложена"}
            work["deferred_until"] = None
            review_audit(state, a, "resume", "Возвращено в очередь проверки")
            return {"message": "Объявление возвращено в очередь"}
        decision = data.get("decision")
        if decision not in ("approve", "return", "remove"): raise DemoError("Выберите решение модератора")
        if a["status"] != ("active" if decision == "remove" else "pending"):
            raise DemoError("Статус объявления уже изменился. Обновите очередь")
        reason = str(data.get("reason", "")).strip()
        if len(reason) > 1000: raise DemoError("Комментарий должен быть короче 1 000 символов")
        if decision != "approve" and not 10 <= len(reason) <= 1000:
            raise DemoError("Укажите понятную продавцу причину: от 10 до 1 000 символов")
        checks = data.get("checks", {})
        if not isinstance(checks, dict): raise DemoError("Проверьте чек-лист")
        if decision == "approve" and not all(checks.get(k) is True for k in ("photos", "details", "description")):
            raise DemoError("Проверьте фотографии, характеристики и описание")
        if decision == "approve" and any(f["level"] == "error" for f in review_info(state, a)["flags"]):
            raise DemoError("Не заполнены обязательные данные. Верните объявление продавцу с пояснением")
        before = a["status"]
        snapshot = review_snapshot(a)
        a["status"] = "active" if decision == "approve" else "rejected"
        a["rejection"] = reason if decision != "approve" else ""
        a["moderation_hold"] = decision != "approve"
        a["updated"] = now(); a["revision"] = a.get("revision", 1) + 1
        work["deferred_until"] = None
        review_audit(state, a, decision, reason, before=before, snapshot=snapshot, checks=checks)
        notice(state, "Объявление опубликовано" if decision == "approve" else "Нужны исправления", a["title"] + (": " + reason if reason else " прошло модерацию"), a["id"], a["owner"])
        return {"message": "Опубликовано" if decision == "approve" else "Возвращено продавцу на исправление", "id": a["id"]}
    if action == "my_ads":
        u = user_id(state); status = data.get("status", "all"); q = data.get("q", "").casefold()
        statuses = ["pending", "rejected"] if status == "pending" else ["archived", "sold"] if status == "archived" else [status]
        return {"ids": [a["id"] for a in state["ads"] if a["owner"] == u and a["status"] != "deleted" and (status == "all" or a["status"] in statuses) and q in a["title"].casefold()]}
    if action == "validate_ad":
        preview = copy.deepcopy(state)
        result = dispatch(preview, "save_ad", {"ad": data.get("ad", {}), "status": "pending"})
        return {"ad": ad_by_id(preview, result["id"])}
    if action == "demo_user":
        if data.get("user") not in ("azat", "ilya", "moderator"):
            raise DemoError("Выберите тестовый аккаунт")
        state["user_id"] = data["user"]; state["challenge"] = None
        return {"message": "Вы вошли как " + state["users"][data["user"]]["name"]}
    if action == "logout":
        state["user_id"] = None; state["challenge"] = None; return {}
    if action == "request_code":
        digits = re.sub(r"\D", "", data.get("phone", ""))
        if len(digits) != 11 or digits[0] not in "78":
            raise DemoError("Введите номер в формате +7 999 123-45-67")
        state["challenge"] = {"phone": "+7 " + "••• ••• " + digits[-4:-2] + " " + digits[-2:], "expires": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)).isoformat(), "attempts": 0}
        return {"phone": state["challenge"]["phone"], "demo_code": "123456"}
    if action == "verify_code":
        c = state.get("challenge")
        if not c or dt.datetime.fromisoformat(c["expires"]) < dt.datetime.now(dt.timezone.utc):
            raise DemoError("Запросите новый код")
        if str(data.get("code", "")) != "123456":
            raise DemoError("Код не подходит. Для демо используйте 123456")
        state["user_id"] = "azat"; state["challenge"] = None; return {"message": "Вы вошли в аккаунт"}
    if action == "favorite":
        u = user_id(state); a = ad_by_id(state, data.get("id"))
        values = state["favorites"].setdefault(u, [])
        if a["id"] in values: values.remove(a["id"])
        else: values.insert(0, a["id"])
        return {"selected": a["id"] in values}
    if action == "compare_toggle":
        a = ad_by_id(state, data.get("id")); values = state["compare"]
        if a["id"] in values: values.remove(a["id"])
        elif len(values) >= 4: raise DemoError("В сравнении может быть до 4 машин")
        else: values.append(a["id"])
        return {"selected": a["id"] in values}
    if action == "compare_clear":
        state["compare"] = []; return {}
    if action == "save_ad":
        u = user_id(state); values = data.get("ad", {}); ad_id = values.get("id")
        old = ad_by_id(state, ad_id, True) if ad_id else None
        target = data.get("status", "draft")
        if target not in ("draft", "pending", "keep"):
            raise DemoError("Недопустимый статус объявления")
        if target == "keep" and not old: raise DemoError("Объявление не найдено")
        status = ("draft" if old["status"] == "draft" else "pending") if target == "keep" else target
        category = str(values.get("category", "tractor"))
        if category not in CATEGORIES: raise DemoError("Выберите тип техники")
        brand = str(values.get("brand", "")).strip()[:50]; model = str(values.get("model", "")).strip()[:80]
        title = (brand + " " + model).strip() or "Новое объявление"
        description = str(values.get("description", "")).strip()
        if len(description) > 5000: raise DemoError("Описание должно быть короче 5 000 символов")
        price = integer(values.get("price"), "Цена", 1, 10**10)
        year = integer(values.get("year"), "Год выпуска", 1900, dt.datetime.now().year + 1)
        meter = meter_unit(category)
        mileage = integer(values.get("mileage"), "Пробег", 0, 10**8) if meter == "km" else None
        hours = integer(values.get("hours"), "Наработка", 0, 10**8) if meter == "hours" else None
        photos = photo_list(values.get("photos", []))
        city = str(values.get("city", "")).strip()[:80]
        if status != "draft":
            missing = {}
            for k, v, label in (("brand", brand, "Укажите марку"), ("model", model, "Укажите модель"), ("price", price, "Укажите цену"), ("year", year, "Укажите год"), ("city", city, "Укажите город"), ("photos", photos, "Добавьте хотя бы одну фотографию")):
                if not v: missing[k] = label
            if len(description) < 10: missing["description"] = "Добавьте описание от 10 символов"
            if missing: raise DemoError(next(iter(missing.values())), missing)
        ad = dict(old or {})
        ad.update({"id": old["id"] if old else uid("a"), "owner": u, "category": category, "brand": brand, "model": model, "title": title, "price": price, "year": year, "mileage": mileage, "photos": photos, "city": city, "description": description, "status": status, "updated": now(), "created": old["created"] if old else now(), "rejection": ""})
        for k, default in (("wheels", "4×2"), ("gearbox", "Автомат"), ("condition", "used"), ("vat", "no"), ("fuel", "Дизель"), ("asset", "volvo")):
            ad[k] = str(values.get(k, (old or {}).get(k, default)))[:100]
        ad["power"] = integer(values.get("power", (old or {}).get("power")), "Мощность", 1, 3000)
        section = CATEGORY_SECTIONS[category]
        ad.update(section=section, hours=hours, revision=(old or {}).get("revision", 0)+1, availability="order" if values.get("availability") == "order" else "stock")
        for f in FIELDS:
            k = f["key"]
            if not applicable(f, section, category, values):
                ad.pop(k, None)
                continue
            v = values.get(k, (old or {}).get(k))
            if f["type"] == "number": ad[k] = number(v, f["label"])
            elif v in f["options"]: ad[k] = v
            elif v in (None, "", "Не указано", "—"): ad.pop(k, None)
            else: raise DemoError("Проверьте поле «" + f["label"] + "»")
        if status == "pending":
            ad["submitted"] = now()
            state["moderation_work"].setdefault(ad["id"], {})["deferred_until"] = None
        if old: state["ads"][state["ads"].index(old)] = ad
        else: state["ads"].insert(0, ad)
        if target == "pending": notice(state, "Объявление отправлено", title + " на проверке", ad["id"])
        return {"id": ad["id"], "message": "Отправлено на проверку" if target == "pending" else "Черновик сохранён" if status == "draft" else "Изменения сохранены"}
    if action in ("archive", "restore", "sold", "delete_ad"):
        ad = ad_by_id(state, data.get("id"), True)
        if action == "restore":
            if ad["status"] not in ("archived", "sold"): raise DemoError("Восстановить можно объявление из архива")
            ad["status"] = "pending" if ad.get("price") and ad["photos"] else "draft"
            if ad["status"] == "pending":
                ad["submitted"] = now()
                state["moderation_work"].setdefault(ad["id"], {})["deferred_until"] = None
        else:
            ad["status"] = {"archive": "archived", "sold": "sold", "delete_ad": "deleted"}[action]
        ad["updated"] = now()
        ad["revision"] = ad.get("revision", 1) + 1
        notice(state, ad["title"], STATUSES[ad["status"]], ad["id"])
        return {"message": STATUSES[ad["status"]], "id": ad["id"]}
    if action == "start_chat":
        u = user_id(state); ad = ad_by_id(state, data.get("id"))
        if ad["owner"] == u: raise DemoError("Это ваше объявление. Откройте переписку с покупателями")
        if ad["status"] != "active": raise DemoError("Объявление уже недоступно для связи")
        chat = next((c for c in state["conversations"] if c["ad_id"] == ad["id"] and u in c["participants"]), None)
        if not chat:
            chat = {"id": uid("c"), "ad_id": ad["id"], "participants": [u, ad["owner"]], "unread": {}, "messages": []}; state["conversations"].insert(0, chat)
        return {"id": chat["id"]}
    if action in ("send_message", "read_chat", "simulate_reply"):
        u = user_id(state); chat = next((c for c in state["conversations"] if c["id"] == data.get("id") and u in c["participants"]), None)
        if not chat: raise DemoError("Переписка не найдена")
        if action == "read_chat": chat["unread"][u] = 0; return {}
        sender = u if action == "send_message" else next(p for p in chat["participants"] if p != u)
        text = str(data.get("text", "")).strip() if action == "send_message" else "Да, техника в наличии. Можно договориться об осмотре завтра после 15:00."
        attachment = data.get("attachment") if action == "send_message" else None
        if attachment: photo_list([attachment])
        if not text and not attachment: raise DemoError("Введите сообщение или добавьте фотографию")
        if len(text) > 3000: raise DemoError("Сообщение должно быть короче 3 000 символов")
        chat["messages"].append({"id": uid("m"), "sender": sender, "text": text, "attachment": attachment, "time": now()})
        for p in chat["participants"]:
            if p != sender: chat["unread"][p] = chat["unread"].get(p, 0) + 1
        return {"message": "Сообщение отправлено в демо"}
    if action == "save_search":
        u = user_id(state); searches = state["searches"].setdefault(u, []); search_id = data.get("id")
        old = next((s for s in searches if s["id"] == search_id), None)
        if search_id and not old: raise DemoError("Поиск не найден")
        name = str(data.get("name", "")).strip()[:100]
        if not name: raise DemoError("Назовите сохранённый поиск")
        s = {"id": search_id or uid("s"), "name": name, "filters": normalize_filters(data.get("filters", {})), "notify": bool(data.get("notify", True)), "frequency": data.get("frequency", "daily"), "seen": old.get("seen", []) if old else []}
        if s["frequency"] not in ("instant", "daily", "weekly"): raise DemoError("Выберите частоту уведомлений")
        if old: searches[searches.index(old)] = s
        else: searches.insert(0, s)
        return {"id": s["id"], "message": "Поиск сохранён"}
    if action in ("delete_search", "search_preferences", "search_seen"):
        u = user_id(state); searches = state["searches"].setdefault(u, [])
        s = next((s for s in searches if s["id"] == data.get("id")), None)
        if not s: raise DemoError("Поиск не найден")
        if action == "delete_search": searches.remove(s)
        elif action == "search_seen": s["seen"] = [a["id"] for a in query(state, s["filters"])]
        else:
            if "notify" in data: s["notify"] = bool(data["notify"])
            if data.get("frequency") in ("instant", "daily", "weekly"): s["frequency"] = data["frequency"]
        return {}
    if action == "profile":
        u = user_id(state); profile = state["users"][u]
        name = str(data.get("name", profile["name"])).strip()
        if not 2 <= len(name) <= 80: raise DemoError("Имя должно содержать от 2 до 80 символов")
        email = str(data.get("email", profile["email"])).strip()
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email): raise DemoError("Проверьте адрес электронной почты")
        profile.update({"name": name, "email": email, "city": str(data.get("city", profile["city"]))[:80], "kind": "company" if data.get("kind") == "company" else "private"})
        if data.get("phone") and "•" not in data["phone"]:
            digits = re.sub(r"\D", "", data["phone"])
            if len(digits) != 11: raise DemoError("Телефон должен содержать 11 цифр")
            profile["phone"] = "+7 ••• ••• " + digits[-4:-2] + " " + digits[-2:]
        if data.get("avatar"):
            profile["avatar"] = photo_list([data["avatar"]])[0]
        for key in profile["notifications"]:
            if key in data.get("notifications", {}): profile["notifications"][key] = bool(data["notifications"][key])
        return {"message": "Профиль сохранён"}
    if action == "end_sessions":
        u = user_id(state); state["sessions"][u] = [{"id": "current", "name": "Этот браузер", "current": True}]; return {"message": "Другие сеансы завершены"}
    if action == "read_notices":
        u = user_id(state)
        for n in state["notices"]:
            if n["user"] == u: n["read"] = True
        return {}
    if action == "support":
        u = user_id(state); text = str(data.get("text", "")).strip()
        if not 10 <= len(text) <= 3000: raise DemoError("Опишите вопрос: от 10 до 3 000 символов")
        ad_id = data.get("ad_id")
        if ad_id: ad_by_id(state, ad_id, True)
        attachment = data.get("attachment")
        if attachment: photo_list([attachment])
        ticket = {"id": uid("t"), "number": 1001 + len(state["tickets"]), "user": u, "topic": str(data.get("topic", "Вопрос об объявлении"))[:100], "ad_id": ad_id, "text": text, "attachment": attachment, "time": now(), "status": "Принято"}
        state["tickets"].insert(0, ticket); notice(state, "Обращение №" + str(ticket["number"]), "Обращение сохранено в демо")
        return {"number": ticket["number"], "message": "Обращение принято в демо"}
    raise DemoError("Неизвестное действие")


def request(state_json, action, payload_json="{}"):
    """Atomic transport-neutral action. Errors never mutate saved state."""
    try:
        state = json.loads(state_json) if state_json else seed()
        state = migrate(state)
        data = json.loads(payload_json) if payload_json else {}
        if not isinstance(data, dict): raise DemoError("Неверный формат запроса")
        state = copy.deepcopy(state)
        if action == "reset": state = seed(); result = {"message": "Исходные данные восстановлены"}
        else: result = dispatch(state, action, data)
        return json.dumps({"ok": True, "state": state, "summary": overview(state), "result": result}, ensure_ascii=False)
    except DemoError as exc:
        return json.dumps({"ok": False, "error": {"message": str(exc), "fields": exc.fields}}, ensure_ascii=False)
    except (ValueError, TypeError, KeyError) as exc:
        return json.dumps({"ok": False, "error": {"message": "Проверьте заполненные данные", "fields": {}}}, ensure_ascii=False)

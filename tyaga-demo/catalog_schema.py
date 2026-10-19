"""Shared catalog vocabulary and field schema, used by Python and the UI."""
SECTIONS = {
    "cars": "Легковые автомобили", "commercial": "Грузовики и спецтехника",
    "moto": "Мотоциклы и мототехника", "water": "Водный транспорт",
}
CATEGORY_GROUPS = {
    "cars": {"car": "Легковые автомобили"},
    "commercial": {"tractor": "Тягачи", "truck": "Грузовики", "dump": "Самосвалы",
        "lcv": "Лёгкий коммерческий транспорт", "bus": "Автобусы", "trailer": "Прицепы и полуприцепы",
        "excavator": "Экскаваторы", "loader": "Погрузчики", "construction": "Строительная техника",
        "farm": "Сельскохозяйственная техника", "warehouse": "Складская техника", "municipal": "Коммунальная техника"},
    "moto": {"motorcycle": "Мотоциклы", "scooter": "Скутеры и мопеды", "atv": "Квадроциклы и багги", "snowmobile": "Снегоходы"},
    "water": {"motorboat": "Моторные лодки", "boat": "Катера", "yacht": "Яхты", "jetski": "Гидроциклы", "rowing": "Гребные и надувные лодки"},
}
CATEGORIES = {k: v for group in CATEGORY_GROUPS.values() for k, v in group.items()}
CATEGORY_SECTIONS = {k: section for section, group in CATEGORY_GROUPS.items() for k in group}
HOUR_CATEGORIES = {"excavator", "loader", "construction", "farm", "warehouse", "snowmobile", "motorboat", "boat", "yacht", "jetski"}
NO_METER_CATEGORIES = {"trailer", "rowing"}


def select(key, label, options, sections=(), categories=(), when=None):
    return dict(key=key, label=label, type="select", options={s: s for s in options}, sections=list(sections), categories=list(categories), when=when)


def numeric(key, label, unit, sections=(), categories=(), when=None):
    return dict(key=key, label=label, unit=unit, type="number", sections=list(sections), categories=list(categories), when=when)


FIELDS = [
    select("body", "Кузов", ["Седан", "Хэтчбек", "Универсал", "Внедорожник", "Купе", "Минивэн"], ["cars"]),
    select("vehicle_class", "Класс", ["Дорожный", "Спорт", "Эндуро", "Туристический", "Круизер"], categories=["motorcycle"]),
    select("purpose", "Назначение", ["Городской", "Междугородний", "Туристический", "Школьный"], categories=["bus"]),
    select("equipment_type", "Вид техники", ["Кран", "Автовышка", "Каток", "Бульдозер"], categories=["construction"]),
    select("farm_type", "Вид техники", ["Трактор", "Комбайн", "Опрыскиватель", "Посевная техника"], categories=["farm"]),
    select("warehouse_type", "Вид техники", ["Вилочный погрузчик", "Штабелёр", "Ричтрак"], categories=["warehouse"]),
    select("municipal_type", "Назначение", ["Мусоровоз", "Уборочная", "Вакуумная", "Поливомоечная"], categories=["municipal"]),
    select("snow_type", "Назначение", ["Утилитарный", "Туристический", "Горный", "Спортивный"], categories=["snowmobile"]),
    select("hull", "Материал корпуса", ["Алюминий", "Стеклопластик", "Сталь", "ПВХ", "Резина"], ["water"]),
    select("yacht_type", "Тип яхты", ["Моторная", "Парусная"], categories=["yacht"]),
    select("jet_type", "Тип гидроцикла", ["Сидячий", "Стоячий"], categories=["jetski"]),
    select("floor", "Дно лодки", ["Надувное", "Жёсткое", "Пайол"], categories=["rowing"]),
    select("transom", "Транец", ["Встроенный", "Навесной", "Нет"], categories=["rowing"]),
    select("fuel", "Топливо / двигатель", ["Бензин", "Дизель", "Электро", "Гибрид", "Газ"], ["cars", "moto"], ["tractor", "truck", "dump", "lcv", "bus", "excavator", "loader", "construction", "farm", "warehouse", "municipal"]),
    select("gearbox", "Коробка передач", ["Автомат", "Механика", "Робот", "Вариатор"], ["cars"], ["tractor", "truck", "dump", "lcv", "bus", "motorcycle", "scooter", "atv"]),
    select("drive", "Привод", ["Передний", "Задний", "Полный"], ["cars"], ["atv", "farm"]),
    select("wheels", "Колёсная формула", ["4×2", "4×4", "6×2", "6×4", "6×6", "8×4"], categories=["tractor", "truck", "dump", "lcv", "bus", "municipal"]),
    select("chassis", "Ходовая часть", ["Гусеничная", "Колёсная"], categories=["excavator", "loader", "construction"]),
    select("cargo_body", "Тип кузова", ["Бортовой", "Фургон", "Рефрижератор", "Тент", "Самосвальный", "Цистерна", "Платформа"], categories=["truck", "dump", "lcv", "trailer"]),
    select("suspension", "Подвеска", ["Пневматическая", "Рессорная"], categories=["trailer"]),
    select("steering", "Руль", ["Левый", "Правый"], ["cars"]),
    select("taxi", "Использование в такси", ["Нет", "Да"], ["cars"]),
    select("color", "Цвет", ["Белый", "Серебристый", "Серый", "Чёрный", "Синий", "Красный"], ["cars"]),
    select("abs", "ABS", ["Есть", "Нет"], categories=["motorcycle", "scooter", "atv"]),
    select("reverse", "Реверс", ["Есть", "Нет"], categories=["jetski"]),
    select("motor_included", "Мотор в комплекте", ["Да", "Нет"], ["water"]),
    select("trailer_included", "Прицеп в комплекте", ["Да", "Нет"], ["water"]),
    select("motor_type", "Тип мотора", ["Подвесной", "Стационарный", "Водомёт"], categories=["motorboat", "boat", "yacht", "jetski"]),
    numeric("power", "Мощность", "л. с.", ["cars", "moto"], ["tractor", "truck", "dump", "lcv", "bus", "excavator", "loader", "construction", "farm", "warehouse", "municipal"]),
    numeric("engine_cc", "Объём двигателя", "см³", ["cars", "moto"], when={"not": {"fuel": "Электро"}}),
    numeric("battery", "Ёмкость батареи", "кВт⋅ч", ["cars", "moto"], when={"fuel": "Электро"}),
    select("charging", "Зарядный разъём", ["CCS2", "Type 2", "GB/T", "CHAdeMO"], ["cars", "moto"], when={"fuel": "Электро"}),
    numeric("owners", "Владельцев", "", ["cars"]),
    numeric("seats", "Мест", "", ["cars", "water"], ["lcv", "bus", "atv"]),
    numeric("payload", "Грузоподъёмность", "кг", categories=["truck", "dump", "lcv", "trailer", "loader", "warehouse", "rowing"]),
    numeric("gross_weight", "Полная масса", "кг", categories=["truck", "dump", "lcv", "trailer"]),
    numeric("volume", "Объём кузова", "м³", categories=["truck", "dump", "lcv", "trailer"]),
    numeric("cargo_length", "Длина грузового отсека", "м", categories=["truck", "lcv", "trailer"]),
    numeric("cargo_width", "Ширина грузового отсека", "м", categories=["truck", "lcv", "trailer"]),
    numeric("cargo_height", "Высота грузового отсека", "м", categories=["truck", "lcv", "trailer"]),
    numeric("axles", "Количество осей", "", categories=["trailer"]),
    numeric("saddle_load", "Нагрузка на седло", "кг", categories=["tractor"]),
    numeric("saddle_height", "Высота седла", "мм", categories=["tractor"]),
    numeric("berths", "Спальных мест", "", categories=["tractor", "boat", "yacht"]),
    numeric("weight", "Рабочая масса", "кг", categories=["excavator", "loader", "construction"]),
    numeric("bucket", "Объём ковша", "м³", categories=["excavator", "loader"]),
    numeric("dig_depth", "Глубина копания", "м", categories=["excavator"]),
    numeric("lift_height", "Высота подъёма", "м", categories=["loader", "warehouse", "construction"]),
    numeric("crane_capacity", "Грузоподъёмность крана", "т", categories=["construction"], when={"equipment_type": "Кран"}),
    numeric("boom", "Длина стрелы", "м", categories=["construction"], when={"equipment_type": "Кран"}),
    numeric("reach", "Вылет платформы", "м", categories=["construction"], when={"equipment_type": "Автовышка"}),
    numeric("platform_load", "Нагрузка платформы", "кг", categories=["construction"], when={"equipment_type": "Автовышка"}),
    numeric("work_width", "Рабочая ширина", "м", categories=["farm", "municipal", "construction"]),
    numeric("equipment_hours", "Наработка оборудования", "м/ч", categories=["municipal"]),
    numeric("tank", "Объём цистерны", "м³", categories=["municipal"]),
    numeric("seat_height", "Высота сиденья", "мм", categories=["motorcycle"]),
    numeric("wheel_size", "Диаметр колёс", "дюйм", categories=["scooter"]),
    numeric("track_length", "Длина гусеницы", "мм", categories=["snowmobile"]),
    numeric("track_width", "Ширина гусеницы", "мм", categories=["snowmobile"]),
    numeric("length", "Длина", "м", ["water"], ["bus"]),
    numeric("width", "Ширина", "м", ["water"]),
    numeric("draft", "Осадка", "м", categories=["motorboat", "boat", "yacht"]),
    numeric("cabins", "Кают", "", categories=["boat", "yacht"]),
    numeric("motor_power", "Мощность установленного мотора", "л. с.", ["water"]),
    numeric("max_motor_power", "Допустимая мощность мотора", "л. с.", categories=["rowing", "motorboat"]),
    numeric("motors", "Моторов", "", categories=["motorboat", "boat", "yacht"]),
]


def applicable(field, section, category="", values=None):
    if section not in field["sections"] and category not in field["categories"]:
        return False
    values = values or {}
    when = field.get("when")
    if not when:
        return True
    if "not" in when:
        return all(values.get(k) != v for k, v in when["not"].items())
    return all(values.get(k) == v for k, v in when.items())


def meter_unit(category):
    return None if category in NO_METER_CATEGORIES else "hours" if category in HOUR_CATEGORIES else "km"

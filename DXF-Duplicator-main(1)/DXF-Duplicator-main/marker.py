import os
import math


TEXT_HEIGHT = 25.0

# --------------------------------------------------
# Настройки отметки кромки
# --------------------------------------------------

EDGE_LAYER = "ED_Кром. в цвет"

EDGE_MARK_LENGTH = 7.0
EDGE_MARK_OFFSET = 20.0


# ==================================================
# МАРКИРОВКА
# ==================================================

def make_mark_text(filename, has_back):
    """
    I_6_2.DXF + I_6_O_2.DXF -> I6
    I_6_2.DXF без оборота -> I

    Арабская часть остается обычным MTEXT.
    Римская часть рисуется линиями.
    """

    name = os.path.splitext(filename)[0]
    parts = name.split("_")

    if len(parts) < 2:
        return parts[0]

    prefix = parts[0]
    number = parts[1]

    if has_back:
        return f"{prefix}{number}"

    return prefix


# ==================================================
# РИМСКИЕ ЦИФРЫ
# ==================================================

def split_roman_prefix(text):
    """
    Возвращает:

        (римская часть, арабская часть)

    Примеры:

        I      -> ("I", "")
        IV     -> ("IV", "")
        I4     -> ("I", "4")
        III7   -> ("III", "7")
        12     -> ("", "12")
    """

    roman = []
    i = 0

    while i < len(text) and text[i].upper() in "IVX":
        roman.append(text[i].upper())
        i += 1

    return "".join(roman), text[i:]


def roman_is_vector(text):
    roman, arabic = split_roman_prefix(text)

    return (
        bool(roman)
        and all(ch in "IVX" for ch in roman)
    )


def roman_glyphs(text, height):
    """
    Построение римских цифр линиями.

    I = 1 линия
    V = 2 линии
    X = 2 линии
    """

    h = float(height)

    w_i = h * 0.22
    w_v = h * 0.48
    gap = h * 0.22

    segments = []

    x = 0.0

    for ch in text:

        if ch == "I":

            segments.append(
                (
                    x,
                    0.0,
                    x,
                    h
                )
            )

            x += w_i + gap

        elif ch == "V":

            left = x
            right = x + w_v
            bottom = x + w_v / 2.0

            segments.append(
                (
                    left,
                    h,
                    bottom,
                    0.0
                )
            )

            segments.append(
                (
                    bottom,
                    0.0,
                    right,
                    h
                )
            )

            x += w_v + gap

        elif ch == "X":

            left = x
            right = x + w_v

            segments.append(
                (
                    left,
                    0.0,
                    right,
                    h
                )
            )

            segments.append(
                (
                    left,
                    h,
                    right,
                    0.0
                )
            )

            x += w_v + gap

    if segments:
        total_width = x - gap
    else:
        total_width = 0.0

    return segments, total_width


# ==================================================
# ПОИСК MTEXT
# ==================================================

def _find_mtext(lines):

    start = None

    for i in range(len(lines) - 1):

        if (
            lines[i].strip() == "0"
            and
            lines[i + 1].strip() == "MTEXT"
        ):

            start = i
            break

    if start is None:
        return None, None, None

    end = start + 2

    while end < len(lines):

        if lines[end].strip() == "0":
            break

        end += 1

    return start, end, lines[start:end]


# ==================================================
# DXF GROUP FUNCTIONS
# ==================================================

def _get_group_value(entity_lines, code, default=None):

    for i in range(len(entity_lines) - 1):

        if entity_lines[i].strip() == str(code):

            return entity_lines[i + 1].strip()

    return default


def _set_group_value(entity_lines, code, value):

    for i in range(len(entity_lines) - 1):

        if entity_lines[i].strip() == str(code):

            entity_lines[i + 1] = str(value) + "\n"

            return True

    return False


# ==================================================
# HANDLE
# ==================================================

def _next_handle(lines):

    max_handle = 0

    for i in range(len(lines) - 1):

        if lines[i].strip() in (
            "5",
            "105",
            "320",
            "330"
        ):

            value = lines[i + 1].strip()

            try:

                max_handle = max(
                    max_handle,
                    int(value, 16)
                )

            except Exception:
                pass

    return f"{max_handle + 1:X}"


def _update_handseed(lines, handle):

    for i in range(len(lines) - 1):

        if lines[i].strip() == "$HANDSEED":

            j = i + 1

            while j < min(i + 8, len(lines) - 1):

                if lines[j].strip() == "5":

                    lines[j + 1] = handle + "\n"

                    return

                j += 1


# ==================================================
# ПОВОРОТ
# ==================================================

def _rotate_point(x, y, angle_deg):

    a = math.radians(angle_deg)

    ca = math.cos(a)
    sa = math.sin(a)

    return (
        x * ca - y * sa,
        x * sa + y * ca
    )


# ==================================================
# СОЗДАНИЕ LINE
# ==================================================

def _make_line(
    handle,
    owner,
    layer,
    x1,
    y1,
    x2,
    y2
):

    return [

        "0\n",
        "LINE\n",

        "  5\n",
        f"{handle}\n",

        "330\n",
        f"{owner}\n",

        "100\n",
        "AcDbEntity\n",

        "  8\n",
        f"{layer}\n",

        "  6\n",
        "CONTINUOUS\n",

        "100\n",
        "AcDbLine\n",

        " 10\n",
        f"{x1:.6f}\n",

        " 20\n",
        f"{y1:.6f}\n",

        " 30\n",
        "0.0\n",

        " 11\n",
        f"{x2:.6f}\n",

        " 21\n",
        f"{y2:.6f}\n",

        " 31\n",
        "0.0\n",
    ]


# ==================================================
# ARABIC MTEXT
# ==================================================

def _prepare_arabic_mtext(
    entity_lines,
    arabic_text,
    x,
    y,
    angle,
    height
):

    result = list(entity_lines)

    _set_group_value(
        result,
        10,
        f"{x:.6f}"
    )

    _set_group_value(
        result,
        20,
        f"{y:.6f}"
    )

    _set_group_value(
        result,
        40,
        f"{height:g}"
    )

    _set_group_value(
        result,
        50,
        f"{angle:g}"
    )

    _set_group_value(
        result,
        1,
        arabic_text
    )

    return result


# ==================================================
# РИМСКАЯ НАДПИСЬ
# ==================================================

def _replace_roman_mtext(
    lines,
    start,
    end,
    entity_lines,
    new_text,
    angle
):

    roman, arabic = split_roman_prefix(new_text)

    if not roman:
        return None

    height = float(
        _get_group_value(
            entity_lines,
            40,
            TEXT_HEIGHT
        )
    )

    insert_x = float(
        _get_group_value(
            entity_lines,
            10,
            0.0
        )
    )

    insert_y = float(
        _get_group_value(
            entity_lines,
            20,
            0.0
        )
    )

    layer = _get_group_value(
        entity_lines,
        8,
        "0"
    )

    owner = _get_group_value(
        entity_lines,
        330,
        "1F"
    )

    segments, roman_width = roman_glyphs(
        roman,
        height
    )

    new_entities = []

    next_handle_int = 0

    for i in range(len(lines) - 1):

        if lines[i].strip() in (
            "5",
            "105",
            "320",
            "330"
        ):

            value = lines[i + 1].strip()

            try:

                next_handle_int = max(
                    next_handle_int,
                    int(value, 16)
                )

            except Exception:
                pass

    next_handle_int += 1

    def get_handle():

        nonlocal next_handle_int

        h = f"{next_handle_int:X}"

        next_handle_int += 1

        return h

    # --------------------------------------------------
    # Римские линии
    # --------------------------------------------------

    for x1, y1, x2, y2 in segments:

        rx1, ry1 = _rotate_point(
            x1,
            y1,
            angle
        )

        rx2, ry2 = _rotate_point(
            x2,
            y2,
            angle
        )

        new_entities.extend(
            _make_line(
                get_handle(),
                owner,
                layer,
                insert_x + rx1,
                insert_y + ry1,
                insert_x + rx2,
                insert_y + ry2
            )
        )

    # --------------------------------------------------
    # Арабская часть
    # --------------------------------------------------

    if arabic:

        gap = height * 0.25

        shift_x = roman_width + gap

        rx, ry = _rotate_point(
            shift_x,
            0.0,
            angle
        )

        arabic_entity = _prepare_arabic_mtext(
            entity_lines,
            arabic,
            insert_x + rx,
            insert_y + ry,
            angle,
            height
        )

        _set_group_value(
            arabic_entity,
            5,
            get_handle()
        )

        new_entities.extend(
            arabic_entity
        )

    _update_handseed(
        lines,
        f"{next_handle_int:X}"
    )

    return new_entities


# ==================================================
# ПАРСИНГ LINE
# ==================================================

def _parse_line_entity(entity):

    layer = _get_group_value(
        entity,
        8,
        ""
    )

    if layer != EDGE_LAYER:
        return None

    try:

        x1 = float(
            _get_group_value(
                entity,
                10,
                0
            )
        )

        y1 = float(
            _get_group_value(
                entity,
                20,
                0
            )
        )

        x2 = float(
            _get_group_value(
                entity,
                11,
                0
            )
        )

        y2 = float(
            _get_group_value(
                entity,
                21,
                0
            )
        )

    except Exception:

        return None

    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2
    }


# ==================================================
# ПОИСК ГАБАРИТОВ ПАНЕЛИ
# ==================================================



def _is_entity_start(lines, index):
    """Возвращает True только для реального начала DXF-сущности.

    Нельзя считать любой group code/value 0 началом сущности:
    у LWPOLYLINE значение координаты Y (group code 20) вполне может быть 0.
    """
    if index < 0 or index + 1 >= len(lines):
        return False
    if lines[index].strip() != "0":
        return False
    value = lines[index + 1].strip()
    return bool(value) and not value.replace('.', '', 1).replace('-', '', 1).isdigit()


def _get_panel_bounds(lines):

    """
    Ищем реальные габариты панели.

    В DXF Базиса обычно есть LWPOLYLINE
    FK_16, которая содержит контур панели.

    Если FK_16 найти нельзя,
    используем геометрию линий ED_Кром.
    """

    points = []

    i = 0

    while i < len(lines):

        if (
            lines[i].strip() == "0"
            and
            i + 1 < len(lines)
            and
            lines[i + 1].strip() == "LWPOLYLINE"
        ):

            entity = []

            j = i

            while j < len(lines):

                if j > i and _is_entity_start(lines, j):

                    break

                entity.append(lines[j])

                j += 1

            layer = _get_group_value(
                entity,
                8,
                ""
            )

            # Контур панели
            if layer == "FK_16":

                for k in range(len(entity) - 1):

                    if entity[k].strip() == "10":

                        try:

                            x = float(
                                entity[k + 1].strip()
                            )

                            # Ищем следующий код 20
                            for m in range(
                                k + 2,
                                min(k + 6, len(entity) - 1)
                            ):

                                if entity[m].strip() == "20":

                                    y = float(
                                        entity[m + 1].strip()
                                    )

                                    points.append(
                                        (x, y)
                                    )

                                    break

                        except Exception:
                            pass

            i = j

        else:

            i += 1

    if not points:

        return None

    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)

    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)

    return (
        min_x,
        min_y,
        max_x,
        max_y
    )


# ==================================================
# СОЗДАНИЕ ОТМЕТКИ КРОМКИ
# ==================================================

def _make_edge_mark(
    line,
    bounds,
    handle
):

    """
    Берем существующую длинную линию ED_Кром.
    Вместо неё создаем короткую линию 7 мм,
    отступив 20 мм внутрь панели.

    Линия ставится по центру соответствующей стороны.
    """

    if bounds is None:
        return None

    min_x, min_y, max_x, max_y = bounds

    x1 = line["x1"]
    y1 = line["y1"]

    x2 = line["x2"]
    y2 = line["y2"]

    tolerance = 0.5

    # --------------------------------------------------
    # Вертикальная линия
    # --------------------------------------------------

    if abs(x1 - x2) < tolerance:

        edge_x = (x1 + x2) / 2.0

        # Левая сторона
        if abs(edge_x - min_x) < tolerance:

            x = min_x + EDGE_MARK_OFFSET

        # Правая сторона
        elif abs(edge_x - max_x) < tolerance:

            x = max_x - EDGE_MARK_OFFSET

        else:

            return None

        center_y = (
            max(min(y1, y2), min_y)
            +
            min(max(y1, y2), max_y)
        ) / 2.0

        y_start = (
            center_y
            -
            EDGE_MARK_LENGTH / 2.0
        )

        y_end = (
            center_y
            +
            EDGE_MARK_LENGTH / 2.0
        )

        return _make_line(
            handle,
            "1F",
            EDGE_LAYER,
            x,
            y_start,
            x,
            y_end
        )

    # --------------------------------------------------
    # Горизонтальная линия
    # --------------------------------------------------

    if abs(y1 - y2) < tolerance:

        edge_y = (y1 + y2) / 2.0

        # Нижняя сторона
        if abs(edge_y - min_y) < tolerance:

            y = min_y + EDGE_MARK_OFFSET

        # Верхняя сторона
        elif abs(edge_y - max_y) < tolerance:

            y = max_y - EDGE_MARK_OFFSET

        else:

            return None

        center_x = (
            max(min(x1, x2), min_x)
            +
            min(max(x1, x2), max_x)
        ) / 2.0

        x_start = (
            center_x
            -
            EDGE_MARK_LENGTH / 2.0
        )

        x_end = (
            center_x
            +
            EDGE_MARK_LENGTH / 2.0
        )

        return _make_line(
            handle,
            "1F",
            EDGE_LAYER,
            x_start,
            y,
            x_end,
            y
        )

    return None


# ==================================================
# ОБРАБОТКА КРОМКИ
# ==================================================

def _replace_edge_lines(lines):

    """
    Ищет существующие LINE слоя:

        ED_Кром. в цвет

    и заменяет длинную линию кромки
    коротким маркером 7 мм.

    Исходная длинная линия удаляется.
    """

    bounds = _get_panel_bounds(lines)

    if bounds is None:
        return lines

    # --------------------------------------------------
    # Находим свободный handle
    # --------------------------------------------------

    max_handle = 0

    for i in range(len(lines) - 1):

        if lines[i].strip() in (
            "5",
            "105"
        ):

            try:

                value = lines[i + 1].strip()

                max_handle = max(
                    max_handle,
                    int(value, 16)
                )

            except Exception:
                pass

    next_handle = max_handle + 1

    # --------------------------------------------------
    # Перебираем ENTITY
    # --------------------------------------------------

    result = []

    i = 0

    edge_count = 0

    while i < len(lines):

        # Начало LINE
        if (
            lines[i].strip() == "0"
            and
            i + 1 < len(lines)
            and
            lines[i + 1].strip() == "LINE"
        ):

            start = i

            j = i + 2

            while j < len(lines):

                if _is_entity_start(lines, j):

                    break

                j += 1

            entity = lines[start:j]

            parsed = _parse_line_entity(
                entity
            )

            # --------------------------------------------------
            # Это линия ED_Кром
            # --------------------------------------------------

            if parsed is not None:

                new_line = _make_edge_mark(
                    parsed,
                    bounds,
                    f"{next_handle:X}"
                )

                if new_line is not None:

                    result.extend(
                        new_line
                    )

                    next_handle += 1

                    edge_count += 1

                    i = j

                    continue

            # Обычная LINE
            result.extend(entity)

            i = j

            continue

        result.append(lines[i])

        i += 1

    # --------------------------------------------------
    # Обновляем HANDSEED
    # --------------------------------------------------

    if edge_count:

        _update_handseed(
            result,
            f"{next_handle:X}"
        )

    return result


# ==================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ==================================================

def modify_dxf_text(filepath, new_text):

    """
    Обработка DXF Базиса.

    1. Римские цифры превращаются в LINE.
    2. Арабские цифры остаются MTEXT.
    3. Существующая длинная линия слоя
       ED_Кром. в цвет заменяется на маркер 7 мм.
    """

    with open(
        filepath,
        "r",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        lines = f.readlines()

    # ==================================================
    # СНАЧАЛА КРОМКА
    # ==================================================

    lines = _replace_edge_lines(
        lines
    )

    # ==================================================
    # ОПРЕДЕЛЯЕМ ГАБАРИТЫ ДЛЯ ПОВОРОТА НОМЕРА
    # ==================================================

    min_x = None
    min_y = None
    max_x = None
    max_y = None

    for i in range(len(lines) - 1):

        code = lines[i].strip()

        if code == "$EXTMIN":

            j = i + 1

            while j < min(
                i + 30,
                len(lines) - 1
            ):

                if lines[j].strip() == "10":

                    try:
                        min_x = float(
                            lines[j + 1].strip()
                        )
                    except Exception:
                        pass

                elif lines[j].strip() == "20":

                    try:
                        min_y = float(
                            lines[j + 1].strip()
                        )
                    except Exception:
                        pass

                j += 1

        elif code == "$EXTMAX":

            j = i + 1

            while j < min(
                i + 30,
                len(lines) - 1
            ):

                if lines[j].strip() == "10":

                    try:
                        max_x = float(
                            lines[j + 1].strip()
                        )
                    except Exception:
                        pass

                elif lines[j].strip() == "20":

                    try:
                        max_y = float(
                            lines[j + 1].strip()
                        )
                    except Exception:
                        pass

                j += 1

    angle = 0.0

    if (
        min_x is not None
        and
        min_y is not None
        and
        max_x is not None
        and
        max_y is not None
    ):

        width = max_x - min_x
        height = max_y - min_y

        if height > width:

            angle = 90.0

    # ==================================================
    # ИЩЕМ MTEXT
    # ==================================================

    start, end, entity_lines = _find_mtext(
        lines
    )

    if entity_lines is None:

        raise Exception(
            "Не найден MTEXT для замены"
        )

    # ==================================================
    # РИМСКАЯ ЧАСТЬ
    # ==================================================

    if roman_is_vector(new_text):

        replacement = _replace_roman_mtext(
            lines,
            start,
            end,
            entity_lines,
            new_text,
            angle
        )

        if replacement is None:

            raise Exception(
                "Не удалось построить римскую надпись"
            )

        lines = (
            lines[:start]
            +
            replacement
            +
            lines[end:]
        )

    # ==================================================
    # АРАБСКАЯ ЧАСТЬ
    # ==================================================

    else:

        inside = False

        result = []

        for i, line in enumerate(lines):

            s = line.strip()

            if (
                s == "0"
                and
                i + 1 < len(lines)
                and
                lines[i + 1].strip() == "MTEXT"
            ):

                inside = True

                result.append(line)

                continue

            if inside and s == "40":

                result.append(line)

                result.append(
                    f"{TEXT_HEIGHT:g}\n"
                )

                continue

            if inside and s == "41":

                result.append(line)

                if i + 1 < len(lines):

                    result.append(
                        lines[i + 1]
                    )

                result.append(
                    "50\n"
                )

                result.append(
                    f"{angle:g}\n"
                )

                continue

            if inside and s == "1":

                result.append(line)

                result.append(
                    new_text + "\n"
                )

                inside = False

                continue

            result.append(line)

        lines = result

    # ==================================================
    # СОХРАНЯЕМ
    # ==================================================

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        f.writelines(lines)

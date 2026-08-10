import os
import math


TEXT_HEIGHT = 25.0
ROMAN_GAP = 6.0

# ============================================================
# НАСТРОЙКИ МАРКЕРА КРОМКИ
# ============================================================

EDGE_LAYER = "ED_Кром. в цвет"

EDGE_MARK_LENGTH = 7.0
EDGE_MARK_OFFSET = 20.0

# Допуск определения, что линия действительно находится
# на границе панели
EDGE_TOLERANCE = 1.0


# ============================================================
# РИМСКАЯ МАРКИРОВКА
# ============================================================

def make_mark_text(filename, has_back):
    """
    I_6_2.DXF + I_6_O_2.DXF -> I6
    I_6_2.DXF без оборота -> I

    Арабская часть остается обычным MTEXT.
    Римская часть строится LINE.
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


def split_roman_prefix(text):
    """
    Возвращает:

        римская часть
        арабская часть

    Например:

        I       -> I, ""
        IV      -> IV, ""
        I4      -> I, 4
        III7    -> III, 7
        12      -> "", 12
    """

    roman = []
    i = 0

    while i < len(text) and text[i].upper() in "IVX":
        roman.append(text[i].upper())
        i += 1

    return "".join(roman), text[i:]


def roman_is_vector(text):
    roman, arabic = split_roman_prefix(text)

    return bool(roman) and all(
        ch in "IVX"
        for ch in roman
    )


def roman_glyphs(text, height):
    """
    Римские цифры строятся только отрезками.

    I = 1 линия
    V = 2 линии
    X = 2 линии

    Поэтому:

    I    = 1
    II   = 2
    III  = 3
    IV   = 3
    V    = 2
    VI   = 3
    VII  = 4
    VIII = 5
    IX   = 3
    X    = 2
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


# ============================================================
# ПОИСК MTEXT
# ============================================================

def _find_mtext(lines):

    start = None

    for i in range(len(lines) - 1):

        if (
            lines[i].strip() == "0"
            and lines[i + 1].strip() == "MTEXT"
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


# ============================================================
# HANDLE
# ============================================================

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

            while j < min(
                i + 8,
                len(lines) - 1
            ):

                if lines[j].strip() == "5":

                    lines[j + 1] = handle + "\n"

                    return

                j += 1


# ============================================================
# ГЕОМЕТРИЯ
# ============================================================

def _rotate_point(x, y, angle_deg):

    a = math.radians(angle_deg)

    ca = math.cos(a)
    sa = math.sin(a)

    return (
        x * ca - y * sa,
        x * sa + y * ca
    )


# ============================================================
# СОЗДАНИЕ LINE
# ============================================================

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


# ============================================================
# АРАБСКИЙ MTEXT
# ============================================================

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


# ============================================================
# РИМСКАЯ НАДПИСЬ
# ============================================================

def _replace_roman_mtext(
    lines,
    start,
    end,
    entity_lines,
    new_text,
    angle
):

    roman, arabic = split_roman_prefix(
        new_text
    )

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

    # ----------------------------------------
    # Римские линии
    # ----------------------------------------

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

    # ----------------------------------------
    # Арабская часть
    # ----------------------------------------

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


# ============================================================
# ПОЛУЧЕНИЕ ГАБАРИТОВ ПАНЕЛИ
# ============================================================

def _get_panel_bounds(lines):

    points = []

    current_layer = None
    current_type = None

    i = 0

    while i < len(lines) - 1:

        code = lines[i].strip()
        value = lines[i + 1].strip()

        # ----------------------------------------
        # Определяем начало сущности
        # ----------------------------------------

        if code == "0":

            current_type = value
            current_layer = None

        # ----------------------------------------
        # Слой
        # ----------------------------------------

        elif code == "8":

            current_layer = value

        # ----------------------------------------
        # Координаты LWPOLYLINE
        # ----------------------------------------

        elif (
            current_type == "LWPOLYLINE"
            and current_layer == "FK_16"
            and code == "10"
        ):

            try:

                x = float(value)

                if i + 2 < len(lines):

                    if lines[i + 2].strip() == "20":

                        y = float(
                            lines[i + 3].strip()
                        )

                        points.append(
                            (x, y)
                        )

            except Exception:
                pass

        i += 1

    # ----------------------------------------
    # Если FK_16 не найден,
    # пробуем найти любую LWPOLYLINE
    # ----------------------------------------

    if not points:

        current_layer = None
        current_type = None

        i = 0

        while i < len(lines) - 1:

            code = lines[i].strip()
            value = lines[i + 1].strip()

            if code == "0":

                current_type = value
                current_layer = None

            elif code == "8":

                current_layer = value

            elif (
                current_type == "LWPOLYLINE"
                and code == "10"
            ):

                try:

                    x = float(value)

                    if i + 2 < len(lines):

                        if lines[i + 2].strip() == "20":

                            y = float(
                                lines[i + 3].strip()
                            )

                            points.append(
                                (x, y)
                            )

                except Exception:
                    pass

            i += 1

    if not points:

        return None

    min_x = min(
        p[0]
        for p in points
    )

    max_x = max(
        p[0]
        for p in points
    )

    min_y = min(
        p[1]
        for p in points
    )

    max_y = max(
        p[1]
        for p in points
    )

    return (
        min_x,
        min_y,
        max_x,
        max_y
    )


# ============================================================
# ПОИСК ЛИНИЙ КРОМКИ
# ============================================================

def _find_edge_lines(lines):

    result = []

    current_type = None
    current_layer = None

    x1 = None
    y1 = None
    x2 = None
    y2 = None

    entity_start = None

    i = 0

    while i < len(lines) - 1:

        code = lines[i].strip()
        value = lines[i + 1].strip()

        # ----------------------------------------
        # Новая сущность
        # ----------------------------------------

        if code == "0":

            # Сохраняем предыдущую LINE
            if (
                current_type == "LINE"
                and current_layer == EDGE_LAYER
                and x1 is not None
                and y1 is not None
                and x2 is not None
                and y2 is not None
            ):

                result.append(
                    {
                        "start": entity_start,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2
                    }
                )

            current_type = value
            current_layer = None

            x1 = None
            y1 = None
            x2 = None
            y2 = None

            entity_start = i

        elif code == "8":

            current_layer = value

        elif (
            current_type == "LINE"
            and code == "10"
        ):

            try:
                x1 = float(value)
            except Exception:
                pass

        elif (
            current_type == "LINE"
            and code == "20"
        ):

            try:
                y1 = float(value)
            except Exception:
                pass

        elif (
            current_type == "LINE"
            and code == "11"
        ):

            try:
                x2 = float(value)
            except Exception:
                pass

        elif (
            current_type == "LINE"
            and code == "21"
        ):

            try:
                y2 = float(value)
            except Exception:
                pass

        i += 1

    # ----------------------------------------
    # Последняя сущность
    # ----------------------------------------

    if (
        current_type == "LINE"
        and current_layer == EDGE_LAYER
        and x1 is not None
        and y1 is not None
        and x2 is not None
        and y2 is not None
    ):

        result.append(
            {
                "start": entity_start,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2
            }
        )

    return result


# ============================================================
# СОЗДАНИЕ МАРКЕРОВ КРОМКИ
# ============================================================

def _make_edge_markers(
    lines,
    panel_bounds,
    edge_lines
):

    if not panel_bounds:
        return []

    min_x, min_y, max_x, max_y = panel_bounds

    if not edge_lines:
        return []

    # ----------------------------------------
    # Ищем максимальный handle
    # ----------------------------------------

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

    # ----------------------------------------
    # Owner Model Space
    # ----------------------------------------

    owner = "1F"

    new_entities = []

    # ----------------------------------------
    # Проверяем каждую линию кромки
    # ----------------------------------------

    for edge in edge_lines:

        x1 = edge["x1"]
        y1 = edge["y1"]

        x2 = edge["x2"]
        y2 = edge["y2"]

        dx = x2 - x1
        dy = y2 - y1

        length = math.sqrt(
            dx * dx + dy * dy
        )

        if length <= 0.001:
            continue

        # ----------------------------------------
        # Определяем, какая это сторона панели
        # ----------------------------------------

        side = None

        if (
            abs(y1 - min_y) <= EDGE_TOLERANCE
            and abs(y2 - min_y) <= EDGE_TOLERANCE
        ):

            side = "BOTTOM"

        elif (
            abs(y1 - max_y) <= EDGE_TOLERANCE
            and abs(y2 - max_y) <= EDGE_TOLERANCE
        ):

            side = "TOP"

        elif (
            abs(x1 - min_x) <= EDGE_TOLERANCE
            and abs(x2 - min_x) <= EDGE_TOLERANCE
        ):

            side = "LEFT"

        elif (
            abs(x1 - max_x) <= EDGE_TOLERANCE
            and abs(x2 - max_x) <= EDGE_TOLERANCE
        ):

            side = "RIGHT"

        else:

            # Линия на слое кромки есть,
            # но она не совпала с границей панели.
            continue

        # ----------------------------------------
        # Центр линии кромки
        # ----------------------------------------

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        # ----------------------------------------
        # Направление вдоль кромки
        # ----------------------------------------

        ux = dx / length
        uy = dy / length

        # ----------------------------------------
        # Отступ внутрь панели = 20 мм
        # ----------------------------------------

        if side == "BOTTOM":

            offset_x = 0.0
            offset_y = EDGE_MARK_OFFSET

        elif side == "TOP":

            offset_x = 0.0
            offset_y = -EDGE_MARK_OFFSET

        elif side == "LEFT":

            offset_x = EDGE_MARK_OFFSET
            offset_y = 0.0

        elif side == "RIGHT":

            offset_x = -EDGE_MARK_OFFSET
            offset_y = 0.0

        else:

            continue

        mx = cx + offset_x
        my = cy + offset_y

        # ----------------------------------------
        # Длина маркера 7 мм
        # ----------------------------------------

        half = EDGE_MARK_LENGTH / 2.0

        mark_x1 = mx - ux * half
        mark_y1 = my - uy * half

        mark_x2 = mx + ux * half
        mark_y2 = my + uy * half

        # ----------------------------------------
        # Создаём НОВУЮ линию.
        #
        # Исходная линия кромки остается!
        # ----------------------------------------

        new_entities.extend(
            _make_line(
                get_handle(),
                owner,
                EDGE_LAYER,
                mark_x1,
                mark_y1,
                mark_x2,
                mark_y2
            )
        )

    return new_entities


# ============================================================
# ДОБАВЛЕНИЕ МАРКЕРОВ В DXF
# ============================================================

def _insert_edge_markers(
    lines,
    panel_bounds
):

    edge_lines = _find_edge_lines(
        lines
    )

    if not edge_lines:
        return lines, 0

    new_entities = _make_edge_markers(
        lines,
        panel_bounds,
        edge_lines
    )

    if not new_entities:
        return lines, 0

    # ----------------------------------------
    # ВАЖНО:
    #
    # Ничего из существующего DXF
    # не удаляем.
    #
    # Просто вставляем новые LINE
    # перед ENDSEC секции ENTITIES.
    # ----------------------------------------

    insert_index = None

    in_entities = False

    for i in range(len(lines) - 1):

        if (
            lines[i].strip() == "2"
            and lines[i + 1].strip() == "ENTITIES"
        ):

            in_entities = True
            continue

        if in_entities:

            if (
                lines[i].strip() == "0"
                and lines[i + 1].strip() == "ENDSEC"
            ):

                insert_index = i
                break

    if insert_index is None:
        return lines, 0

    lines = (
        lines[:insert_index]
        + new_entities
        + lines[insert_index:]
    )

    # ----------------------------------------
    # Обновляем HANDSEED
    # ----------------------------------------

    new_handle = _next_handle(
        lines
    )

    _update_handseed(
        lines,
        new_handle
    )

    return (
        lines,
        len(new_entities) // 16
    )


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

def modify_dxf_text(
    filepath,
    new_text
):

    """
    Обработка DXF Базиса.

    Арабские цифры:
        остаются обычным MTEXT.

    Римские цифры:
        строятся LINE.

    Кромка:
        исходные линии слоя ED_Кром. в цвет
        НЕ УДАЛЯЮТСЯ.

        Для каждой найденной стороны кромки
        добавляется новый отрезок:

            длина = 7 мм
            отступ = 20 мм внутрь панели

        новый отрезок также находится
        на слое ED_Кром. в цвет.
    """

    # ========================================================
    # ЧИТАЕМ DXF
    # ========================================================

    with open(
        filepath,
        "r",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        lines = f.readlines()

    # ========================================================
    # ОПРЕДЕЛЯЕМ ГАБАРИТ ПАНЕЛИ
    # ========================================================

    panel_bounds = _get_panel_bounds(
        lines
    )

    # ========================================================
    # ОПРЕДЕЛЯЕМ ПОВОРОТ ТЕКСТА
    # ========================================================

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
        and min_y is not None
        and max_x is not None
        and max_y is not None
    ):

        width = max_x - min_x
        height = max_y - min_y

        if height > width:

            angle = 90.0

    # ========================================================
    # ИЩЕМ MTEXT
    # ========================================================

    start, end, entity_lines = _find_mtext(
        lines
    )

    if entity_lines is None:

        raise Exception(
            "Не найден MTEXT для замены"
        )

    # ========================================================
    # РИМСКАЯ НАДПИСЬ
    # ========================================================

    if roman_is_vector(
        new_text
    ):

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
            + replacement
            + lines[end:]
        )

    # ========================================================
    # АРАБСКАЯ НАДПИСЬ
    # ========================================================

    else:

        inside = False

        result = []

        for i, line in enumerate(lines):

            s = line.strip()

            if (
                s == "0"
                and i + 1 < len(lines)
                and lines[i + 1].strip() == "MTEXT"
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

    # ========================================================
    # ДОБАВЛЯЕМ МАРКЕРЫ КРОМКИ
    #
    # ВАЖНО:
    # исходные линии НЕ удаляются.
    # ========================================================

    lines, marker_count = _insert_edge_markers(
        lines,
        panel_bounds
    )

    # ========================================================
    # ЗАПИСЫВАЕМ DXF
    # ========================================================

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        f.writelines(lines)

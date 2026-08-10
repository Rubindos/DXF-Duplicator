import os
import math


TEXT_HEIGHT = 25.0
ROMAN_GAP = 6.0

# ============================================================
# НАСТРОЙКИ МАРКЕРА КРОМКИ
# ============================================================

EDGE_LAYER = "ED_Кром. в цвет"

# Отступ маркера от кромки внутрь панели
EDGE_MARK_OFFSET = 20.0

# Длина маркера
EDGE_MARK_LENGTH = 7.0


# ============================================================
# МАРКИРОВКА НОМЕРА
# ============================================================

def make_mark_text(filename, has_back):
    """
    I_6_2.DXF + I_6_O_2.DXF -> I6
    I_6_2.DXF без оборота -> I

    Арабская часть номера остается обычным MTEXT.
    Римская часть I/V/X рисуется линиями.
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


# ============================================================
# РАЗДЕЛЕНИЕ РИМСКОЙ И АРАБСКОЙ ЧАСТИ
# ============================================================

def split_roman_prefix(text):
    """
    Возвращает:
        (римская_часть, арабская_часть)

    Примеры:

        I       -> ("I", "")
        IV      -> ("IV", "")
        I4      -> ("I", "4")
        III7    -> ("III", "7")
        12      -> ("", "12")
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


# ============================================================
# РИМСКИЕ ЦИФРЫ ЛИНИЯМИ
# ============================================================

def roman_glyphs(text, height):
    """
    Римские цифры строятся LINE.

    I = 1 линия
    V = 2 линии
    X = 2 линии

    Поэтому:

        I     = 1
        II    = 2
        III   = 3
        IV    = 3
        V     = 2
        VI    = 3
        VII   = 4
        VIII  = 5
        IX    = 3
        X     = 2
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
                (x, 0.0, x, h)
            )

            x += w_i + gap

        elif ch == "V":

            left = x
            right = x + w_v
            bottom = x + w_v / 2.0

            segments.append(
                (left, h, bottom, 0.0)
            )

            segments.append(
                (bottom, 0.0, right, h)
            )

            x += w_v + gap

        elif ch == "X":

            left = x
            right = x + w_v

            segments.append(
                (left, 0.0, right, h)
            )

            segments.append(
                (left, h, right, 0.0)
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


# ============================================================
# DXF GROUP CODE
# ============================================================

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

def _get_max_handle(lines):

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

    return max_handle


def _update_handseed(lines, handle):

    for i in range(len(lines) - 1):

        if lines[i].strip() == "$HANDSEED":

            j = i + 1

            while j < min(i + 8, len(lines) - 1):

                if lines[j].strip() == "5":

                    lines[j + 1] = handle + "\n"

                    return

                j += 1


# ============================================================
# ПОВОРОТ ТОЧКИ
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


# ============================================================
# ARABIC MTEXT
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
# ЗАМЕНА РИМСКОГО MTEXT
# ============================================================

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

    next_handle_int = _get_max_handle(lines) + 1

    def get_handle():

        nonlocal next_handle_int

        h = f"{next_handle_int:X}"

        next_handle_int += 1

        return h

    # --------------------------------------------------------
    # РИМСКАЯ ЧАСТЬ
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # АРАБСКАЯ ЧАСТЬ
    # --------------------------------------------------------

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
# ЧТЕНИЕ LINE
# ============================================================

def _read_line_entity(entity):

    x1 = None
    y1 = None
    x2 = None
    y2 = None

    layer = None

    for i in range(len(entity) - 1):

        code = entity[i].strip()
        value = entity[i + 1].strip()

        if code == "8":
            layer = value

        elif code == "10":

            try:
                x1 = float(value)
            except Exception:
                pass

        elif code == "20":

            try:
                y1 = float(value)
            except Exception:
                pass

        elif code == "11":

            try:
                x2 = float(value)
            except Exception:
                pass

        elif code == "21":

            try:
                y2 = float(value)
            except Exception:
                pass

    if (
        x1 is None
        or y1 is None
        or x2 is None
        or y2 is None
    ):
        return None

    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "layer": layer
    }


# ============================================================
# ПОЛУЧЕНИЕ ВСЕХ LINE
# ============================================================

def _get_line_entities(lines):

    result = []

    i = 0

    while i < len(lines) - 1:

        if (
            lines[i].strip() == "0"
            and lines[i + 1].strip() == "LINE"
        ):

            start = i
            i += 2

            while i < len(lines):

                if lines[i].strip() == "0":
                    break

                i += 1

            entity = lines[start:i]

            data = _read_line_entity(entity)

            if data is not None:
                result.append(data)

            continue

        i += 1

    return result


# ============================================================
# ПОЛУЧЕНИЕ ГАБАРИТА ПАНЕЛИ
# ============================================================

def _get_panel_bbox(lines):

    min_x = None
    min_y = None
    max_x = None
    max_y = None

    # --------------------------------------------------------
    # Сначала ищем LWPOLYLINE.
    # Обычно именно она является контуром панели.
    # --------------------------------------------------------

    i = 0

    while i < len(lines) - 1:

        if (
            lines[i].strip() == "0"
            and lines[i + 1].strip() == "LWPOLYLINE"
        ):

            start = i

            i += 2

            while i < len(lines):

                if lines[i].strip() == "0":
                    break

                i += 1

            entity = lines[start:i]

            xs = []
            ys = []

            j = 0

            while j < len(entity) - 1:

                code = entity[j].strip()

                if code == "10":

                    try:
                        xs.append(
                            float(
                                entity[j + 1].strip()
                            )
                        )
                    except Exception:
                        pass

                elif code == "20":

                    try:
                        ys.append(
                            float(
                                entity[j + 1].strip()
                            )
                        )
                    except Exception:
                        pass

                j += 1

            if xs and ys:

                e_min_x = min(xs)
                e_max_x = max(xs)

                e_min_y = min(ys)
                e_max_y = max(ys)

                e_width = e_max_x - e_min_x
                e_height = e_max_y - e_min_y

                # Берём самый крупный контур.
                if (
                    min_x is None
                    or e_width * e_height
                    > (max_x - min_x)
                    * (max_y - min_y)
                ):

                    min_x = e_min_x
                    max_x = e_max_x
                    min_y = e_min_y
                    max_y = e_max_y

            continue

        i += 1

    if (
        min_x is not None
        and min_y is not None
        and max_x is not None
        and max_y is not None
    ):
        return (
            min_x,
            min_y,
            max_x,
            max_y
        )

    # --------------------------------------------------------
    # Если LWPOLYLINE не нашли,
    # используем EXTMIN / EXTMAX.
    # --------------------------------------------------------

    ext_min_x = None
    ext_min_y = None
    ext_max_x = None
    ext_max_y = None

    i = 0

    while i < len(lines) - 1:

        if lines[i].strip() == "$EXTMIN":

            j = i + 1

            while j < min(i + 30, len(lines) - 1):

                if lines[j].strip() == "10":

                    try:
                        ext_min_x = float(
                            lines[j + 1].strip()
                        )
                    except Exception:
                        pass

                elif lines[j].strip() == "20":

                    try:
                        ext_min_y = float(
                            lines[j + 1].strip()
                        )
                    except Exception:
                        pass

                j += 1

        elif lines[i].strip() == "$EXTMAX":

            j = i + 1

            while j < min(i + 30, len(lines) - 1):

                if lines[j].strip() == "10":

                    try:
                        ext_max_x = float(
                            lines[j + 1].strip()
                        )
                    except Exception:
                        pass

                elif lines[j].strip() == "20":

                    try:
                        ext_max_y = float(
                            lines[j + 1].strip()
                        )
                    except Exception:
                        pass

                j += 1

        i += 1

    if (
        ext_min_x is not None
        and ext_min_y is not None
        and ext_max_x is not None
        and ext_max_y is not None
    ):

        return (
            ext_min_x,
            ext_min_y,
            ext_max_x,
            ext_max_y
        )

    return None


# ============================================================
# СОЗДАНИЕ МАРКЕРА КРОМКИ
# ============================================================

def _make_edge_markers(
    lines,
    bbox
):

    if bbox is None:
        return []

    min_x, min_y, max_x, max_y = bbox

    panel_width = max_x - min_x
    panel_height = max_y - min_y

    if panel_width <= 0 or panel_height <= 0:
        return []

    edge_lines = _get_line_entities(lines)

    markers = []

    next_handle = _get_max_handle(lines) + 1

    def get_handle():

        nonlocal next_handle

        h = f"{next_handle:X}"

        next_handle += 1

        return h

    for edge in edge_lines:

        # ----------------------------------------------------
        # ТОЛЬКО слой кромки
        # ----------------------------------------------------

        if edge["layer"] != EDGE_LAYER:
            continue

        x1 = edge["x1"]
        y1 = edge["y1"]
        x2 = edge["x2"]
        y2 = edge["y2"]

        dx = x2 - x1
        dy = y2 - y1

        length = math.sqrt(
            dx * dx + dy * dy
        )

        if length < EDGE_MARK_LENGTH:
            continue

        # ----------------------------------------------------
        # Проверяем, что линия действительно является
        # стороной панели.
        # ----------------------------------------------------

        tolerance = 1.0

        is_left = (
            abs(x1 - min_x) <= tolerance
            and abs(x2 - min_x) <= tolerance
        )

        is_right = (
            abs(x1 - max_x) <= tolerance
            and abs(x2 - max_x) <= tolerance
        )

        is_bottom = (
            abs(y1 - min_y) <= tolerance
            and abs(y2 - min_y) <= tolerance
        )

        is_top = (
            abs(y1 - max_y) <= tolerance
            and abs(y2 - max_y) <= tolerance
        )

        # ----------------------------------------------------
        # Если линия не лежит на стороне панели,
        # не ставим маркер.
        # ----------------------------------------------------

        if not (
            is_left
            or is_right
            or is_bottom
            or is_top
        ):
            continue

        # ----------------------------------------------------
        # Единичный вектор вдоль кромки.
        # ----------------------------------------------------

        ux = dx / length
        uy = dy / length

        # ----------------------------------------------------
        # Центр линии.
        # ----------------------------------------------------

        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        # ----------------------------------------------------
        # Вектор внутрь панели.
        # ----------------------------------------------------

        if is_left:

            nx = 1.0
            ny = 0.0

        elif is_right:

            nx = -1.0
            ny = 0.0

        elif is_bottom:

            nx = 0.0
            ny = 1.0

        else:

            nx = 0.0
            ny = -1.0

        # ----------------------------------------------------
        # Центр будущего маркера:
        # 20 мм внутрь панели.
        # ----------------------------------------------------

        mcx = (
            cx
            + nx * EDGE_MARK_OFFSET
        )

        mcy = (
            cy
            + ny * EDGE_MARK_OFFSET
        )

        # ----------------------------------------------------
        # Половина длины маркера.
        # ----------------------------------------------------

        half = EDGE_MARK_LENGTH / 2.0

        mx1 = (
            mcx
            - ux * half
        )

        my1 = (
            mcy
            - uy * half
        )

        mx2 = (
            mcx
            + ux * half
        )

        my2 = (
            mcy
            + uy * half
        )

        # ----------------------------------------------------
        # Создаём новый LINE.
        #
        # ВАЖНО:
        # исходная линия здесь вообще не изменяется.
        # ----------------------------------------------------

        markers.extend(
            _make_line(
                get_handle(),
                "1F",
                EDGE_LAYER,
                mx1,
                my1,
                mx2,
                my2
            )
        )

    return markers


# ============================================================
# ДОБАВЛЕНИЕ МАРКЕРОВ ПЕРЕД ENDSEC
# ============================================================

def _insert_edge_markers(
    lines,
    markers
):

    if not markers:
        return lines

    # --------------------------------------------------------
    # Ищем ENDSEC именно секции ENTITIES.
    # --------------------------------------------------------

    entities_start = None
    entities_end = None

    i = 0

    while i < len(lines) - 1:

        if (
            lines[i].strip() == "2"
            and lines[i + 1].strip() == "ENTITIES"
        ):

            entities_start = i + 2

            j = entities_start

            while j < len(lines):

                if lines[j].strip() == "ENDSEC":

                    entities_end = j
                    break

                j += 1

            break

        i += 1

    if entities_end is None:
        return lines

    return (
        lines[:entities_end]
        + markers
        + lines[entities_end:]
    )


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

def modify_dxf_text(filepath, new_text):

    with open(
        filepath,
        "r",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        lines = f.readlines()

    # ========================================================
    # 1. Габариты панели
    # ========================================================

    bbox = _get_panel_bbox(lines)

    # ========================================================
    # 2. Римская / арабская маркировка
    # ========================================================

    start, end, entity_lines = _find_mtext(lines)

    if entity_lines is None:

        raise Exception(
            "Не найден MTEXT для замены"
        )

    # --------------------------------------------------------
    # Римская часть
    # --------------------------------------------------------

    if roman_is_vector(new_text):

        replacement = _replace_roman_mtext(
            lines,
            start,
            end,
            entity_lines,
            new_text,
            0.0
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

    # --------------------------------------------------------
    # Арабская часть
    # --------------------------------------------------------

    else:

        inside = False

        result = []

        # После замены римского MTEXT
        # обработка арабского также сохраняется.
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

                result.append("50\n")

                result.append("0\n")

                inside = False

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
    # 3. МАРКЕРЫ КРОМКИ
    # ========================================================
    #
    # ВАЖНО:
    #
    # Исходные линии слоя ED_Кром. в цвет
    # НЕ УДАЛЯЮТСЯ.
    #
    # Мы только добавляем новые LINE.
    #

    markers = _make_edge_markers(
        lines,
        bbox
    )

    lines = _insert_edge_markers(
        lines,
        markers
    )

    # ========================================================
    # 4. HANDSEED
    # ========================================================

    max_handle = _get_max_handle(lines)

    _update_handseed(
        lines,
        f"{max_handle + 1:X}"
    )

    # ========================================================
    # 5. Записываем DXF
    # ========================================================

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        f.writelines(lines)

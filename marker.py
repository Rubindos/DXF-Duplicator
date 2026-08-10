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


# ============================================================
# ФОРМИРОВАНИЕ ТЕКСТА МАРКИРОВКИ
# ============================================================

def make_mark_text(filename, has_back):
    """
    I_6_2.DXF + I_6_O_2.DXF -> I6
    I_6_2.DXF без оборота -> I

    Арабская часть номера остается обычным MTEXT.
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


# ============================================================
# РАЗДЕЛЕНИЕ РИМСКОЙ И АРАБСКОЙ ЧАСТИ
# ============================================================

def split_roman_prefix(text):
    """
    Возвращает:

        (римская_часть, арабская_часть)

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

    return bool(roman) and all(
        ch in "IVX"
        for ch in roman
    )


# ============================================================
# РИМСКИЕ ЦИФРЫ
# ============================================================

def roman_glyphs(text, height):
    """
    Римская цифра состоит только из LINE.

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


# ============================================================
# DXF GROUP VALUE
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

            while j < min(
                i + 8,
                len(lines) - 1
            ):

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
# ПОИСК ЛИНИЙ КРОМКИ
# ============================================================

def _find_edge_lines(lines):

    edge_lines = []

    i = 0

    while i < len(lines):

        if lines[i].strip() == "0":

            if (
                i + 1 < len(lines)
                and lines[i + 1].strip() == "LINE"
            ):

                start = i

                end = i + 2

                while end < len(lines):

                    if lines[end].strip() == "0":
                        break

                    end += 1

                entity = lines[start:end]

                layer = _get_group_value(
                    entity,
                    8,
                    ""
                )

                if layer == EDGE_LAYER:

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

                        edge_lines.append(
                            (
                                x1,
                                y1,
                                x2,
                                y2
                            )
                        )

                    except Exception:
                        pass

                i = end

                continue

        i += 1

    return edge_lines


# ============================================================
# ЦЕНТР ДЕТАЛИ
# ============================================================

def _get_panel_center(lines):

    min_x = None
    min_y = None
    max_x = None
    max_y = None

    # --------------------------------------------------------
    # Сначала пробуем LWPOLYLINE
    # --------------------------------------------------------

    i = 0

    while i < len(lines):

        if (
            lines[i].strip() == "0"
            and i + 1 < len(lines)
            and lines[i + 1].strip() == "LWPOLYLINE"
        ):

            end = i + 2

            vertices = []

            current_x = None
            current_y = None

            while end < len(lines):

                if lines[end].strip() == "0":
                    break

                code = lines[end].strip()

                if code == "10":

                    try:
                        current_x = float(
                            lines[end + 1].strip()
                        )
                    except Exception:
                        current_x = None

                elif code == "20":

                    try:
                        current_y = float(
                            lines[end + 1].strip()
                        )
                    except Exception:
                        current_y = None

                    if (
                        current_x is not None
                        and current_y is not None
                    ):

                        vertices.append(
                            (
                                current_x,
                                current_y
                            )
                        )

                        current_x = None
                        current_y = None

                end += 1

            for x, y in vertices:

                if min_x is None or x < min_x:
                    min_x = x

                if max_x is None or x > max_x:
                    max_x = x

                if min_y is None or y < min_y:
                    min_y = y

                if max_y is None or y > max_y:
                    max_y = y

            i = end

            continue

        i += 1

    # --------------------------------------------------------
    # Если полилиния не найдена — EXTMIN / EXTMAX
    # --------------------------------------------------------

    if (
        min_x is None
        or min_y is None
        or max_x is None
        or max_y is None
    ):

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

    if (
        min_x is None
        or min_y is None
        or max_x is None
        or max_y is None
    ):

        return 0.0, 0.0

    return (
        (min_x + max_x) / 2.0,
        (min_y + max_y) / 2.0
    )


# ============================================================
# ДОБАВЛЕНИЕ МАРКЕРОВ КРОМКИ
# ============================================================

def _add_edge_markers(lines):

    edge_lines = _find_edge_lines(lines)

    if not edge_lines:
        return lines

    center_x, center_y = _get_panel_center(
        lines
    )

    next_handle = _get_max_handle(lines) + 1

    new_entities = []

    for x1, y1, x2, y2 in edge_lines:

        dx = x2 - x1
        dy = y2 - y1

        length = math.sqrt(
            dx * dx + dy * dy
        )

        if length < 0.001:
            continue

        # ----------------------------------------------------
        # Единичный вектор вдоль кромки
        # ----------------------------------------------------

        tx = dx / length
        ty = dy / length

        # ----------------------------------------------------
        # Два возможных нормальных направления
        # ----------------------------------------------------

        nx1 = -ty
        ny1 = tx

        nx2 = ty
        ny2 = -tx

        # ----------------------------------------------------
        # Середина существующей линии кромки
        # ----------------------------------------------------

        mx = (x1 + x2) / 2.0
        my = (y1 + y2) / 2.0

        # ----------------------------------------------------
        # Определяем, какая сторона направлена ВНУТРЬ панели.
        #
        # Смотрим, какой из двух нормальных векторов
        # направлен к центру детали.
        # ----------------------------------------------------

        to_center_x = center_x - mx
        to_center_y = center_y - my

        dot1 = (
            nx1 * to_center_x
            +
            ny1 * to_center_y
        )

        dot2 = (
            nx2 * to_center_x
            +
            ny2 * to_center_y
        )

        if dot1 >= dot2:

            nx = nx1
            ny = ny1

        else:

            nx = nx2
            ny = ny2

        # ----------------------------------------------------
        # Точка маркера:
        #
        # 20 мм ВНУТРЬ от линии кромки.
        # ----------------------------------------------------

        marker_center_x = (
            mx
            +
            nx * EDGE_MARK_OFFSET
        )

        marker_center_y = (
            my
            +
            ny * EDGE_MARK_OFFSET
        )

        # ----------------------------------------------------
        # Половина длины маркера
        # ----------------------------------------------------

        half = EDGE_MARK_LENGTH / 2.0

        marker_x1 = (
            marker_center_x
            -
            tx * half
        )

        marker_y1 = (
            marker_center_y
            -
            ty * half
        )

        marker_x2 = (
            marker_center_x
            +
            tx * half
        )

        marker_y2 = (
            marker_center_y
            +
            ty * half
        )

        # ----------------------------------------------------
        # Создаём новый LINE.
        #
        # ВАЖНО:
        # исходная линия кромки НЕ ТРОГАЕТСЯ.
        # ----------------------------------------------------

        new_entities.extend(
            _make_line(
                f"{next_handle:X}",
                "1F",
                EDGE_LAYER,
                marker_x1,
                marker_y1,
                marker_x2,
                marker_y2
            )
        )

        next_handle += 1

    if not new_entities:
        return lines

    # --------------------------------------------------------
    # Вставляем новые LINE перед ENDSEC в ENTITIES.
    # --------------------------------------------------------

    insert_index = None

    in_entities = False

    i = 0

    while i < len(lines) - 1:

        if (
            lines[i].strip() == "0"
            and lines[i + 1].strip() == "SECTION"
        ):

            # Проверяем следующий 2-код

            j = i + 2

            if (
                j < len(lines)
                and lines[j].strip() == "2"
            ):

                if (
                    j + 1 < len(lines)
                    and lines[j + 1].strip() == "ENTITIES"
                ):

                    in_entities = True

                    i = j + 2

                    continue

        if in_entities:

            if (
                lines[i].strip() == "0"
                and i + 1 < len(lines)
                and lines[i + 1].strip() == "ENDSEC"
            ):

                insert_index = i

                break

        i += 1

    if insert_index is None:

        return lines

    lines = (
        lines[:insert_index]
        +
        new_entities
        +
        lines[insert_index:]
    )

    # --------------------------------------------------------
    # Обновляем HANDSEED
    # --------------------------------------------------------

    _update_handseed(
        lines,
        f"{next_handle:X}"
    )

    return lines


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
    # Определяем габариты детали
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

    # ========================================================
    # Определяем поворот текста
    # ========================================================

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
    # Ищем MTEXT
    # ========================================================

    start, end, entity_lines = _find_mtext(
        lines
    )

    if entity_lines is None:

        raise Exception(
            "Не найден MTEXT для замены"
        )

    # ========================================================
    # РИМСКАЯ ЧАСТЬ
    # ========================================================

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

    # ========================================================
    # АРАБСКАЯ ЧАСТЬ
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
    # НОВОЕ:
    #
    # ДОБАВЛЯЕМ МАРКЕРЫ КРОМКИ
    #
    # Исходные линии слоя ED_Кром. в цвет
    # НЕ УДАЛЯЮТСЯ.
    # ========================================================

    lines = _add_edge_markers(
        lines
    )

    # ========================================================
    # Сохраняем DXF
    # ========================================================

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        f.writelines(lines)

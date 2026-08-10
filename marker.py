import os
import math


TEXT_HEIGHT = 25.0
ROMAN_GAP = 6.0

# ============================================================
# НАСТРОЙКИ ОТМЕТКИ КРОМКИ
# ============================================================

EDGE_LAYER = "ED_Кром. в цвет"

# Слой контура панели в DXF Базиса
PANEL_LAYER = "FK_16"

# Насколько отступаем внутрь панели от закромленной стороны
EDGE_MARK_OFFSET = 20.0

# Длина отметки
EDGE_MARK_LENGTH = 7.0

# Допуск при сравнении координат
EDGE_TOLERANCE = 0.5


# ============================================================
# РИМСКИЕ ЦИФРЫ
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


def split_roman_prefix(text):
    """
    Возвращает (римская_часть, арабская_часть).

    Поддерживаются римские символы I, V, X.

    Например:
        I    -> ("I", "")
        IV   -> ("IV", "")
        I4   -> ("I", "4")
        III7 -> ("III", "7")
        12   -> ("", "12")
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
    Возвращает набор отрезков римской надписи.

    Правило:

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

    Координаты локальные:

      X вправо
      Y вверх
    """
    h = float(height)

    w_i = h * 0.22
    w_v = h * 0.48
    gap = h * 0.22

    segments = []
    x = 0.0

    for ch in text:

        if ch == "I":

            # Одна вертикальная линия
            segments.append(
                (x, 0.0, x, h)
            )

            x += w_i + gap

        elif ch == "V":

            # Две диагональные линии
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

            # Две диагональные линии
            left = x
            right = x + w_v

            segments.append(
                (left, 0.0, right, h)
            )

            segments.append(
                (left, h, right, 0.0)
            )

            x += w_v + gap

    # Убираем последний промежуток
    if segments:
        total_width = x - gap
    else:
        total_width = 0.0

    return segments, total_width


# ============================================================
# РАБОТА С MTEXT
# ============================================================

def _find_mtext(lines):
    """
    Находит первое MTEXT и возвращает:

        start_index,
        end_index,
        entity_lines

    end_index указывает на строку перед следующим
    entity marker "0".
    """

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


def _rotate_point(x, y, angle_deg):

    a = math.radians(angle_deg)

    ca = math.cos(a)
    sa = math.sin(a)

    return (
        x * ca - y * sa,
        x * sa + y * ca
    )


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


def _prepare_arabic_mtext(
    entity_lines,
    arabic_text,
    x,
    y,
    angle,
    height
):
    """
    Берем исходный MTEXT Базиса и оставляем
    в нем только арабскую часть.

    Это сохраняет стиль/слой и сам принцип
    вывода арабского номера.
    """

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

    # Если это не римская часть —
    # ничего не ломаем.
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

    # Римская надпись строится линиями.
    segments, roman_width = roman_glyphs(
        roman,
        height
    )

    new_entities = []

    # ========================================================
    # Получаем следующий свободный HANDLE
    # ========================================================

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

    # ========================================================
    # Создаем линии римской цифры
    # ========================================================

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
                insert_y + ry2,
            )
        )

    # ========================================================
    # Если после римской части есть арабский номер
    # ========================================================

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
            height,
        )

        # У арабского MTEXT тоже должен быть
        # новый handle.

        _set_group_value(
            arabic_entity,
            5,
            get_handle()
        )

        new_entities.extend(
            arabic_entity
        )

    # Обновляем HANDSEED.

    _update_handseed(
        lines,
        f"{next_handle_int:X}"
    )

    return new_entities


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КРОМКИ
# ============================================================

def _safe_float(value):

    try:
        return float(value)

    except Exception:
        return None


def _get_entity_layer(entity_lines):

    return _get_group_value(
        entity_lines,
        8,
        ""
    ).strip()


def _get_entity_owner(entity_lines):

    return _get_group_value(
        entity_lines,
        330,
        "1F"
    ).strip()


def _find_entities(lines):
    """
    Разбирает ENTITIES на отдельные DXF-сущности.

    Возвращает список:

        [
            {
                "start": ...,
                "end": ...,
                "lines": [...]
            },
            ...
        ]
    """

    entities = []

    i = 0

    while i < len(lines) - 1:

        if (
            lines[i].strip() == "0"
            and i + 1 < len(lines)
        ):

            entity_type = lines[i + 1].strip()

            # Только реальные графические сущности.
            if entity_type in (
                "LINE",
                "LWPOLYLINE",
                "POLYLINE",
                "CIRCLE",
                "ARC",
                "MTEXT",
                "TEXT"
            ):

                start = i

                j = i + 2

                while j < len(lines):

                    if (
                        lines[j].strip() == "0"
                        and j + 1 < len(lines)
                    ):
                        break

                    j += 1

                entities.append(
                    {
                        "start": start,
                        "end": j,
                        "lines": lines[start:j],
                    }
                )

                i = j
                continue

        i += 1

    return entities


def _get_lwpolyline_points(entity_lines):

    points = []

    current_x = None
    current_y = None

    i = 0

    while i < len(entity_lines) - 1:

        code = entity_lines[i].strip()

        value = entity_lines[i + 1].strip()

        if code == "10":

            current_x = _safe_float(value)

        elif code == "20":

            current_y = _safe_float(value)

            if (
                current_x is not None
                and current_y is not None
            ):

                points.append(
                    (
                        current_x,
                        current_y
                    )
                )

                current_x = None
                current_y = None

        i += 1

    return points


def _get_line_points(entity_lines):

    x1 = None
    y1 = None
    x2 = None
    y2 = None

    i = 0

    while i < len(entity_lines) - 1:

        code = entity_lines[i].strip()
        value = entity_lines[i + 1].strip()

        if code == "10":
            x1 = _safe_float(value)

        elif code == "20":
            y1 = _safe_float(value)

        elif code == "11":
            x2 = _safe_float(value)

        elif code == "21":
            y2 = _safe_float(value)

        i += 1

    if (
        x1 is None
        or y1 is None
        or x2 is None
        or y2 is None
    ):
        return None

    return (
        x1,
        y1,
        x2,
        y2
    )


def _distance_point_to_segment(
    px,
    py,
    x1,
    y1,
    x2,
    y2
):

    dx = x2 - x1
    dy = y2 - y1

    length_sq = dx * dx + dy * dy

    if length_sq == 0:

        return math.hypot(
            px - x1,
            py - y1
        )

    t = (
        (px - x1) * dx
        + (py - y1) * dy
    ) / length_sq

    t = max(
        0.0,
        min(1.0, t)
    )

    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    return math.hypot(
        px - closest_x,
        py - closest_y
    )


def _segments_collinear(
    a1,
    a2,
    b1,
    b2,
    tolerance=EDGE_TOLERANCE
):
    """
    Проверяет, находятся ли два отрезка
    примерно на одной прямой.

    Это позволяет определить, что объект
    на слое кромки совпадает со стороной панели.
    """

    ax1, ay1 = a1
    ax2, ay2 = a2

    bx1, by1 = b1
    bx2, by2 = b2

    distance1 = _distance_point_to_segment(
        ax1,
        ay1,
        bx1,
        by1,
        bx2,
        by2
    )

    distance2 = _distance_point_to_segment(
        ax2,
        ay2,
        bx1,
        by1,
        bx2,
        by2
    )

    distance3 = _distance_point_to_segment(
        bx1,
        by1,
        ax1,
        ay1,
        ax2,
        ay2
    )

    distance4 = _distance_point_to_segment(
        bx2,
        by2,
        ax1,
        ay1,
        ax2,
        ay2
    )

    return (
        distance1 <= tolerance
        and distance2 <= tolerance
    ) or (
        distance3 <= tolerance
        and distance4 <= tolerance
    )


def _get_panel_sides(points):

    if len(points) < 4:
        return []

    # Убираем повторяющиеся соседние точки.

    clean = []

    for point in points:

        if not clean:

            clean.append(point)
            continue

        if (
            abs(point[0] - clean[-1][0])
            > EDGE_TOLERANCE
            or
            abs(point[1] - clean[-1][1])
            > EDGE_TOLERANCE
        ):

            clean.append(point)

    # Если последняя точка совпадает
    # с первой — убираем её.

    if len(clean) >= 2:

        if (
            abs(clean[0][0] - clean[-1][0])
            <= EDGE_TOLERANCE
            and
            abs(clean[0][1] - clean[-1][1])
            <= EDGE_TOLERANCE
        ):

            clean.pop()

    if len(clean) < 4:
        return []

    sides = []

    for i in range(len(clean)):

        p1 = clean[i]
        p2 = clean[
            (i + 1) % len(clean)
        ]

        # Нас интересуют стороны
        # прямоугольной панели.

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        if (
            abs(dx) <= EDGE_TOLERANCE
            or
            abs(dy) <= EDGE_TOLERANCE
        ):

            sides.append(
                (
                    p1,
                    p2
                )
            )

    return sides


def _get_edge_segments(entity_lines):

    entity_type = ""

    if len(entity_lines) >= 2:

        if entity_lines[0].strip() == "0":

            entity_type = entity_lines[1].strip()

    segments = []

    if entity_type == "LINE":

        points = _get_line_points(
            entity_lines
        )

        if points is not None:

            x1, y1, x2, y2 = points

            segments.append(
                (
                    (x1, y1),
                    (x2, y2)
                )
            )

    elif entity_type == "LWPOLYLINE":

        points = _get_lwpolyline_points(
            entity_lines
        )

        if len(points) >= 2:

            for i in range(len(points) - 1):

                segments.append(
                    (
                        points[i],
                        points[i + 1]
                    )
                )

            # Замыкаем полилинию,
            # только если она действительно
            # закрыта.

            flags = _get_group_value(
                entity_lines,
                70,
                "0"
            )

            try:
                flags = int(flags)

            except Exception:
                flags = 0

            if flags & 1:

                segments.append(
                    (
                        points[-1],
                        points[0]
                    )
                )

    return segments


def _find_panel_contour(lines):

    entities = _find_entities(lines)

    candidates = []

    for entity in entities:

        entity_lines = entity["lines"]

        layer = _get_entity_layer(
            entity_lines
        )

        if layer.upper() != PANEL_LAYER.upper():
            continue

        entity_type = ""

        if len(entity_lines) >= 2:

            entity_type = entity_lines[1].strip()

        if entity_type == "LWPOLYLINE":

            points = _get_lwpolyline_points(
                entity_lines
            )

            sides = _get_panel_sides(
                points
            )

            if len(sides) >= 4:

                candidates.append(
                    (
                        entity,
                        sides
                    )
                )

    if not candidates:
        return None, None, None

    # Берем самый большой прямоугольный контур.

    best_entity = None
    best_sides = None
    best_area = 0.0

    for entity, sides in candidates:

        xs = []
        ys = []

        for p1, p2 in sides:

            xs.append(p1[0])
            xs.append(p2[0])

            ys.append(p1[1])
            ys.append(p2[1])

        if not xs or not ys:
            continue

        width = max(xs) - min(xs)
        height = max(ys) - min(ys)

        area = abs(
            width * height
        )

        if area > best_area:

            best_area = area

            best_entity = entity

            best_sides = sides

    if best_entity is None:

        return None, None, None

    owner = _get_entity_owner(
        best_entity["lines"]
    )

    return (
        best_entity,
        best_sides,
        owner
    )


def _side_length(side):

    p1, p2 = side

    return math.hypot(
        p2[0] - p1[0],
        p2[1] - p1[1]
    )


def _side_midpoint(side):

    p1, p2 = side

    return (
        (p1[0] + p2[0]) / 2.0,
        (p1[1] + p2[1]) / 2.0
    )


def _side_direction(side):

    p1, p2 = side

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    length = math.hypot(
        dx,
        dy
    )

    if length == 0:

        return (
            0.0,
            0.0
        )

    return (
        dx / length,
        dy / length
    )


def _panel_center(sides):

    xs = []
    ys = []

    for p1, p2 in sides:

        xs.extend(
            [
                p1[0],
                p2[0]
            ]
        )

        ys.extend(
            [
                p1[1],
                p2[1]
            ]
        )

    if not xs or not ys:

        return (
            0.0,
            0.0
        )

    return (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0
    )


def _move_point_inside_panel(
    x,
    y,
    side,
    sides,
    distance
):
    """
    Берем точку на стороне и переносим её
    на distance мм внутрь панели.

    Направление определяется автоматически
    относительно центра панели.
    """

    center_x, center_y = _panel_center(
        sides
    )

    p1, p2 = side

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    length = math.hypot(
        dx,
        dy
    )

    if length == 0:

        return x, y

    # Два нормальных направления.

    nx1 = -dy / length
    ny1 = dx / length

    nx2 = dy / length
    ny2 = -dx / length

    # Выбираем нормаль, направленную
    # к центру панели.

    test1_x = x + nx1 * distance
    test1_y = y + ny1 * distance

    test2_x = x + nx2 * distance
    test2_y = y + ny2 * distance

    d1 = math.hypot(
        test1_x - center_x,
        test1_y - center_y
    )

    d2 = math.hypot(
        test2_x - center_x,
        test2_y - center_y
    )

    if d1 < d2:

        return (
            test1_x,
            test1_y
        )

    return (
        test2_x,
        test2_y
    )


def _edge_side_matches(
    panel_side,
    edge_segment
):
    """
    Проверяет, относится ли сегмент кромки
    к стороне панели.
    """

    p1, p2 = panel_side
    e1, e2 = edge_segment

    if _segments_collinear(
        p1,
        p2,
        e1,
        e2,
        EDGE_TOLERANCE
    ):
        return True

    return False


def _make_edge_mark(
    handle,
    owner,
    side,
    sides
):
    """
    Создает отметку 7 мм.

    Отметка:

      - параллельна стороне;
      - находится на 20 мм внутри панели;
      - расположена примерно по центру стороны.
    """

    p1, p2 = side

    side_length = _side_length(
        side
    )

    if side_length < EDGE_MARK_LENGTH:
        return []

    dx, dy = _side_direction(
        side
    )

    # Центр стороны.

    cx, cy = _side_midpoint(
        side
    )

    # Сначала уходим внутрь панели на 20 мм.

    cx, cy = _move_point_inside_panel(
        cx,
        cy,
        side,
        sides,
        EDGE_MARK_OFFSET
    )

    half = EDGE_MARK_LENGTH / 2.0

    x1 = cx - dx * half
    y1 = cy - dy * half

    x2 = cx + dx * half
    y2 = cy + dy * half

    return _make_line(
        handle,
        owner,
        EDGE_LAYER,
        x1,
        y1,
        x2,
        y2
    )


# ============================================================
# ДОБАВЛЕНИЕ ОТМЕТОК КРОМКИ
# ============================================================

def add_edge_mark(filepath):
    """
    Находит кромку панели и ставит отметку 7 мм.

    Логика:

      1. Находим контур панели на слое FK_16.
      2. Определяем его стороны.
      3. Ищем объекты на слое
         ED_Кром. в цвет.
      4. Определяем, какие стороны закромлены.
      5. На каждой закромленной стороне
         ставим отрезок 7 мм.
      6. Отрезок отстоит от края панели
         на 20 мм внутрь.

    Если кромки нет — файл остается без изменений.

    Если кромка есть с нескольких сторон —
    отметка ставится на каждой такой стороне.
    """

    with open(
        filepath,
        "r",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        lines = f.readlines()

    # ========================================================
    # Ищем контур панели
    # ========================================================

    panel_entity, panel_sides, owner = (
        _find_panel_contour(lines)
    )

    if not panel_sides:

        # Не нашли контур панели.
        # Ничего не меняем.

        return False

    # ========================================================
    # Получаем все сущности
    # ========================================================

    entities = _find_entities(
        lines
    )

    edge_segments = []

    for entity in entities:

        entity_lines = entity["lines"]

        layer = _get_entity_layer(
            entity_lines
        )

        if layer.upper() != EDGE_LAYER.upper():
            continue

        segments = _get_edge_segments(
            entity_lines
        )

        for segment in segments:

            edge_segments.append(
                segment
            )

    if not edge_segments:

        # Кромка отсутствует.

        return False

    # ========================================================
    # Определяем закромленные стороны
    # ========================================================

    marked_sides = []

    for side in panel_sides:

        side_is_edge = False

        for edge_segment in edge_segments:

            if _edge_side_matches(
                side,
                edge_segment
            ):

                side_is_edge = True
                break

        if side_is_edge:

            # Проверяем, чтобы одна и та же
            # сторона не попала повторно.

            already_added = False

            for existing in marked_sides:

                if (
                    _edge_side_matches(
                        side,
                        existing
                    )
                ):

                    already_added = True
                    break

            if not already_added:

                marked_sides.append(
                    side
                )

    if not marked_sides:

        # Не нашли совпадение между
        # слоем кромки и сторонами панели.

        return False

    # ========================================================
    # Получаем свободные HANDLE
    # ========================================================

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

    next_handle_int = max_handle + 1

    new_entities = []

    # ========================================================
    # Создаем отметки
    # ========================================================

    for side in marked_sides:

        handle = f"{next_handle_int:X}"

        next_handle_int += 1

        entity = _make_edge_mark(
            handle,
            owner,
            side,
            panel_sides
        )

        if entity:

            new_entities.extend(
                entity
            )

    if not new_entities:

        return False

    # ========================================================
    # Вставляем новые LINE перед ENDSEC
    # секции ENTITIES.
    # ========================================================

    entities_start = None
    entities_end = None

    for i in range(len(lines) - 1):

        if (
            lines[i].strip() == "2"
            and lines[i + 1].strip() == "ENTITIES"
        ):

            # Ищем ближайший ENDSEC после ENTITIES.

            entities_start = i + 2

            j = entities_start

            while j < len(lines) - 1:

                if (
                    lines[j].strip() == "0"
                    and lines[j + 1].strip() == "ENDSEC"
                ):

                    entities_end = j
                    break

                j += 1

            break

    if entities_end is None:

        raise Exception(
            "Не найдена секция ENTITIES"
        )

    lines = (
        lines[:entities_end]
        + new_entities
        + lines[entities_end:]
    )

    # ========================================================
    # Обновляем HANDSEED
    # ========================================================

    _update_handseed(
        lines,
        f"{next_handle_int:X}"
    )

    # ========================================================
    # Записываем DXF
    # ========================================================

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        f.writelines(
            lines
        )

    return True


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ ОБРАБОТКИ РИМСКИХ / АРАБСКИХ ЦИФР
# ============================================================

def modify_dxf_text(filepath, new_text):
    """
    Обрабатывает DXF Базиса.

    Арабские номера:

        остаются MTEXT,
        как их выдает Базис.

    Римские номера:

        I, II, III, IV, V,
        VI, VII, VIII, IX, X

        превращаются в LINE-геометрию.

    Благодаря этому шрифт txt.shx вообще
    не участвует в построении римской части
    и не может добавить верхнюю/нижнюю черточку.
    """

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
    # Только римская часть -> линии
    # ========================================================

    if roman_is_vector(new_text):

        replacement = _replace_roman_mtext(
            lines,
            start,
            end,
            entity_lines,
            new_text,
            angle,
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

    else:

        # ====================================================
        # Арабский номер -> старое поведение
        # ====================================================

        inside = False
        result = []

        for i, line in enumerate(lines):

            s = line.strip()

            if (
                s == "0"
                and i + 1 < len(lines)
                and lines[i + 1].strip()
                == "MTEXT"
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
    # Записываем DXF
    # ========================================================

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        f.writelines(
            lines
        )

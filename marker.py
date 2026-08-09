import os
import math


TEXT_HEIGHT = 25.0
ROMAN_GAP = 6.0


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
    return bool(roman) and all(ch in "IVX" for ch in roman)


def roman_glyphs(text, height):
    """
    Возвращает набор отрезков римской надписи.

    Правило:
      I = 1 линия
      V = 2 линии
      X = 2 линии

    Поэтому:
      I   = 1
      II  = 2
      III = 3
      IV  = 3
      V   = 2
      VI  = 3
      VII = 4
      VIII= 5
      IX  = 3
      X   = 2

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
            segments.append((x, 0.0, x, h))
            x += w_i + gap

        elif ch == "V":
            # Две диагональные линии
            left = x
            right = x + w_v
            bottom = x + w_v / 2.0

            segments.append((left, h, bottom, 0.0))
            segments.append((bottom, 0.0, right, h))

            x += w_v + gap

        elif ch == "X":
            # Две диагональные линии
            left = x
            right = x + w_v

            segments.append((left, 0.0, right, h))
            segments.append((left, h, right, 0.0))

            x += w_v + gap

    # Убираем последний промежуток
    if segments:
        total_width = x - gap
    else:
        total_width = 0.0

    return segments, total_width


def _find_mtext(lines):
    """
    Находит первое MTEXT и возвращает:
        start_index, end_index, entity_lines

    end_index указывает на строку перед следующим entity marker "0".
    """
    start = None

    for i in range(len(lines) - 1):
        if lines[i].strip() == "0" and lines[i + 1].strip() == "MTEXT":
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
        if lines[i].strip() in ("5", "105", "320", "330"):
            value = lines[i + 1].strip()
            try:
                max_handle = max(max_handle, int(value, 16))
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
    return x * ca - y * sa, x * sa + y * ca


def _make_line(handle, owner, layer, x1, y1, x2, y2):
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


def _prepare_arabic_mtext(entity_lines, arabic_text, x, y, angle, height):
    """
    Берем исходный MTEXT Базиса и оставляем в нем только арабскую часть.
    Это сохраняет стиль/слой и сам принцип вывода арабского номера.
    """
    result = list(entity_lines)

    _set_group_value(result, 10, f"{x:.6f}")
    _set_group_value(result, 20, f"{y:.6f}")
    _set_group_value(result, 40, f"{height:g}")
    _set_group_value(result, 50, f"{angle:g}")
    _set_group_value(result, 1, arabic_text)

    return result


def _replace_roman_mtext(lines, start, end, entity_lines, new_text, angle):
    roman, arabic = split_roman_prefix(new_text)

    # Если это не римская часть — ничего не ломаем.
    if not roman:
        return None

    height = float(_get_group_value(entity_lines, 40, TEXT_HEIGHT))
    insert_x = float(_get_group_value(entity_lines, 10, 0.0))
    insert_y = float(_get_group_value(entity_lines, 20, 0.0))

    layer = _get_group_value(entity_lines, 8, "0")
    owner = _get_group_value(entity_lines, 330, "1F")

    # Римская надпись строится линиями.
    segments, roman_width = roman_glyphs(roman, height)

    new_entities = []
    handle_counter = None

    # Первая новая линия получает следующий свободный handle.
    temp_lines = list(lines)
    next_handle_int = 0

    for i in range(len(temp_lines) - 1):
        if temp_lines[i].strip() in ("5", "105", "320", "330"):
            value = temp_lines[i + 1].strip()
            try:
                next_handle_int = max(next_handle_int, int(value, 16))
            except Exception:
                pass

    next_handle_int += 1

    def get_handle():
        nonlocal next_handle_int
        h = f"{next_handle_int:X}"
        next_handle_int += 1
        return h

    for x1, y1, x2, y2 in segments:
        rx1, ry1 = _rotate_point(x1, y1, angle)
        rx2, ry2 = _rotate_point(x2, y2, angle)

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

    # Если после римской части есть арабский номер (например I4),
    # оставляем его обычным MTEXT.
    if arabic:
        gap = height * 0.25
        shift_x = roman_width + gap

        rx, ry = _rotate_point(shift_x, 0.0, angle)

        arabic_entity = _prepare_arabic_mtext(
            entity_lines,
            arabic,
            insert_x + rx,
            insert_y + ry,
            angle,
            height,
        )

        # У арабского MTEXT тоже должен быть новый handle.
        _set_group_value(arabic_entity, 5, get_handle())
        new_entities.extend(arabic_entity)

    # Обновляем HANDSEED.
    _update_handseed(lines, f"{next_handle_int:X}")

    return new_entities


def modify_dxf_text(filepath, new_text):
    """
    Обрабатывает DXF Базиса.

    Арабские номера:
        остаются MTEXT, как их выдает Базис.

    Римские номера:
        I, II, III, IV, V, VI, VII, VIII, IX, X
        превращаются в LINE-геометрию.

    Благодаря этому шрифт txt.shx вообще не участвует
    в построении римской части и не может добавить
    верхнюю/нижнюю черточку.
    """
    with open(
        filepath,
        "r",
        encoding="cp1251",
        errors="ignore"
    ) as f:
        lines = f.readlines()

    # ---------- определяем габариты детали ----------
    min_x = None
    min_y = None
    max_x = None
    max_y = None

    for i in range(len(lines) - 1):
        code = lines[i].strip()

        if code == "$EXTMIN":
            j = i + 1
            while j < min(i + 30, len(lines) - 1):
                if lines[j].strip() == "10":
                    try:
                        min_x = float(lines[j + 1].strip())
                    except Exception:
                        pass
                elif lines[j].strip() == "20":
                    try:
                        min_y = float(lines[j + 1].strip())
                    except Exception:
                        pass
                j += 1

        elif code == "$EXTMAX":
            j = i + 1
            while j < min(i + 30, len(lines) - 1):
                if lines[j].strip() == "10":
                    try:
                        max_x = float(lines[j + 1].strip())
                    except Exception:
                        pass
                elif lines[j].strip() == "20":
                    try:
                        max_y = float(lines[j + 1].strip())
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

    # ---------- ищем MTEXT ----------
    start, end, entity_lines = _find_mtext(lines)

    if entity_lines is None:
        raise Exception("Не найден MTEXT для замены")

    # ---------- только римская часть -> линии ----------
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
            raise Exception("Не удалось построить римскую надпись")

        lines = lines[:start] + replacement + lines[end:]

    else:
        # ---------- арабский номер -> старое поведение ----------
        # Меняем только существующий MTEXT.
        inside = False
        result = []

        for i, line in enumerate(lines):
            s = line.strip()

            if s == "0" and i + 1 < len(lines) and lines[i + 1].strip() == "MTEXT":
                inside = True
                result.append(line)
                continue

            if inside and s == "40":
                result.append(line)
                result.append(f"{TEXT_HEIGHT:g}\n")
                continue

            if inside and s == "41":
                result.append(line)

                if i + 1 < len(lines):
                    result.append(lines[i + 1])

                result.append("50\n")
                result.append(f"{angle:g}\n")
                continue

            if inside and s == "1":
                result.append(line)
                result.append(new_text + "\n")
                inside = False
                continue

            result.append(line)

        lines = result

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:
        f.writelines(lines)

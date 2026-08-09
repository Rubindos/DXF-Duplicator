import os


TEXT_HEIGHT = 25.0


def make_mark_text(filename, has_back):
    """
    Формирует текст маркировки.

    Пример:
    I_6_2.DXF + оборотная сторона -> I6
    I_6_2.DXF без оборотной       -> I
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


def find_extents(lines):
    """
    Получает габариты детали из $EXTMIN / $EXTMAX.
    """

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
                    except:
                        pass

                if lines[j].strip() == "20":
                    try:
                        min_y = float(lines[j + 1].strip())
                    except:
                        pass

                if min_x is not None and min_y is not None:
                    break

                j += 1

        elif code == "$EXTMAX":

            j = i + 1

            while j < min(i + 30, len(lines) - 1):

                if lines[j].strip() == "10":
                    try:
                        max_x = float(lines[j + 1].strip())
                    except:
                        pass

                if lines[j].strip() == "20":
                    try:
                        max_y = float(lines[j + 1].strip())
                    except:
                        pass

                if max_x is not None and max_y is not None:
                    break

                j += 1

    if (
        min_x is None
        or min_y is None
        or max_x is None
        or max_y is None
    ):
        return None

    return min_x, min_y, max_x, max_y


def find_mtext(lines):
    """
    Находит первый MTEXT и получает:
    - layer
    - координату X
    - координату Y
    - текст
    """

    for i in range(len(lines)):

        if lines[i].strip() != "MTEXT":
            continue

        layer = "0"
        x = None
        y = None
        old_text = ""

        j = i + 1

        while j < len(lines):

            code = lines[j].strip()

            if code == "0":
                break

            if code == "8" and j + 1 < len(lines):
                layer = lines[j + 1].strip()

            elif code == "10" and j + 1 < len(lines):
                try:
                    x = float(lines[j + 1].strip())
                except:
                    pass

            elif code == "20" and j + 1 < len(lines):
                try:
                    y = float(lines[j + 1].strip())
                except:
                    pass

            elif code == "1" and j + 1 < len(lines):
                old_text = lines[j + 1].strip()

            j += 1

        return {
            "start": i,
            "end": j,
            "layer": layer,
            "x": x,
            "y": y,
            "text": old_text
        }

    return None


def make_text_entity(
    handle,
    owner,
    layer,
    x,
    y,
    text,
    angle
):
    """
    Создаёт обычный DXF TEXT.

    TEXT используется вместо MTEXT,
    чтобы CAM получал максимально простой объект.
    """

    return [
        "  0\n",
        "TEXT\n",

        "  5\n",
        f"{handle}\n",

        "330\n",
        f"{owner}\n",

        "100\n",
        "AcDbEntity\n",

        "  8\n",
        f"{layer}\n",

        "100\n",
        "AcDbText\n",

        " 10\n",
        f"{x:.6f}\n",

        " 20\n",
        f"{y:.6f}\n",

        " 30\n",
        "0.0\n",

        " 40\n",
        f"{TEXT_HEIGHT:.6f}\n",

        "  1\n",
        f"{text}\n",

        " 50\n",
        f"{angle:.6f}\n",

        "  7\n",
        "STANDARD\n",

        # Центрирование текста по горизонтали
        " 72\n",
        "1\n",

        # Точка выравнивания
        " 11\n",
        f"{x:.6f}\n",

        " 21\n",
        f"{y:.6f}\n",

        " 31\n",
        "0.0\n",

        # Центрирование по вертикали
        " 73\n",
        "2\n",
    ]


def modify_dxf_text(filepath, new_text):

    with open(
        filepath,
        "r",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        lines = f.readlines()

    # --------------------------------------------------
    # Получаем габариты детали
    # --------------------------------------------------

    extents = find_extents(lines)

    if extents is None:
        raise Exception(
            "Не удалось определить габариты детали"
        )

    min_x, min_y, max_x, max_y = extents

    width = max_x - min_x
    height = max_y - min_y

    # --------------------------------------------------
    # Центр детали
    # --------------------------------------------------

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    # --------------------------------------------------
    # Поворот текста
    #
    # Деталь широкая  -> 0°
    # Деталь высокая  -> 90°
    # --------------------------------------------------

    if height > width:
        angle = 90.0
    else:
        angle = 0.0

    # --------------------------------------------------
    # Ищем существующий MTEXT
    # --------------------------------------------------

    mtext = find_mtext(lines)

    if mtext is None:
        raise Exception(
            "В DXF не найден MTEXT для маркировки"
        )

    start = mtext["start"]
    end = mtext["end"]

    layer = mtext["layer"]

    # --------------------------------------------------
    # Получаем handle MTEXT
    # --------------------------------------------------

    handle = "FFFFFF"

    i = start + 1

    while i < end:

        if lines[i].strip() == "5":

            if i + 1 < end:
                handle = lines[i + 1].strip()

            break

        i += 1

    # --------------------------------------------------
    # Получаем owner 330
    # --------------------------------------------------

    owner = "1F"

    i = start + 1

    while i < end:

        if lines[i].strip() == "330":

            if i + 1 < end:
                owner = lines[i + 1].strip()

            break

        i += 1

    # --------------------------------------------------
    # Создаём новый TEXT
    # --------------------------------------------------

    text_entity = make_text_entity(
        handle,
        owner,
        layer,
        center_x,
        center_y,
        new_text,
        angle
    )

    # --------------------------------------------------
    # Заменяем старый MTEXT на TEXT
    # --------------------------------------------------

    new_lines = (
        lines[:start]
        + text_entity
        + lines[end:]
    )

    # --------------------------------------------------
    # Записываем DXF
    # --------------------------------------------------

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        f.writelines(new_lines)

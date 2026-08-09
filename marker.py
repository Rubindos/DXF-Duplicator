import os


TEXT_HEIGHT = "25"


def make_mark_text(filename, has_back):
    """
    I_6_2.DXF + I_6_O_2.DXF -> I6
    I_6_2.DXF без оборота    -> I
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


def modify_dxf_text(filepath, new_text):

    with open(
        filepath,
        "r",
        encoding="cp1251",
        errors="ignore"
    ) as f:
        lines = f.readlines()

    # --------------------------------------------------
    # Определяем габариты детали
    # --------------------------------------------------

    min_x = None
    min_y = None
    max_x = None
    max_y = None

    for i in range(len(lines) - 1):

        if lines[i].strip() == "$EXTMIN":

            j = i + 1

            while j < min(i + 30, len(lines) - 1):

                if lines[j].strip() == "10":
                    try:
                        min_x = float(lines[j + 1].strip())
                    except:
                        pass

                elif lines[j].strip() == "20":
                    try:
                        min_y = float(lines[j + 1].strip())
                    except:
                        pass

                j += 1

                if min_x is not None and min_y is not None:
                    break

        elif lines[i].strip() == "$EXTMAX":

            j = i + 1

            while j < min(i + 30, len(lines) - 1):

                if lines[j].strip() == "10":
                    try:
                        max_x = float(lines[j + 1].strip())
                    except:
                        pass

                elif lines[j].strip() == "20":
                    try:
                        max_y = float(lines[j + 1].strip())
                    except:
                        pass

                j += 1

                if max_x is not None and max_y is not None:
                    break

    # --------------------------------------------------
    # Если габариты найдены — определяем ориентацию
    # --------------------------------------------------

    angle = "0"

    if (
        min_x is not None
        and min_y is not None
        and max_x is not None
        and max_y is not None
    ):

        width = max_x - min_x
        height = max_y - min_y

        if height > width:
            angle = "90"

    # --------------------------------------------------
    # Изменяем ТОЛЬКО существующий MTEXT
    # --------------------------------------------------

    new_lines = []

    inside_mtext = False
    text_replaced = False
    height_replaced = False
    angle_replaced = False

    i = 0

    while i < len(lines):

        current = lines[i].strip()

        # Начало MTEXT
        if current == "MTEXT":

            inside_mtext = True
            text_replaced = False
            height_replaced = False
            angle_replaced = False

            new_lines.append(lines[i])
            i += 1
            continue

        # Конец сущности
        if inside_mtext and current == "0":

            inside_mtext = False

            new_lines.append(lines[i])
            i += 1
            continue

        # --------------------------------------------------
        # Высота текста
        # --------------------------------------------------

        if inside_mtext and current == "40":

            new_lines.append(lines[i])

            if i + 1 < len(lines):

                new_lines.append(
                    TEXT_HEIGHT + "\n"
                )

                i += 2
                height_replaced = True
                continue

        # --------------------------------------------------
        # Поворот
        # --------------------------------------------------

        if inside_mtext and current == "50":

            new_lines.append(lines[i])

            if i + 1 < len(lines):

                new_lines.append(
                    angle + "\n"
                )

                i += 2
                angle_replaced = True
                continue

        # --------------------------------------------------
        # Текст MTEXT
        # --------------------------------------------------

        if inside_mtext and current == "1":

            new_lines.append(lines[i])

            new_lines.append(
                new_text + "\n"
            )

            i += 2

            text_replaced = True
            continue

        # --------------------------------------------------
        # Остальные данные оставляем БЕЗ ИЗМЕНЕНИЙ
        # --------------------------------------------------

        new_lines.append(lines[i])
        i += 1

    # --------------------------------------------------
    # Если поворота 50 не было — добавляем его перед
    # концом MTEXT.
    #
    # Но специально НЕ перестраиваем DXF.
    # --------------------------------------------------

    if not text_replaced:
        raise Exception(
            "Не найден текст MTEXT для замены"
        )

    # --------------------------------------------------
    # Сохраняем исходный DXF
    # --------------------------------------------------

    with open(
        filepath,
        "w",
        encoding="cp1251",
        errors="ignore"
    ) as f:

        f.writelines(new_lines)

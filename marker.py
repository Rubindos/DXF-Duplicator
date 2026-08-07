import os


def make_mark_text(filename, has_back):

    name = os.path.splitext(filename)[0]
    parts = name.split("_")

    prefix = parts[0]
    number = parts[1]

    if has_back:
        return f"{prefix}{number}"

    return prefix


def modify_dxf_text(filepath, new_text):

    with open(filepath, "r", encoding="cp1251", errors="ignore") as f:
        lines = f.readlines()

    # ---------- определяем размеры детали ----------
    width = 0
    height = 0

    for i in range(len(lines) - 1):

        if lines[i].strip() == "$EXTMAX":

            j = i

            while j < min(i + 20, len(lines)):

                if lines[j].strip() == "10":
                    width = float(lines[j + 1])

                if lines[j].strip() == "20":
                    height = float(lines[j + 1])
                    break

                j += 1

            break

    angle = "0"

    if height > width:
        angle = "90"

    # ---------- изменяем MTEXT ----------

    new_lines = []

    inside = False

    inserted_angle = False

    i = 0

    while i < len(lines):

        s = lines[i].strip()

        new_lines.append(lines[i])

        if s == "MTEXT":
            inside = True
            inserted_angle = False

        elif inside and s == "40":

            new_lines.append("25\n")
            i += 2
            continue

        elif inside and s == "41":

            if not inserted_angle:

                new_lines.append(lines[i])

                new_lines.append(lines[i + 1])

                new_lines.append("50\n")
                new_lines.append(angle + "\n")

                inserted_angle = True

                i += 2
                continue

        elif inside and s == "1":

            new_lines.append(new_text + "\n")
            inside = False
            i += 2
            continue

        i += 1

    with open(filepath, "w", encoding="cp1251", errors="ignore") as f:
        f.writelines(new_lines)

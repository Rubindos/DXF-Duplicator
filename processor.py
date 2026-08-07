import os
import shutil

from marker import make_mark_text, modify_dxf_text


def process_folder(folder):

    reverse_folder = os.path.join(folder, "Reverse")
    os.makedirs(reverse_folder, exist_ok=True)

    # Запоминаем детали, у которых есть оборотная сторона
    back_parts = set()

    for filename in os.listdir(folder):

        if not filename.upper().endswith(".DXF"):
            continue

        name = os.path.splitext(filename)[0]
        parts = name.split("_")

        if "O" in parts:
            key = f"{parts[0]}_{parts[1]}"
            back_parts.add(key)

    front = 0
    reverse = 0
    copies = 0
    errors = 0

    for filename in os.listdir(folder):

        if not filename.upper().endswith(".DXF"):
            continue

        fullpath = os.path.join(folder, filename)

        if not os.path.isfile(fullpath):
            continue

        try:

            name = os.path.splitext(filename)[0]
            parts = name.split("_")

            # ---------- ОБОРОТ ----------
            if "O" in parts:

                shutil.move(
                    fullpath,
                    os.path.join(reverse_folder, filename)
                )

                reverse += 1
                continue

            # ---------- ЛИЦО ----------

            qty = int(parts[-1])

            key = f"{parts[0]}_{parts[1]}"

            has_back = key in back_parts

            text = make_mark_text(filename, has_back)

            modify_dxf_text(fullpath, text)

            prefix = "_".join(parts[:-1])

            front += 1

            for i in range(1, qty + 1):

                newname = f"{prefix}_{i}.DXF"

                shutil.copy2(
                    fullpath,
                    os.path.join(folder, newname)
                )

                copies += 1

            os.remove(fullpath)

        except Exception as e:
            print(e)
            errors += 1

    return {
        "front": front,
        "reverse": reverse,
        "copies": copies,
        "errors": errors
    }

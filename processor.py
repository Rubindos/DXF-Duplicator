import os
import shutil

from marker import make_mark_text, modify_dxf_text


def process_folder(folder):

    reverse_folder = os.path.join(folder, "Reverse")
    os.makedirs(reverse_folder, exist_ok=True)

    # --------------------------------------------------
    # 1. Находим все детали, у которых есть оборот
    # --------------------------------------------------

    back_parts = set()

    for filename in os.listdir(folder):

        if not filename.upper().endswith(".DXF"):
            continue

        name = os.path.splitext(filename)[0]
        parts = name.split("_")

        # Пример:
        # I_6_O_2
        #
        # parts:
        # [I, 6, O, 2]

        if len(parts) >= 3 and parts[2].upper() == "O":

            key = f"{parts[0]}_{parts[1]}"

            back_parts.add(key)

    front = 0
    reverse = 0
    copies = 0
    errors = 0

    # --------------------------------------------------
    # 2. Обрабатываем только исходные DXF
    # --------------------------------------------------

    files = list(os.listdir(folder))

    for filename in files:

        if not filename.upper().endswith(".DXF"):
            continue

        fullpath = os.path.join(folder, filename)

        if not os.path.isfile(fullpath):
            continue

        try:

            name = os.path.splitext(filename)[0]
            parts = name.split("_")

            # --------------------------------------------------
            # ОБОРОТНАЯ СТОРОНА
            # --------------------------------------------------

            if len(parts) >= 3 and parts[2].upper() == "O":

                destination = os.path.join(
                    reverse_folder,
                    filename
                )

                # Если такой файл уже существует,
                # заменяем его
                if os.path.exists(destination):
                    os.remove(destination)

                shutil.move(
                    fullpath,
                    destination
                )

                reverse += 1

                continue

            # --------------------------------------------------
            # ЛИЦЕВАЯ СТОРОНА
            # --------------------------------------------------

            if len(parts) < 2:
                errors += 1
                continue

            # Последняя часть — количество
            qty = int(parts[-1])

            # Например:
            # I_6_2
            #
            # key = I_6

            key = f"{parts[0]}_{parts[1]}"

            has_back = key in back_parts

            # Текст маркировки:
            #
            # I_6_2 + оборот -> I6
            #
            # I_6_2 без оборота -> I

            text = make_mark_text(
                filename,
                has_back
            )

            # --------------------------------------------------
            # Создаём копии
            # --------------------------------------------------

            prefix = "_".join(parts[:-1])

            created_files = []

            for i in range(1, qty + 1):

                newname = f"{prefix}_{i}.DXF"

                newpath = os.path.join(
                    folder,
                    newname
                )

                # Если файл уже существует —
                # удаляем старую копию
                if os.path.exists(newpath):
                    os.remove(newpath)

                shutil.copy2(
                    fullpath,
                    newpath
                )

                created_files.append(newpath)

                copies += 1

            # --------------------------------------------------
            # Теперь маркируем КОПИИ,
            # а не исходный DXF
            # --------------------------------------------------

            for newpath in created_files:

                modify_dxf_text(
                    newpath,
                    text
                )

            # --------------------------------------------------
            # После успешной обработки удаляем исходник
            # --------------------------------------------------

            os.remove(fullpath)

            front += 1

        except Exception as e:

            print(
                f"Ошибка обработки {filename}: {e}"
            )

            errors += 1

    return {
        "front": front,
        "reverse": reverse,
        "copies": copies,
        "errors": errors
    }

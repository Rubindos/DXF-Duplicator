import os
import shutil

from marker import make_mark_text, modify_dxf_text


def process_folder(folder):

    reverse_folder = os.path.join(folder, "Reverse")
    os.makedirs(reverse_folder, exist_ok=True)

    front = 0
    reverse = 0
    copies = 0
    errors = 0

    # ==================================================
    # ВАЖНО:
    # Один раз получаем список ИСХОДНЫХ файлов.
    #
    # Новые копии, созданные ниже, сюда уже не попадут.
    # ==================================================

    source_files = []

    for filename in os.listdir(folder):

        fullpath = os.path.join(folder, filename)

        if not os.path.isfile(fullpath):
            continue

        if not filename.upper().endswith(".DXF"):
            continue

        source_files.append(filename)

    # ==================================================
    # Ищем оборотные стороны
    # ==================================================

    back_parts = set()

    for filename in source_files:

        name = os.path.splitext(filename)[0]
        parts = name.split("_")

        # I_6_O_2.DXF
        #
        # [I, 6, O, 2]

        if len(parts) >= 4:

            if parts[2].upper() == "O":

                key = f"{parts[0]}_{parts[1]}"

                back_parts.add(key)

    # ==================================================
    # Обрабатываем ТОЛЬКО исходные файлы
    # ==================================================

    for filename in source_files:

        fullpath = os.path.join(folder, filename)

        try:

            name = os.path.splitext(filename)[0]
            parts = name.split("_")

            # ==================================================
            # ОБОРОТНАЯ СТОРОНА
            # ==================================================

            if len(parts) >= 4 and parts[2].upper() == "O":

                destination = os.path.join(
                    reverse_folder,
                    filename
                )

                if os.path.exists(destination):
                    os.remove(destination)

                shutil.move(
                    fullpath,
                    destination
                )

                reverse += 1

                continue

            # ==================================================
            # ЛИЦЕВАЯ СТОРОНА
            # ==================================================

            if len(parts) < 3:
                continue

            # Последний элемент = количество

            try:
                qty = int(parts[-1])
            except ValueError:
                errors += 1
                continue

            # Например:
            #
            # I_6_2.DXF
            #
            # parts:
            # I
            # 6
            # 2
            #
            # prefix:
            # I_6

            prefix = "_".join(parts[:-1])

            key = f"{parts[0]}_{parts[1]}"

            has_back = key in back_parts

            # Получаем текст:
            #
            # I_6_2 + оборот -> I6
            # I_6_2 без оборота -> I

            mark_text = make_mark_text(
                filename,
                has_back
            )

            # ==================================================
            # Создаём копии
            # ==================================================

            created_files = []

            for number in range(1, qty + 1):

                newname = f"{prefix}_{number}.DXF"

                newpath = os.path.join(
                    folder,
                    newname
                )

                # Если имя совпадает с исходником,
                # сначала не удаляем его.
                #
                # Например:
                # I_6_2.DXF
                #
                # одна из копий тоже I_6_2.DXF

                if os.path.abspath(newpath) != os.path.abspath(fullpath):

                    if os.path.exists(newpath):
                        os.remove(newpath)

                    shutil.copy2(
                        fullpath,
                        newpath
                    )

                else:

                    # Исходный файл уже является
                    # одной из необходимых копий.
                    #
                    # Просто используем его.

                    pass

                created_files.append(newpath)

                copies += 1

            # ==================================================
            # Наносим маркировку
            # ==================================================

            for newpath in created_files:

                modify_dxf_text(
                    newpath,
                    mark_text
                )

            # ==================================================
            # Если исходный файл НЕ входит в итоговые копии,
            # удаляем его.
            # ==================================================

            source_is_result = False

            for result_file in created_files:

                if os.path.abspath(result_file) == os.path.abspath(fullpath):

                    source_is_result = True
                    break

            if not source_is_result:

                os.remove(fullpath)

            front += 1

        except Exception as e:

            print(
                f"Ошибка: {filename} -> {e}"
            )

            errors += 1

    # ==================================================
    # Результат
    # ==================================================

    return {
        "front": front,
        "reverse": reverse,
        "copies": copies,
        "errors": errors
    }

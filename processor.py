import os
import shutil

def process_folder(folder):

    reverse_folder = os.path.join(folder, "Reverse")
    os.makedirs(reverse_folder, exist_ok=True)

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

            name, ext = os.path.splitext(filename)
            parts = name.split("_")

            # ------------------------
            # ОБОРОТНАЯ СТОРОНА
            # Если есть O
            # ------------------------

            if "O" in parts:

                shutil.move(
                    fullpath,
                    os.path.join(reverse_folder, filename)
                )

                reverse += 1
                continue

            # ------------------------
            # ЛИЦЕВАЯ СТОРОНА
            # ------------------------

            qty = int(parts[-1])

            prefix = "_".join(parts[:-1])

            front += 1

            for i in range(1, qty + 1):

                newname = f"{prefix}_{i}{ext}"

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

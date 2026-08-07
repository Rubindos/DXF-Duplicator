import os
import shutil

def process_folder(folder):

    reverse_folder = os.path.join(folder, "Reverse")
    os.makedirs(reverse_folder, exist_ok=True)

    front = 0
    reverse = 0
    copies = 0
    errors = 0

    files = list(os.listdir(folder))

    for filename in files:

        if not filename.upper().endswith(".DXF"):
            continue

        fullpath = os.path.join(folder, filename)

        if not os.path.isfile(fullpath):
            continue

        name, ext = os.path.splitext(filename)
        parts = name.split("_")

        try:

            # ---------------------------
            # Форматы:
            # 23_2.DXF
            # I_23_2.DXF
            # ---------------------------

            if len(parts) == 2 or (len(parts) == 3 and not parts[0].isdigit()):

                if len(parts) == 2:
                    prefix = ""
                    number = parts[0]
                    qty = int(parts[1])

                else:
                    prefix = parts[0] + "_"
                    number = parts[1]
                    qty = int(parts[2])

                front += 1

                for i in range(1, qty + 1):

                    newname = f"{prefix}{number}_{i}{ext}"

                    shutil.copy2(
                        fullpath,
                        os.path.join(folder, newname)
                    )

                    copies += 1

                os.remove(fullpath)

            # ---------------------------
            # Форматы:
            # 23_1_2.DXF
            # I_23_1_2.DXF
            # ---------------------------

            elif len(parts) == 3 or len(parts) == 4:

                shutil.move(
                    fullpath,
                    os.path.join(reverse_folder, filename)
                )

                reverse += 1

        except Exception:
            errors += 1

    return {
        "front": front,
        "reverse": reverse,
        "copies": copies,
        "errors": errors
    }

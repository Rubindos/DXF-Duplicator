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

        if not filename.lower().endswith(".dxf"):
            continue

        name, ext = os.path.splitext(filename)

        parts = name.split("_")

        try:

            # Лицевая сторона
            if len(parts) == 2:

                number = parts[0]
                qty = int(parts[1])

                front += 1

                source = os.path.join(folder, filename)

                if qty > 1:

                    for i in range(1, qty):

                        newname = f"{number}_{i}{ext}"

                        shutil.copy2(
                            source,
                            os.path.join(folder, newname)
                        )

                        copies += 1

                    os.rename(
                        source,
                        os.path.join(folder, f"{number}_{qty}{ext}")
                    )

            # Обратная сторона
            elif len(parts) == 3:

                shutil.move(
                    os.path.join(folder, filename),
                    os.path.join(reverse_folder, filename)
                )

                reverse += 1

        except:

            errors += 1

    return {
        "front": front,
        "reverse": reverse,
        "copies": copies,
        "errors": errors
    }

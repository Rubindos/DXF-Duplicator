import os
import shutil
from tkinter import Tk, Button, filedialog, messagebox

def process():
    folder = filedialog.askdirectory(title="Выберите папку с DXF")
    if not folder:
        return

    for file in os.listdir(folder):
        if not file.lower().endswith(".dxf"):
            continue

        name = os.path.splitext(file)[0]
        parts = name.split("_")

        if len(parts) != 3:
            continue

        pos, side, qty = parts

        try:
            qty = int(qty)
        except:
            continue

        src = os.path.join(folder, file)

        for i in range(1, qty + 1):
            dst = os.path.join(folder, f"{pos}_{side}_{i}.dxf")
            shutil.copy2(src, dst)

    messagebox.showinfo("Готово", "Обработка завершена!")

root = Tk()
root.title("DXF Duplicator")
root.geometry("300x120")

Button(root, text="Выбрать папку и обработать", command=process).pack(expand=True)

root.mainloop()

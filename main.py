import tkinter as tk
from tkinter import filedialog, messagebox
from processor import process_folder

def run():
    folder = filedialog.askdirectory(title="Выберите папку с DXF")
    if not folder:
        return

    result = process_folder(folder)

    messagebox.showinfo(
        "Готово",
        f"""Лицевых файлов: {result['front']}
Создано копий: {result['copies']}
Перемещено обратных: {result['reverse']}
Ошибок: {result['errors']}"""
    )

root = tk.Tk()
root.title("DXF Manager")
root.geometry("350x140")

btn = tk.Button(root,
                text="Выбрать папку и обработать",
                command=run,
                height=2)

btn.pack(expand=True, padx=20, pady=20)

root.mainloop()

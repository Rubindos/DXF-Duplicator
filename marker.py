import os
import re


def make_mark_text(filename, has_back):
    """
    I_6_2.DXF      -> I
    I_6_2.DXF + back -> I6

    II_23_5.DXF -> II
    II_23_5.DXF + back -> II23
    """

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

    new_lines = []

    inside_mtext = False

    i = 0

    while i < len(lines):

        line = lines[i].rstrip("\n")

        new_lines.append(lines[i])

        if line.strip() == "MTEXT":
            inside_mtext = True

        elif inside_mtext and line.strip() == "40":
            if i + 1 < len(lines):
                new_lines.append("25\n")
                i += 2
                continue

        elif inside_mtext and line.strip() == "1":
            if i + 1 < len(lines):
                new_lines.append(new_text + "\n")
                inside_mtext = False
                i += 2
                continue

        i += 1

    with open(filepath, "w", encoding="cp1251", errors="ignore") as f:
        f.writelines(new_lines)

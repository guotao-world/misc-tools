# -*- coding: utf-8 -*-
import xlrd
import xlwt
from xlutils.copy import copy

def insert_column(rows, insert_col_index, default_value=0):
    header = rows[0]
    data_rows = rows[1:]
    new_rows = []
    number = default_value
    # 处理表头 - 确保header是列表
    header = [header]
    for row in header:
        new_row = row[:insert_col_index] + ["index"] + row[insert_col_index:]
        new_rows.append(new_row)
    for row in data_rows:
        new_row = row[:insert_col_index] + [number] + row[insert_col_index:]
        new_rows.append(new_row)
        number = number + 1
    return new_rows

def delete_column(rows, delete_col_index):
    new_rows = []
    for row in rows:
        new_row = row[:delete_col_index] + row[delete_col_index + 1:]
        new_rows.append(new_row)
    return new_rows

def insert_row(rows, insert_row_index, default_row):
    return rows[:insert_row_index] + [default_row] + rows[insert_row_index:]

def delete_row(rows, delete_row_index):
    return rows[:delete_row_index] + rows[delete_row_index + 1:]

def sort_rows_by_column(rows, sort_col):
    header = rows[0]
    data_rows = rows[1:]
    try:
        data_rows.sort(key=lambda row: float(row[sort_col]), reverse=False)
    except ValueError:
        data_rows.sort(key=lambda row: str(row[sort_col]), reverse=False)
    return [header] + data_rows

def write_to_excel(rows, sheet_name, output_file):
    new_wb = xlwt.Workbook()
    new_ws = new_wb.add_sheet(sheet_name)
    for row_idx, row in enumerate(rows):
        for col_idx, value in enumerate(row):
            new_ws.write(row_idx, col_idx, value)
    new_wb.save(output_file)
    print(f"写入完成，保存为: {output_file}")

def main():
    old_file = "豆瓣电影Top25.xls"
    new_file = "豆瓣电影Top25_modified.xls"

    # 读取原始数据
    rb = xlrd.open_workbook(old_file, formatting_info=True)
    sheet = rb.sheet_by_index(0)
    all_rows = [sheet.row_values(i) for i in range(sheet.nrows)]
    sheet_name = sheet.name

    # 调用处理函数
    all_rows = insert_column(all_rows, 0, 0)
    all_rows = sort_rows_by_column(all_rows, 5)
    all_rows = insert_column(all_rows, 5, 0)
    all_rows = sort_rows_by_column(all_rows, 0)
    all_rows = delete_column(all_rows, 0)
    
    # all_rows[0][1] = ""
    # all_rows = insert_row(all_rows, 2, ["新行"] * len(all_rows[0]))
    # all_rows = delete_row(all_rows, 4)

    # 写入新文件
    write_to_excel(all_rows, sheet_name, new_file)

if __name__ == "__main__":
    main()
    print("完成")

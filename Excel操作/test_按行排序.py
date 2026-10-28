# -*- coding: utf-8 -*-
import xlrd
import xlwt
from xlutils.copy import copy

def main():
    old_file = "豆瓣电影Top25.xls"
    new_file = "豆瓣电影Top25_sorted.xls"
    sort_xls_by_column(old_file, new_file, sort_col=5)

def get_sort_key(row):
    try:
        return float(row[5])
    except ValueError:
        return str(row[5])


def sort_xls_by_column(old_file, new_file, sort_col):
    # 读取旧 Excel 文件
    rb = xlrd.open_workbook(old_file, formatting_info=True)
    sheet = rb.sheet_by_index(0)

    # 读取所有数据（每一行作为列表），包括表头
    all_rows = [sheet.row_values(row_idx) for row_idx in range(sheet.nrows)]

    # 分离表头和数据
    header = all_rows[0]
    data_rows = all_rows[1:]

    # 排序：按指定列从小到大（如果是数字排序）
    data_rows.sort(key=get_sort_key)

    # 创建新 workbook，写入排序后的内容
    new_wb = xlwt.Workbook()
    new_ws = new_wb.add_sheet(sheet.name)

    # 写入表头
    for col, value in enumerate(header):
        new_ws.write(0, col, value)

    # 写入排序后的数据
    for row_idx, row_data in enumerate(data_rows, start=1):
        for col_idx, value in enumerate(row_data):
            new_ws.write(row_idx, col_idx, value)

    # 保存到新文件
    new_wb.save(new_file)
    print(f"按第 {sort_col + 1} 列排序后保存到: {new_file}")

if __name__ == "__main__":
    main()
    print("排序完成")

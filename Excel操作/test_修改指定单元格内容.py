# -*- codeing = utf-8 -*-
from bs4 import BeautifulSoup  # 网页解析，获取数据
import re  # 正则表达式，进行文字匹配`
import urllib.request
import urllib.error  # 制定URL，获取网页数据
import xlwt  # 进行excel操作
import xlrd
from xlutils.copy import copy

def main():
    # 使用示例：修改第2行，第3列（从0开始计数）内容为“修改后的内容”
    old_file = "豆瓣电影Top25.xls"
    new_file = "豆瓣电影Top25_modified.xls"
    modify_xls_cell(old_file, new_file, 1, 2, "修改后的内容")


def modify_xls_cell(old_file, new_file, row, col, new_value):
    # 读取旧文件
    rb = xlrd.open_workbook(old_file, formatting_info=True)  # formatting_info=True保留格式
    sheet = rb.sheet_by_index(0)

    # 复制成可写的workbook
    wb = copy(rb)
    ws = wb.get_sheet(0)

    # 修改指定单元格
    ws.write(row, col, new_value)

    # 保存为新文件
    wb.save(new_file)
    print(f"修改后保存到: {new_file}")



if __name__ == "__main__":  # 当程序执行时
    # 调用函数
    main()
    # init_db("movietest.db")
    print("更新完毕")

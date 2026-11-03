# -*- codeing = utf-8 -*-
from bs4 import BeautifulSoup  # 网页解析，获取数据
import re  # 正则表达式，进行文字匹配`
import urllib.request
import urllib.error  # 制定URL，获取网页数据
import xlwt  # 进行excel操作
# import sqlite3  # 进行SQLite数据库操作

findLink = re.compile(r'<a href="(.*?)">')  # 创建正则表达式对象，标售规则   影片详情链接的规则
findImgSrc = re.compile(r'<img.*src="(.*?)"', re.S)
findTitle = re.compile(r'<span class="title">(.*)</span>')
findRating = re.compile(
    r'<span class="rating_num" property="v:average">(.*)</span>')
findJudge = re.compile(r'<span>(\d*)人评价</span>')
findInq = re.compile(r'<span class="inq">(.*)</span>')
findBd = re.compile(r'<div class="bd">.*?<p.*?>(.*?)</p>', re.S)


def main():
    baseurl = "https://movie.douban.com/top250?start="  # 要爬取的网页链接
    # 1.爬取网页
    datalist = getData(baseurl)
    savepath = "豆瓣电影Top25.xls"  # 当前目录新建XLS，存储进去
    # dbpath = "movie.db"              #当前目录新建数据库，存储进去
    # 3.保存数据
    saveData(datalist, savepath)  # 2种存储方式可以只选择一种
    # saveData2DB(datalist,dbpath)


# 爬取网页
def getData(baseurl):
    datalist = []
    for i in range(0, 1):
        url = baseurl + str(i * 25)
        html = askURL(url)
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.find_all('div', class_="item"):
            data = []
            item = str(item)

            # 提取链接
            link = re.findall(findLink, item)[0]
            data.append(link)

            # 提取图片
            imgSrc = re.findall(findImgSrc, item)[0]
            data.append(imgSrc)

            # 提取标题
            titles = re.findall(findTitle, item)
            if len(titles) == 2:
                data.append(titles[0])  # 中文名
                data.append(titles[1].replace("/", ""))  # 外文名
            else:
                data.append(titles[0])
                data.append(" ")  # 外文名留空

            # 提取评分
            rating = re.findall(findRating, item)[0]
            data.append(rating)

            # 提取评价人数
            judgeNum = re.findall(findJudge, item)[0]
            data.append(judgeNum)

            # 提取短评
            inq = re.findall(findInq, item)
            data.append(inq[0].replace("。", "") if inq else " ")

            # 提取简介（修复点）
            bd_matches = re.findall(findBd, item)
            if bd_matches:
                bd = bd_matches[0]
                bd = re.sub(r'<br(\s+)?/>(\s+)?', "", bd)
                bd = re.sub('/', "", bd).strip()
            else:
                bd = "暂无简介"
            data.append(bd)

            datalist.append(data)
    return datalist


# 得到指定一个URL的网页内容
def askURL(url):
    head = {  # 模拟浏览器头部信息，向豆瓣服务器发送消息
        "User-Agent": "Mozilla / 5.0(Windows NT 10.0; Win64; x64) AppleWebKit / 537.36(KHTML, like Gecko) Chrome / 80.0.3987.122  Safari / 537.36"
    }
    # 用户代理，表示告诉豆瓣服务器，我们是什么类型的机器、浏览器（本质上是告诉浏览器，我们可以接收什么水平的文件内容）

    request = urllib.request.Request(url, headers=head)
    html = ""
    try:
        response = urllib.request.urlopen(request)
        html = response.read().decode("utf-8")
    except urllib.error.URLError as e:
        if hasattr(e, "code"):
            print(e.code)
        if hasattr(e, "reason"):
            print(e.reason)
    return html


# 保存数据到表格
def saveData(datalist, savepath):
    print("save.......")
    book = xlwt.Workbook(encoding="utf-8", style_compression=0)  # 创建workbook对象
    sheet = book.add_sheet('豆瓣电影Top25', cell_overwrite_ok=True)  # 创建工作表
    col = ("电影详情链接", "图片链接", "影片中文名", "影片外国名", "评分", "评价数", "概况", "相关信息")
    #for i in range(8):
    #    sheet.col(i).width = 256 * 20  # 20个字符宽度，256是Excel单位换算
    sheet.col(0).width = 256 * 20  # 20个字符宽度，256是Excel单位换算
    sheet.col(1).width = 256 * 20  # 20个字符宽度，256是Excel单位换算
    sheet.col(2).width = 256 * 20  # 20个字符宽度，256是Excel单位换算
    sheet.col(3).width = 256 * 20  # 20个字符宽度，256是Excel单位换算

    sheet.col(4).width = 256 * 5  # 20个字符宽度，256是Excel单位换算
    sheet.col(5).width = 256 * 10  # 20个字符宽度，256是Excel单位换算
    sheet.col(6).width = 256 * 10  # 20个字符宽度，256是Excel单位换算
    sheet.col(7).width = 256 * 20  # 20个字符宽度，256是Excel单位换算

    # 创建字体样式
    font = xlwt.Font()
    font.name = 'Arial'
    font.bold = True  # 加粗
    font.height = 220  # 字体大小（单位1/20磅）
    # 创建对齐方式
    alignment = xlwt.Alignment()
    alignment.horz = xlwt.Alignment.HORZ_CENTER  # 水平居中
    alignment.vert = xlwt.Alignment.VERT_CENTER  # 垂直居中
    # 创建样式
    style = xlwt.XFStyle()
    style.font = font
    style.alignment = alignment
    # 写入表头时使用style
    for i in range(8):
        sheet.write(0, i, col[i], style)

    data_style = xlwt.XFStyle()
    # 字体
    data_font = xlwt.Font()
    data_font.name = 'Arial'
    data_style.font = data_font
    # 对齐
    data_alignment = xlwt.Alignment()
    data_alignment.horz = xlwt.Alignment.HORZ_LEFT
    data_alignment.vert = xlwt.Alignment.VERT_CENTER
    data_style.alignment = data_alignment
    for i in range(len(datalist)):
        data = datalist[i]
        for j in range(8):
            sheet.write(i+1, j, data[j], data_style)
    book.save(savepath)  # 保存

# def saveData2DB(datalist,dbpath):
#     init_db(dbpath)
#     conn = sqlite3.connect(dbpath)
#     cur = conn.cursor()
#     for data in datalist:
#             for index in range(len(data)):
#                 if index == 4 or index == 5:
#                     continue
#                 data[index] = '"'+data[index]+'"'
#             sql = '''
#                     insert into movie250(
#                     info_link,pic_link,cname,ename,score,rated,instroduction,info)
#                     values (%s)'''%",".join(data)
#             # print(sql)     #输出查询语句，用来测试
#             cur.execute(sql)
#             conn.commit()
#     cur.close
#     conn.close()


# def init_db(dbpath):
#     sql = '''
#         create table movie250(
#         id integer  primary  key autoincrement,
#         info_link text,
#         pic_link text,
#         cname varchar,
#         ename varchar ,
#         score numeric,
#         rated numeric,
#         instroduction text,
#         info text
#         )
#
#
#     '''  #创建数据表
#     conn = sqlite3.connect(dbpath)
#     cursor = conn.cursor()
#     cursor.execute(sql)
#     conn.commit()
#     conn.close()

# 保存数据到数据库


if __name__ == "__main__":  # 当程序执行时
    # 调用函数
    main()
    # init_db("movietest.db")
    print("爬取完毕！")

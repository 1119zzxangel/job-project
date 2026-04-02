# -*- coding: utf-8 -*-
# @Time: 2023-1-29 9:01
# @File: tools.py
# @IDE: PyCharm

import time
from lxml import etree
from multiprocessing.dummy import Pool
import pymysql

import os
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))


# city, all_page, spider_code
def lieSpider(key_word, city, all_page):
    """
    猎聘网爬虫主函数
    :param key_word: 搜索关键词
    :param city: 城市名称
    :param all_page: 需要爬取的页数
    """
    city_dict = {'全国': '410', '北京': '010', '上海': '020', '天津': '030', '重庆': '040', '广州': '050020',
                 '深圳': '050090',
                 '苏州': '060080', '南京': '060020', '杭州': '070020', '大连': '210040', '成都': '280020',
                 '武汉': '170020',
                 '西安': '270020'}
    # 生成需要爬取的URL列表
    urls_list = get_liepin_urls(key_word, all_page, city_dict.get(city, '410'))  # 默认为全国
    # 使用线程池进行多线程爬取
    pool = Pool(2)  # 适当增加线程数，但不宜过多以免被封IP
    pool.map(get_liepin_pages, urls_list)
    pool.close()
    pool.join()
    print("猎聘网爬虫执行完成")
    return 0


def zhilianSpider(key_word, city, all_page):
    """
    智联招聘爬虫主函数
    :param key_word: 搜索关键词
    :param city: 城市名称
    :param all_page: 需要爬取的页数
    """
    city_dict = {'全国': '000000', '北京': '010000', '上海': '020000', '天津': '030000', '重庆': '040000', '广州': '050000',
                 '深圳': '050000', '苏州': '060200', '南京': '060100', '杭州': '070000', '大连': '210200', '成都': '280100',
                 '武汉': '170100', '西安': '270100'}
    # 生成需要爬取的URL列表
    urls_list = get_zhilian_urls(key_word, all_page, city_dict.get(city, '000000'))  # 默认为全国
    # 使用线程池进行多线程爬取
    pool = Pool(2)  # 适当增加线程数，但不宜过多以免被封IP
    pool.map(get_zhilian_pages, urls_list)
    pool.close()
    pool.join()
    print("智联招聘爬虫执行完成")
    return 0


def get_liepin_urls(key_word, all_page, city_code):
    """
    生成猎聘网需要爬取的URL列表
    :param key_word: 搜索关键词
    :param all_page: 需要爬取的页数
    :param city_code: 城市代码
    :return: URL列表
    """
    urls_list = []
    for page in range(1, int(all_page) + 1):
        url = f'https://www.liepin.com/zhaopin/?city={city_code}&dq={city_code}&currentPage={page}&pageSize=40&key={key_word}'
        urls_list.append(url)
    return urls_list


def get_zhilian_urls(key_word, all_page, city_code):
    """
    生成智联招聘需要爬取的URL列表
    :param key_word: 搜索关键词
    :param all_page: 需要爬取的页数
    :param city_code: 城市代码
    :return: URL列表
    """
    urls_list = []
    for page in range(1, int(all_page) + 1):
        url = f'https://sou.zhaopin.com/?jl={city_code}&kw={key_word}&p={page}'
        urls_list.append(url)
    return urls_list


def get_city():
    """
    抓取城市列表及其对应的代码
    :return: 城市列表，每个元素为[城市名称, 城市代码]
    """
    print('开始抓取城市列表...')

    chrome_options = Options()
    # 忽略 SSL 错误
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    # 添加 user-agent 模拟真实浏览器
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    # 禁用浏览器弹窗
    chrome_options.add_argument('--disable-popup-blocking')
    # 禁用扩展
    chrome_options.add_argument('--disable-extensions')
    # 其他选项
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # 使用 undetected_chromedriver
    driver = uc.Chrome(options=chrome_options, version_main=None)

    try:
        driver.get('https://www.liepin.com/zhaopin/?inputFrom=head_navigation&scene=init&workYearCode=0&ckId=ayvlgrooqq8e4w2b3yoae69sd91dmbq9')
        time.sleep(3)
        req_html = etree.HTML(driver.page_source)
        code_list = req_html.xpath('//li[@data-key="dq"]/@data-code')
        name_list = req_html.xpath('//li[@data-key="dq"]/@data-name')
        city_list = [[name, code] for name, code in zip(name_list, code_list)]
        print('抓取到的城市列表:', city_list)
        return city_list
    except Exception as e:
        print('抓取城市列表失败:', e)
        return []
    finally:
        driver.quit()


def get_liepin_pages(url):
    """
    爬取猎聘网单个页面的职位信息并存储到数据库
    :param url: 需要爬取的页面URL
    """
    mysql_conn = get_mysql()
    conn = mysql_conn[0]
    cur = mysql_conn[1]
    print(f'开始爬取猎聘网 {url}...')

    chrome_options = Options()
    # 忽略 SSL 错误
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    # 添加 user-agent 模拟真实浏览器
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    # 禁用浏览器弹窗
    chrome_options.add_argument('--disable-popup-blocking')
    # 禁用扩展
    chrome_options.add_argument('--disable-extensions')
    # 其他选项
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # 使用 undetected_chromedriver
    driver = uc.Chrome(options=chrome_options, version_main=146)

    try:
        driver.get(url)
        time.sleep(3)
        req_html = etree.HTML(driver.page_source)

        # 提取职位信息
        name = req_html.xpath('//div[@class="jsx-2387891236 ellipsis-1"]/text()')
        salary = req_html.xpath('//span[@class="jsx-2387891236 job-salary"]/text()')
        address = req_html.xpath('//span[@class="jsx-2387891236 ellipsis-1"]/text()')
        education = req_html.xpath('//div[@class="jsx-2387891236 job-labels-box"]/span[2]/text()')
        experience = req_html.xpath('//div[@class="jsx-2387891236 job-labels-box"]/span[1]/text()')
        com_name = req_html.xpath('//span[@class="jsx-2387891236 company-name ellipsis-1"]/text()')
        tag_list = req_html.xpath('//div[@class="jsx-2387891236 company-tags-box ellipsis-1"]')
        href_list = req_html.xpath('//a[@data-nick="job-detail-job-info"]/@href')
        # 提取技能要求
        skills_list = []
        skills_elements = req_html.xpath('//div[@class="jsx-2387891236 job-tags-box"]')
        for skills in skills_elements:
            skill_items = skills.xpath('./span/text()')
            skills_list.append(','.join(skill_items) if skill_items else '')

        # 处理标签信息
        label_list = []
        scale_list = []
        for tag in tag_list:
            span_list = tag.xpath('./span/text()')
            if span_list:
                label_list.append(span_list[0])
                scale_list.append(span_list[-1])
            else:
                label_list.append('')
                scale_list.append('')

        # 确保所有列表长度一致
        lists = [name, salary, address, education, experience, com_name, label_list, scale_list, href_list, skills_list]
        min_length = min(len(lst) for lst in lists)
        for lst in lists:
            lst[:] = lst[:min_length]

        # 插入数据库
        select_sql = 'SELECT href FROM job_data'
        cur.execute(select_sql)
        href_list_mysql = [x[0] for x in cur.fetchall()]

        insert_sql = '''INSERT INTO job_data(name, salary, place, education, experience, company, label, scale, href, key_word, required_skills) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''

        for i in range(min_length):
            href = href_list[i].split('?')[0]
            if href not in href_list_mysql:
                # 确保 skills_list 有足够的元素
                required_skills = skills_list[i] if i < len(skills_list) else ''
                data = (name[i], salary[i], address[i], education[i], experience[i], com_name[i], label_list[i], scale_list[i], href, url.split('=')[-1], required_skills)
                try:
                    cur.execute(insert_sql, data)
                    conn.commit()
                    print(f'插入数据成功: {name[i]}')
                except Exception as e:
                    print(f'插入数据失败: {e}')
                    conn.rollback()
            else:
                print(f'数据已存在，跳过: {href}')

    except Exception as e:
        print(f'爬取页面 {url} 失败: {e}')
    finally:
        cur.close()
        conn.close()
        driver.quit()


def get_zhilian_pages(url):
    """
    爬取智联招聘单个页面的职位信息并存储到数据库
    :param url: 需要爬取的页面URL
    """
    mysql_conn = get_mysql()
    conn = mysql_conn[0]
    cur = mysql_conn[1]
    print(f'开始爬取智联招聘 {url}...')

    chrome_options = Options()
    # 忽略 SSL 错误
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    # 添加 user-agent 模拟真实浏览器
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    # 禁用浏览器弹窗
    chrome_options.add_argument('--disable-popup-blocking')
    # 禁用扩展
    chrome_options.add_argument('--disable-extensions')
    # 其他选项
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # 使用 undetected_chromedriver
    driver = uc.Chrome(options=chrome_options, version_main=None)

    try:
        driver.get(url)
        time.sleep(3)
        req_html = etree.HTML(driver.page_source)

        # 提取职位信息
        name = req_html.xpath('//div[@class="joblist-box__item-title"]/text()')
        salary = req_html.xpath('//span[@class="joblist-box__item-salary"]/text()')
        address = req_html.xpath('//li[@class="joblist-box__item-workcity"]/text()')
        education = req_html.xpath('//li[@class="joblist-box__item-edu"]/text()')
        experience = req_html.xpath('//li[@class="joblist-box__item-workyear"]/text()')
        com_name = req_html.xpath('//a[@class="joblist-box__item-companyname"]/text()')
        tag_list = req_html.xpath('//div[@class="joblist-box__item-tag"]')
        href_list = req_html.xpath('//a[@class="joblist-box__item-info"]/@href')
        # 提取技能要求
        skills_list = []
        skills_elements = req_html.xpath('//div[@class="joblist-box__item-tag"]')
        for skills in skills_elements:
            skill_items = skills.xpath('./span/text()')
            # 过滤掉公司类型和规模信息，只保留技能标签
            skill_filtered = [item for item in skill_items if item not in ['计算机软件', 'IT服务', '互联网', '100-499人', '2000-5000人', '10000人以上']]
            skills_list.append(','.join(skill_filtered) if skill_filtered else '')

        # 处理标签信息
        label_list = []
        scale_list = []
        for tag in tag_list:
            span_list = tag.xpath('./span/text()')
            if span_list:
                label_list.append(span_list[0] if span_list else '')
                scale_list.append(span_list[-1] if len(span_list) > 1 else '')
            else:
                label_list.append('')
                scale_list.append('')

        # 确保所有列表长度一致
        lists = [name, salary, address, education, experience, com_name, label_list, scale_list, href_list, skills_list]
        min_length = min(len(lst) for lst in lists)
        for lst in lists:
            lst[:] = lst[:min_length]

        # 插入数据库
        select_sql = 'SELECT href FROM job_data'
        cur.execute(select_sql)
        href_list_mysql = [x[0] for x in cur.fetchall()]

        insert_sql = '''INSERT INTO job_data(name, salary, place, education, experience, company, label, scale, href, key_word, required_skills) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''

        for i in range(min_length):
            href = href_list[i].split('?')[0]
            if href not in href_list_mysql:
                # 确保 skills_list 有足够的元素
                required_skills = skills_list[i] if i < len(skills_list) else ''
                data = (name[i], salary[i], address[i], education[i], experience[i], com_name[i], label_list[i], scale_list[i], href, url.split('kw=')[-1].split('&')[0], required_skills)
                try:
                    cur.execute(insert_sql, data)
                    conn.commit()
                    print(f'插入数据成功: {name[i]}')
                except Exception as e:
                    print(f'插入数据失败: {e}')
                    conn.rollback()
            else:
                print(f'数据已存在，跳过: {href}')

    except Exception as e:
        print(f'爬取页面 {url} 失败: {e}')
    finally:
        cur.close()
        conn.close()
        driver.quit()


def get_mysql():
    """
    连接MySQL数据库
    :return: 数据库连接和游标
    """
    try:
        conn = pymysql.connect(
            host='localhost',
            port=3306,
            user='root',
            passwd='123456',
            database='recommend_job',
            autocommit=True,
            charset='utf8mb4'
        )
        cur = conn.cursor()
        return conn, cur
    except Exception as e:
        print(f'连接数据库失败: {e}')
        return None, None


if __name__ == '__main__':
    lieSpider('java', '北京', '1')

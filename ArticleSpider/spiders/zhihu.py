# -*- coding: utf-8 -*-
import scrapy
import re
import requests
import json
import datetime
import time

from urllib import parse
# py2中叫urlparse  直接import
from scrapy.loader import ItemLoader
from ..items import ZhihuAnswerItem, ZhihuQuestionItem


class ZhihuSpider(scrapy.Spider):
    # session代表的是某一次链接
    # session = requests.session()

    name = 'zhihu'
    allowed_domains = ['www.zhihu.com']
    start_urls = ['https://www.zhihu.com/']
    # question的第一页answer请求url
    start_answer_url = "https://www.zhihu.com/api/v4/questions/{0}/answers?sort_by=default&include=data%5B%2A%5D.is_normal%2Cis_sticky%2Ccollapsed_by%2Csuggest_edit%2Ccomment_count%2Ccollapsed_counts%2Creviewing_comments_count%2Ccan_comment%2Ccontent%2Ceditable_content%2Cvoteup_count%2Creshipment_settings%2Ccomment_permission%2Cmark_infos%2Ccreated_time%2Cupdated_time%2Crelationship.is_author%2Cvoting%2Cis_thanked%2Cis_nothelp%2Cupvoted_followees%3Bdata%5B%2A%5D.author.is_blocking%2Cis_blocked%2Cis_followed%2Cvoteup_count%2Cmessage_thread_token%2Cbadge%5B%3F%28type%3Dbest_answerer%29%5D.topics&limit={1}&offset={2}"
    headers = {
        'HOST': 'www.zhihu.com',
        'Referer': 'https://www.zhihu.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0',
    }
    # 这是Spider类的一个参数
    custom_settings = {
        "COOKIES_ENABLED": True     # 设置使用cookies，它会覆盖settings的值
    }
    def parse(self, response):
        # 提取出html中的所有url,并跟踪这些url近一步爬取
        # 如果url格式为 question\xxx 就下载之后直接进入解析函数
        all_urls = response.css('a::attr(href)').extract()
        all_urls = [parse.urljoin(response.url, url) for url in all_urls]
        all_urls = filter(lambda x: True if x.startswith('https') else False, all_urls)
        for url in all_urls:
            match_obj = re.match('(.*zhihu.com/question/(\d+))(/|$).*', url)
            if match_obj:
                # 如果提取到question相关的页面,则下载后交由提取函数进行提取
                requests_url = match_obj.group(1)
                # question_id = match_obj.group(2)
                yield scrapy.Request(requests_url, headers=self.headers, callback=self.parse_question)
            # break  # 调试
            else:
                # 如果不是question页面,则近一步跟踪.....
                yield scrapy.Request(url, headers=self.headers, callback=self.parse)
                # pass    # 调试

    def parse_question(self, response):
        # 处理question页面,从页面中提取具体的question item
        # 处理新版本,但是目前好像就只有新版本,所以不像教程内容一样做旧版本的处理
        match_obj = re.match('(.*zhihu.com/question/(\d+))(/|$).*', response.url)
        if match_obj:
            question_id = int(match_obj.group(2))
        item_loader = ItemLoader(item=ZhihuQuestionItem(), response=response)
        item_loader.add_css('title', '.QuestionHeader-title::text')
        item_loader.add_css('content', '.QuestionHeader-detail')
        item_loader.add_value('url', response.url)
        item_loader.add_value('zhihu_id', question_id)
        item_loader.add_css('answer_num', 'h4.List-headerText span::text')
        # item_loader.add_css('comments_num', '.QuestionHeader-Comment button::text')
        item_loader.add_css('comments_num', '.QuestionHeader-Comment .Button::text')
        item_loader.add_css('watch_user_num', '.NumberBoard-value::text')
        item_loader.add_css('topics', '.TopicLink .Popover div::text')

        # 这还没写create_time 写好之后item里面的sql也要加------------------------------
        question_item = item_loader.load_item()
        yield scrapy.Request(self.start_answer_url.format(question_id, 20, 0), headers=self.headers, callback=self.parse_answer)
        yield question_item     # 调试

    def parse_answer(self, response):
        # 处理question的answer
        ans_json = json.loads(response.text)
        is_end = ans_json['paging']['is_end']
        # totals_answer = ans_json['paging']['totals']
        next_url = ans_json['paging']['next']
        # 提取answer的具体字段
        for answer in ans_json['data']:
            answer_item = ZhihuAnswerItem()
            answer_item['zhihu_id'] = answer['id']
            answer_item['url'] = answer['url']
            answer_item['question_id'] = answer['question']['id']
            answer_item['author_id'] = answer['author']['id'] if 'id' in answer['author'] else None
            answer_item['content'] = answer['content'] if 'content' in answer else None
            answer_item['praise_nums'] = answer['voteup_count']
            answer_item['comments_num'] = answer['comment_count']
            answer_item['create_time'] = answer['created_time']
            answer_item['crawl_time'] = datetime.datetime.now()
            answer_item['update_time'] = answer['updated_time']
            yield answer_item
        if not is_end:
            yield scrapy.Request(next_url, headers=self.headers, callback=self.parse_answer)


    def start_requests(self):
        return [scrapy.Request('https://www.zhihu.com/#signin', headers=self.headers, callback=self.login)]

    def login(self, response):
        response_text = response.text
        match_obj = re.match('.*name="_xsrf" value="(.*?)"', response_text, re.DOTALL)
        xsrf = ''
        if match_obj:
            xsrf = match_obj.group(1)
        if xsrf:
            post_url = "https://www.zhihu.com/login/phone_num"  # 这条干嘛的
            post_data = {
                "_xsrf": xsrf,
                "password": 'zhHAN886158',
                # "captcha_type":'en',
                "captcha": '',
                "phone_num": '18659305689'
            }
            import time
            t = str(int(time.time() * 1000))
            captcha_url = 'https://www.zhihu.com/captcha.gif?r={0}&type=login&lang=en'.format(t)

            yield scrapy.Request(captcha_url, headers=self.headers, meta={"post_data": post_data}, callback=self.login_after_captcha)



    def login_after_captcha(self, response):
        '''
            在请求验证码的时候,在这里不能使用session和request,所以要保证请求的会话是在同一次.
        '''
        with open('captcha.jpg', 'wb') as f:
            f.write(response.body)
            f.close()
        from PIL import Image
        try:
            im = Image.open('captcha.jpg')
            im.show()
            im.close()
        except Exception:
            pass
        captcha = input("输入验证码").strip()
        post_data = response.meta.get("post_data", {})
        post_data['captcha'] = captcha
        return [scrapy.FormRequest(
            url='https://www.zhihu.com/login/phone_num',
            formdata=post_data,
            headers=self.headers,
            callback=self.check_login,
        )]

    def check_login(self, response):
        '''验证服务器返回数据判断是否成功'''
        text_json = json.loads(response.text)
        if 'msg' in text_json and text_json['msg'] == '登录成功':
            for url in self.start_urls:
                yield scrapy.Request(url, dont_filter=True, headers=self.headers)


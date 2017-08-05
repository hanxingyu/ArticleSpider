# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy
import datetime
import re
from ArticleSpider.settings import SQL_DATE_FORMAT, SQL_DATETIME_FORMAT
from scrapy.loader import ItemLoader
from scrapy.loader.processors import MapCompose, TakeFirst, Join, Identity
from ArticleSpider.utils.common import extract_num


class ArticlespiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


def add_jobbole(value):
    return value+'-han'


def get_nums(value):
    match_re = re.match('.?(\d+).*', value)
    if match_re:
        nums = int(match_re.group(1))
    else:
        nums = 0
    return nums


def date_convert(value):
    try:
        create_date = datetime.datetime.strptime(value, '%Y/%m/%d').date()
    except Exception as e:
        create_date = datetime.datetime.now().date()
    return create_date


def remove_comments_tags(value):
    """tags里有可能出现 评论 这个函数就是专门去除评论二字"""
    value.replace('评论', '')
    return value


class ArticleItemLoader(ItemLoader):
    """重载ItemLoader,这样有些参数就可以不用那么辛苦的写了"""
    # default_output_processor = Identity(),把默认的改成这个,就不需要每次都写了
    default_output_processor = TakeFirst()


class JobBoleArticleItem(scrapy.Item):
    title = scrapy.Field(
        # input_processor可以预处理之后再传递
        # MapCompose()内可以传递任意个函数,他会把值传递到函数内(此处是add_jobbole)
        # input_processor=MapCompose(add_jobbole)
        input_processor=MapCompose(lambda x: x+'-Jobbole', add_jobbole)
    )
    create_date = scrapy.Field(
        # 可以将str转换成我们想要的date格式
        input_processor=MapCompose(date_convert),
        # 默认生成的是一个list,把他转换成第一个元素,就不会是list了,因为重载了ItemLoader,所以不用改
        # output_processor=TakeFirst()
    )
    url = scrapy.Field()
    url_object_id = scrapy.Field()
    front_image_path = scrapy.Field()
    front_image_url = scrapy.Field(
        output_processor=Identity()
    )
    praise_nums = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    comment_nums = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    tags = scrapy.Field(
        input_processor=MapCompose(remove_comments_tags),
        # 使用join方法,
        output_processor=Join(',')
    )
    fav_nums = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    content = scrapy.Field()

    def get_insert_sql(self):
        insert_sql = """insert into jobbole_article(title,url,create_date,url_object_id,fav_nums,praise_nums,comment_nums,tags,content) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        params = (self['title'], self['url'], self['create_date'], self['url_object_id'], self['fav_nums'], self['praise_nums'],
                  self['comment_nums'], self['tags'], self['content'])
        return insert_sql, params


class  ZhihuQuestionItem(scrapy.Item):
    """知乎的问题"""
    zhihu_id = scrapy.Field()
    topics = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    answer_num = scrapy.Field()
    comments_num = scrapy.Field()
    watch_user_num = scrapy.Field()
    click_num = scrapy.Field()
    crawl_time = scrapy.Field()

    def get_insert_sql(self):
        # 插入知乎question表的sql语句
        insert_sql = """
            insert into zhihu_question(zhihu_id, topics, url, title, content, answer_num, comments_num,
              watch_user_num, click_num, crawl_time
              )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE content=VALUES(content), answer_num=VALUES(answer_num), comments_num=VALUES(comments_num),
              watch_user_num=VALUES(watch_user_num), click_num=VALUES(click_num)
        """
        zhihu_id = self["zhihu_id"][0]
        topics = ",".join(self["topics"])
        url = self["url"][0]
        title = "".join(self["title"])
        content = "".join(self["content"])
        answer_num = extract_num("".join(self["answer_num"]))
        comments_num = extract_num("".join(self["comments_num"]))

        if len(self["watch_user_num"]) == 2:
            watch_user_num = int(self["watch_user_num"][0])
            click_num = int(self["watch_user_num"][1])
        else:
            watch_user_num = int(self["watch_user_num"][0])
            click_num = 0

        crawl_time = datetime.datetime.now().strftime(SQL_DATETIME_FORMAT)
        params = (zhihu_id, topics, url, title, content, answer_num, comments_num,
                  watch_user_num, click_num, crawl_time)
        return insert_sql, params


class ZhihuAnswerItem(scrapy.Item):
    # 知乎的问题回答item
    zhihu_id = scrapy.Field()
    url = scrapy.Field()
    question_id = scrapy.Field()
    author_id = scrapy.Field()
    content = scrapy.Field()
    praise_nums = scrapy.Field()
    comments_num = scrapy.Field()
    create_time = scrapy.Field()
    update_time = scrapy.Field()
    crawl_time = scrapy.Field()

    def get_insert_sql(self):
        #插入知乎answer表的sql语句
        # DUPLICATE KEY UPDATE 是说主键冲突的情况下更新下面的数据，这种用法是mysql特有的
        insert_sql = """
            insert into zhihu_answer(zhihu_id, url, question_id, author_id, content, praise_nums, comments_num,
              create_time, update_time, crawl_time
              ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
              ON DUPLICATE KEY UPDATE content=VALUES(content), comments_num=VALUES(comments_num), praise_nums=VALUES(praise_nums),
              update_time=VALUES(update_time)
        """
        create_time = datetime.datetime.fromtimestamp(self["create_time"]).strftime(SQL_DATETIME_FORMAT)
        update_time = datetime.datetime.fromtimestamp(self["update_time"]).strftime(SQL_DATETIME_FORMAT)
        params = (
            self["zhihu_id"], self["url"], self["question_id"],
            self["author_id"], self["content"], self["praise_nums"],
            self["comments_num"], create_time, update_time,
            self["crawl_time"].strftime(SQL_DATETIME_FORMAT),
        )

        return insert_sql, params


class LagouJobItemLoader(ItemLoader):
    """重载ItemLoader,这样有些参数就可以不用那么辛苦的写了"""
    # default_output_processor = Identity(),把默认的改成这个,就不需要每次都写了
    default_output_processor = TakeFirst()


class LagouJobItem(scrapy.Item):
    """拉勾网职位信息"""
    url = scrapy.Field()
    url_object_id = scrapy.Field()
    title = scrapy.Field()
    salary = scrapy.Field()
    job_city = scrapy.Field()
    work_years = scrapy.Field()
    degree_need = scrapy.Field()
    job_type = scrapy.Field()
    publish_time = scrapy.Field()
    tags = scrapy.Field()
    job_advantage = scrapy.Field()
    job_desc = scrapy.Field()
    job_addr = scrapy.Field()
    company_url = scrapy.Field()
    company_name = scrapy.Field()
    crawl_time = scrapy.Field()
    crawl_update_time = scrapy.Field()  # 老师木有这个
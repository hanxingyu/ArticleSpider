# -*- coding: utf-8 -*-
import codecs
import json
import MySQLdb
# import后面可以跟. from xx import 后面不能跟.
import MySQLdb.cursors
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exporters import JsonItemExporter
# 提供异步导入数据库
from twisted.enterprise import adbapi


# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html


class ArticlespiderPipeline(object):
    def process_item(self, item, spider):
        return item


class JsonWithEncodingPipeline:
    """
    自定义json文件的导出
    取代ArticlespiderPipeline,让数据保存到json
    """

    def __init__(self):
        self.file = codecs.open('article.json', 'w', encoding='utf8')

    def process_item(self, item, spider):
        lines = json.dumps(dict(item), ensure_ascii=False) + '\n'
        self.file.write(lines)
        return item

    def spider_close(self, spider):
        self.file.close()


class MysqlPipeline:
    """采用同步的机制写入数据库,下面那个是异步的写法,然后配置到setting中就可以调用相应的方法了"""

    def __init__(self):
        self.conn = MySQLdb.connect('127.0.0.1', 'root', 'root', 'article_spider', charset='utf-8', use_unicode=True)
        self.cursor = self.conn.cursor()

    def process_item(self, item, spider):
        """后期爬取的数据变多,插入速度将跟不上python的解析速度."""
        insert_sql = """
            insert into jobbole_article(title,url,create_date,url_object_id,fav_nums,front_image_path,front_image_url,praise_nums,comment_nums,tags,content)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        self.cursor.execute(insert_sql,
                            (item['title'], item['url'], item['create_date'], item['url_object_id'], item['fav_nums'],item['front_image_path'],item['front_image_url'],item['praise_nums'],item['comment_nums'],item['tags'],item['content']))
        # 不知道这个commit是干嘛的
        self.conn.commit()


class MysqlTwistedPipeline:
    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_settings(cls, settings):
        """该方法的名称是固定的"""
        # dict的key是固定写法和mysql connections里面的要一样
        dbparms = dict(
            host=settings['MYSQL_HOST'],
            db=settings['MYSQL_DBNAME'],
            user=settings['MYSQL_USER'],
            passwd=settings['MYSQL_PASSWORD'],
            charset='utf8',
            cursorclass=MySQLdb.cursors.DictCursor,
            use_unicode=True,
        )

        dbpool = adbapi.ConnectionPool('MySQLdb', **dbparms)
        return cls(dbpool)

    def process_item(self, item, spider):
        # 目前只支持关系类型的数据库
        # 使用twisted将mysql插入变成异步执行,异步发生错误也无法及时处理.
        query = self.dbpool.runInteraction(self.do_insert, item)
        # 错误处理
        query.addErrback(self.handle_error, item, spider) # 处理异常

    def handle_error(self, failure, item, spider):
        # 处理异步插入的异常
        # print(failure)
        pass

    def do_insert(self, cursor, item):
        # 执行具体的插入
        # 根据不同的item构建不同的sql语句并插入到mysql中
        insert_sql, params = item.get_insert_sql()
        cursor.execute(insert_sql, params)


class JsonExproterPipeline:
    """
    调用scrapy提供的json export导出json文件
    """

    def __init__(self):
        self.file = open('articleexport.json', 'wb')
        self.exporter = JsonItemExporter(self.file, encoding='utf-8', ensure_ascii=False)
        self.exporter.start_exporting()

    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item


# 重写这个类,让他有更多的功能,可以得到本地图片的path路径
class ArticleImagePipeline(ImagesPipeline):
    def item_completed(self, results, item, info):
        if 'front_image_path' in item:
            for ok, value in results:
                image_file_path = value['path']
            item['front_image_path'] = image_file_path
        return item

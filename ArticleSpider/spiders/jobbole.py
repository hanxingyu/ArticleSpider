# -*- coding: utf-8 -*-
import scrapy
import re
import datetime

from scrapy.http import Request
from urllib import parse
from ArticleSpider.items import JobBoleArticleItem, ArticleItemLoader
from ArticleSpider.utils.common import get_md5
# 便于后期代码维护
from scrapy.loader import ItemLoader


class JobboleSpider(scrapy.Spider):
    name = 'jobbole'
    allowed_domains = ['blog.jobbole.com']
    start_urls = ['http://blog.jobbole.com/all-posts/']

    def parse(self, response):
        """
        1、获取文章列表页中的文字url，并交给scrapy下载后进行解析
        2、获取下一页的url并交给scrapy进行下载，下载完成后交给parse
        :param response: 
        :return: 
        """
        # 解析列表页中的所有文字url并交给scrapy下载后并解析
        post_nodes = response.css('.grid-8 .floated-thumb .post-thumb a')
        for post_node in post_nodes:
            # extract_first() 相当于extract[0]只是在extract没有值的时候不会报错
            # extract_first("")表示默认为空
            image_url = post_node.css('img::attr(src)').extract_first("")
            post_url = post_node.css('::attr(href)').extract_first("")
            # Request(url=post_url, callback=self.parse_detaill)
            # urljoin拼接url,若post_url内没有域名,则会从response.url提取出域名,进行拼接
            yield Request(url=parse.urljoin(response.url, post_url), meta={'front_image_url': image_url}, callback=self.parse_detaill)
        # 提取下一页并交给scrapy进行下载
        # 去掉class的空格代表两个class是同级的 在一起的样式
        next_urls = response.css('.next.page-numbers::attr(href)').extract_first('')
        if next_urls:
            yield Request(url=parse.urljoin(response.url, post_url), callback=self.parse)

    def parse_detaill(self, response):
        """
        提取文章的具体字段
        :param response: 
        :return: 
        """
        article_item = JobBoleArticleItem()
        # ------------------------用xpath解析------------------------------------
        # 这里的下标是从1开始的，不是从0开始的
        # firefox和chrome复制的xpath不一定一样，检查和源码的html结构也不一定一样！
        # 因为检查的有可能是有js生成的
        # re_selector = response.xpath('/html/body/div[1]/div[2]/div[1]/div[1]')
        # 调用text()函数可以让h1标签消失，只显示里面的数据
        # re_selector = response.xpath('//*[@id="post-111187"]/div[1]/h1/text()')
        # title = response.xpath('//*[@class="entry-header"]/h1/text()')
        # create_date = response.xpath('//p[@class="entry-meta-hide-on-mobile"]/text()').extract()[0].strip()
        # praise_nums = response.xpath('//span[contains(@class,"vote-post-up")]/h10/text()').extract()[0]
        # # 点赞数
        # fav_nums = response.xpath('//span[contains(@class,"bookmark-btn")]/text()').extract()[0]
        # match_re = re.match('.?(\d+).*', fav_nums)
        # if match_re:
        #     fav_nums = match_re.group(1)
        # # 评论数
        # comment_nums = response.xpath('//a[@href="#article-comment"]/span/text()').extract_first()
        # # extract_first()的作用是防止有时候数组没有值，取[0]会报错。
        # match_re = re.match('.?(\d+).*', comment_nums)
        # if match_re:
        #     comment_nums = match_re.group(1)
        # content = response.xpath('//div[@class="entry"]').extract()[0]
        # tag_list = response.xpath("//p[@class='entry-meta-hide-on-mobile']/a/text()").extract()
        # tag_list = [i for i in tag_list if not i.strip().endswith("评论")]
        # tags = ",".join(tag_list)


        # -------------通过css选择器解析-----------------------------
        front_image_url = response.meta.get('front_image_url', '')  # 文章封面图
        title = response.css('.entry-header h1::text').extract_first()
        create_date = response.css('.entry-meta-hide-on-mobile::text').extract_first().strip().replace(r'·', '').strip()
        praise_nums = response.css('span.bookmark-btn::text').extract_first().strip()
        match_re = re.match('.?(\d+).*', praise_nums)
        if match_re:
            praise_nums = int(match_re.group(1))
        else:
            praise_nums = 0
        fav_nums = int(response.css('span.vote-post-up h10::text').extract_first().strip())
        # 评论数
        comment_nums = response.css('a[href="#article-comment"] span::text').extract_first().strip()
        match_re = re.match('.?(\d+).*', comment_nums)
        if match_re:
            comment_nums = int(match_re.group(1))
        else:
            comment_nums = 0
        content = response.css('div .entry').extract_first().strip()
        tag_list = response.css(".entry-meta-hide-on-mobile a::text").extract()
        tag_list = [i for i in tag_list if not i.strip().endswith("评论")]
        tags = ",".join(tag_list)

        # 这个get_md5是自己定义的函数
        article_item['url_object_id'] = get_md5(response.url)
        article_item['title'] = title
        article_item['url'] = response.url
        try:
            create_date = datetime.datetime.strptime(create_date, '%Y/%m/%d').date()
        except Exception as e:
            create_date = datetime.datetime.now().date()
        article_item['create_date'] = create_date
        article_item['front_image_url'] = [front_image_url]
        article_item['praise_nums'] = praise_nums
        article_item['comment_nums'] = comment_nums
        article_item['tags'] = tags
        article_item['fav_nums'] = fav_nums
        article_item['content'] = content
        # 通过item_loader加载item,这样代码的可维护性大大增加
        # ItemLoader是默认的,ArticleItemLoader是自己重载的类.
        # item_loader = ItemLoader(item=JobBoleArticleItem(),response=response)
        item_loader = ArticleItemLoader(item=JobBoleArticleItem(),response=response)
        item_loader.add_css('title', '.entry-header h1::text')
        item_loader.add_value('url', response.url)
        item_loader.add_value('url_object_id', get_md5(response.url))
        item_loader.add_css('create_date', '.entry-meta-hide-on-mobile::text')
        item_loader.add_value('front_image_url', front_image_url)
        item_loader.add_css('fav_nums', 'span.vote-post-up h10::text')
        item_loader.add_css('comment_nums', 'a[href="#article-comment"] span::text')
        item_loader.add_css('praise_nums', 'span.bookmark-btn::text')
        item_loader.add_css('tags', '.entry-meta-hide-on-mobile a::text')
        item_loader.add_css('content', 'div .entry')

        # 调用此方法,才会将这些规则解析,解析之后生成的就是item对象
        article_item = item_loader.load_item()  # 得到的都是list,要解决此问题可以在item中scrapy.Field()添加参数
        # yield会传到pipelines,要让他生效需要在setting中开启item_pipelines
        yield article_item
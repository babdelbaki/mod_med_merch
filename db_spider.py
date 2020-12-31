import re
import statistics

from twisted.internet import reactor
import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.exceptions import DropItem
from scrapy.exceptions import NotConfigured
from scrapy.settings import Settings

from datetime import date

import pandas as pd
import MySQLdb
from sqlalchemy import create_engine

PATH = "/home/bakichu77/scraper/20200915/youtube/youtube/data/"

def round_1000(views):
    # rounds view count to nearest 1,000 (divides by 1,000)
    # e.g. 14602 --> 15
    try:
        ans = int(round(float(views) / 1000))
    except:
        ans = "ERR"
    return ans

def calculate_money(views):
    # 0.x% of viewers (views in thousands)
    proportion = 5

    # cut per shirt (on average, USD)
    shirt_price = 6.2

    try:
        ans = int(float(views) * proportion * shirt_price)
    except:
        ans = "ERR"
    return ans

class YoutubePipeline:
    def process_item(self, item, spider):
        print(2)
        try:
            rounded_views = round_1000(item["med_views"])
            proj_earnings = calculate_money(rounded_views)
            # set up this way to add insertion of table name as a variable
            # insert into two tables: mega table and respective scraper table
            tables = ["all_scrapers", spider.table]
            for table in tables:
                sql = "INSERT INTO %s(`ID`, `Link`, `Name`, `Subscribers`, `Num Videos`, `Median Views`, `Projected Earnings`, `Genre`, `Date Updated`) " \
                        "VALUES(%%s, %%s, %%s, %%s, %%s, %%s, %%s, %%s, %%s)" \
                        "ON DUPLICATE KEY UPDATE Link = %%s, Name = %%s, Subscribers = %%s,"  \
                        "`Num Videos` = %%s, `Median Views` = %%s, `Projected Earnings` = %%s, `Genre` = %%s, `Date Updated` = %%s" % table
                self.cursor.execute(sql,
                    (
                        item["cc_id"], item["url"], item["name"], item["subscribers"],
                        item["num_videos"], rounded_views, proj_earnings, item["genre"], item["date_updated"],
                        # for update
                        item["url"], item["name"], item["subscribers"],
                        item["num_videos"], rounded_views, proj_earnings, item["genre"], item["date_updated"]
                    )
                )
                self.conn.commit()
        except BaseException as error:
            print('An exception occurred: {}'.format(error))
        print(3)

        return item

    def open_spider(self, spider):
        self.db = "redacted"
        self.user = "redacted"
        self.passwd = "redacted"
        self.host = "redacted"

        self.conn = MySQLdb.connect(db=self.db,
                                    user=self.user, passwd=self.passwd,
                                    host=self.host,
                                    charset='utf8', use_unicode=True)
        self.cursor = self.conn.cursor()
        print("SPIDER OPENED")

    def close_spider(self, spider):
        # batch update of respective table
        # this allows spiders to update multiple tables
        try:
            # update respective table from all_scrapers if date updated is greater than the previous date
            # update name, subscribers, num videos, median views, projected earnings, and date updated
            sql = "UPDATE %s t JOIN all_scrapers s on t.id = s.id " \
                "SET t.`Name` = s.`Name`, t.`Num Videos` = s.`Num Videos`, " \
                "t.`Median Views` = s.`Median Views`, t.`Projected Earnings` = s.`Projected Earnings`, " \
                "t.`Date Updated` = s.`Date Updated`, t.`Genre` = s.`Genre` " \
                "WHERE s.`Date Updated` > t.`Date Updated`" % spider.table
            self.cursor.execute(sql)
            self.conn.commit()

            # also update the contact info table
            sql = "UPDATE contact_info t JOIN all_scrapers s on t.id = s.id " \
                "SET t.`NAME` = s.`Name`, t.`Num Videos` = s.`Num Videos`, " \
                "t.`Median Views` = s.`Median Views`, t.`Projected Earnings` = s.`Projected Earnings`, " \
                "t.`Date Updated` = s.`Date Updated`, t.`Genre` = s.`Genre` " \
                "WHERE s.`Date Updated` > t.`Date Updated` OR t.`Date Updated` IS NULL"
            self.cursor.execute(sql)
            self.conn.commit()

            # update the influence.cards contact info table
            sql = "UPDATE contacts_newcontactinfo t JOIN all_scrapers s on t.id = s.id " \
                "SET t.`Channel Name` = s.`Name`, t.`Num Videos` = s.`Num Videos`, " \
                "t.`Median Views` = s.`Median Views`, t.`Projected Earnings` = s.`Projected Earnings`, " \
                "t.`Date Updated` = s.`Date Updated`, t.`Genre` = s.`Genre` " \
                "WHERE s.`Date Updated` > t.`Date Updated` OR t.`Date Updated` IS NULL"
            self.cursor.execute(sql)
            self.conn.commit()
        except BaseException as error:
            print('An exception occurred: {}'.format(error))


        self.conn.close()
        print("CLOSE SPIDER")

class YoutubeItem(scrapy.Item):
    cc_id = scrapy.Field()
    url = scrapy.Field()
    name = scrapy.Field()
    genre = scrapy.Field()
    subscribers = scrapy.Field()
    num_videos = scrapy.Field()
    med_views = scrapy.Field()
    date_updated = scrapy.Field()

class ChannelCrawlerSpider(scrapy.Spider):
    name = "spider"

    def start_requests(self):
        number = getattr(self, 'number', None)
        self.table = getattr(self, "table", None)

        print(number)
        print(self.table)

        try:
            # open DB connection
            self.engine = create_engine("mysql://redacted?charset=utf8",
                    encoding = 'utf-8')
            self.engine.execute('SET NAMES utf8;')
            self.engine.execute('SET CHARACTER SET utf8;')
            self.engine.execute('SET character_set_connection=utf8;')

            # get IDs of channels updated today then close db connection
            today = date.today().strftime("%Y-%m-%d")
            sql = "SELECT id FROM all_scrapers WHERE `Date Updated` = '%s'" % today
            self.updated_today = pd.read_sql_query(sql, self.engine)
            self.engine.dispose()

            # generate links from channelcrawler to scraper
            self.base_url = "https://www.channelcrawler.com/eng/results/" + str(number) + "/page:"
            self.channel_crawler_links = []
            for i in range(1, 51):
                self.channel_crawler_links.append(self.base_url + str(i))

            for url in self.channel_crawler_links:
                print(url)
                yield scrapy.Request(url, self.parse)
        except BaseException as error:
            print('An exception occurred: {}'.format(error))



    def parse(self, response):
        # extract channel links from channelcrawler page, convert to video pages link
        print(0)
        links = redacted
        links = [link + "/videos" for link in links]

        # get unique id from link with regex, remove if they were updated today
        try:
            for link in list(links):
                cc_id = re.findall(redacted)[0]

                if cc_id in self.updated_today.values:
                    print("removed " + link)
                    links.remove(link)
        except BaseException as error:
            print('An exception occurred: {}'.format(error))

        # get list of genres then pass to next level of scraper (easier to access here)
        # remove unnecessary html tags that get picked up
        genres = response.xpath('redacted').getall()
        genres = [genre for genre in genres if genre != "Example Video:"]

        # pass every channel link/corresponding genre to channel parser
        try:
            for link, genre in zip(links, genres):
                yield response.follow(link, self.parse_channel, cb_kwargs = dict(genre = genre))
        except BaseException as error:
            print('An exception occurred: {}'.format(error))

    def parse_channel(self, response, genre):
        # extracts median view count from last 10 (or fewer) videos,
        # number subscribers, channel name, channel link (about page),
        # channel id (unique identifier)
        # yields item with this info which is written to database

        print(1)
        # extract view counts from youtube videos
        view_data = response.xpath("redacted").extract()[0]
        view_list = re.findall('redacted', view_data)
        view_list_cleaned = []

        # drop unnecessary items from view list (can pick up unnecessary html fragments
        # then format viewcount to appropriate number
        for view in view_list:
            if len(view) < 7:
                # convert k and m to thousands and millions
                if view[-1] == "K":
                    view_list_cleaned.append(float(view[0:-1]) * 1000)
                elif view[-1] == "M":
                    view_list_cleaned.append(float(view[0:-1]) * 1000000)
                else:
                    view_list_cleaned.append(float(view))

            if len(view_list_cleaned) == 10: break
        median_views = statistics.median(view_list_cleaned)
        number_of_videos = len(view_list_cleaned)

        # get channel name, subscriber count
        channel_data = str(response.body)
        #channel_name = re.findall('redacted', channel_data)[0]
        # new version added - less likely to pick up weird tags
        channel_name = response.xpath('redacted').get().replace("redacted", "")
        sub_count = re.findall('redacted', channel_data)[0]

        # convert k and m to thousands and millions
        if sub_count[-1] == "K":
            sub_count = float(sub_count[0:-1]) * 1000
        elif sub_count[-1] == "M":
            sub_count = float(sub_count[0:-1]) * 1000000

        # turn url into about page, extract content creator id number
        about_page = str(response.url).replace("/videos", "/about")
        cc_idn = re.findall('[c|channel|user]/(.+?)/', about_page)[0]

        print(cc_idn, channel_name, sub_count, about_page, number_of_videos, median_views, date.today().strftime("%Y-%m-%d"), sep = "\t")

        # try:
        # except BaseException as error:
        #    print('An exception occurred: {}'.format(error))

        item = YoutubeItem(
            cc_id = cc_idn,
            url = about_page,
            name = channel_name,
            genre = genre,
            subscribers = sub_count,
            num_videos = number_of_videos,
            med_views = median_views,
            date_updated = date.today().strftime("%Y-%m-%d")
        )

        yield(item)



if __name__ == "__main__":
    settings = Settings(values = {
        "AUTOTHROTTLE_ENABLED" : True,
        "AUTOTHROTTLE_START_DELAY" : 2,
        "AUTOTHROTTLE_MAX_DELAY" : 20,
        "ITEM_PIPELINES" : {
            '__main__.YoutubePipeline': 300,
        },
        "DOWNLOAD_DELAY" : 2,
        "CONCURRENT_REQUESTS" : 10,
        "CONCURRENT_REQUESTS_PER_DOMAIN" : 10
    })
    runner = CrawlerRunner(settings = settings)

    # run multiple spiders in parallel
    runner.crawl(ChannelCrawlerSpider, number = 4062, table = "unevaluated")
    runner.crawl(ChannelCrawlerSpider, number = 2394, table = "musicians")
    runner.crawl(ChannelCrawlerSpider, number = 191683, table = "all_genres")
    d = runner.join()
    d.addBoth(lambda _: reactor.stop())
    reactor.run()









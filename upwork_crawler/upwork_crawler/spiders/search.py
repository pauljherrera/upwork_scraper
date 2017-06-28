# -*- coding: utf-8 -*-
import django
django.setup()
import json
from time import sleep
import datetime as dt
import sys
import pytz

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.shell import inspect_response

from scrapy_djangoitem import DjangoItem

from data.models import m_tag, m_search, i_searchtag, d_fixedprice, i_searchaltertags
from data.models import d_hourlyrate, d_avghourlyrate



class m_tagItem(DjangoItem):
    django_model = m_tag

class m_searchItem(DjangoItem):
    django_model = m_search

class i_searchtagItem(DjangoItem):
    django_model = i_searchtag

class d_fixedpriceItem(DjangoItem):
    django_model = d_fixedprice

class d_hourlyrateItem(DjangoItem):
    django_model = d_hourlyrate

class i_searchaltertagsItem(DjangoItem):
    django_model = i_searchaltertags


class SearchSpider(CrawlSpider):
    name = 'search'
    allowed_domains = ['https://www.upwork.com']

    def __init__(self, time_limit='' , *args, **kwargs):
        super(SearchSpider, self).__init__(*args, **kwargs)
        self.pages = {}
        self.counter = 0
        self.timeLimit = time_limit if time_limit else dt.datetime.utcnow() - dt.timedelta(7)

        # Saving search date.
        m_search = m_searchItem()
        self.date = m_search.save()


    def start_requests(self):
        skills = ['javascript']
        for s in skills:
            self.pages["{}".format(s)] = 1
            url = 'https://www.upwork.com/o/jobs/browse/?page=1&q={}'.format(s)
            request = scrapy.Request(url=url, callback=self.parse, dont_filter=True)
            request.meta['skill'] = s
            yield request


    def parse(self, response):
        # inspect_response(response, self)
        skill = response.meta['skill']

        # Searching the Javascript fragment that contains the API response.
        hay = response.css('script')[4].extract()
        needle = json.loads(hay.split('var phpVars = ')[1].split('var angularCache')[0].strip()[:-1])
        jobs = needle['jobs']

        # Scraping.
        allJobs = set(i_searchtag.objects.all().values_list('jobTs', flat=True))
        tagId = m_tag.objects.filter(name=skill).first()
        for j in jobs:
            jobId = j['jobTs']
            if jobId not in allJobs:
                # Filling i_searchtag table.
                i_searchtag_item = i_searchtagItem()
                i_searchtag_item['id_m_tag'] = tagId
                i_searchtag_item['id_m_search'] = self.date
                i_searchtag_item['jobTs'] = j['jobTs']
                i_searchtag_item['experience_level'] = j['tierText'].split()[0]
                i_searchtag_item['proposals_number'] = j['proposalsTier']
                i_searchtag_item['total_spent'] = float(j['client']['totalSpent'])
                try:
                    i_searchtag_item['payment_verified'] = int(j['client']['paymentVerificationStatus'])
                except TypeError:
                    i_searchtag_item['payment_verified'] = 0
                i_searchtag_item['location'] = j['client']['location']['country']
                i_searchtag_item['feedback'] = round(float(j['client']['totalFeedback']), 1)
                i_searchtag_item['createdOn'] = dt.datetime.strptime(j['createdOn'], "%Y-%m-%dT%H:%M:%S+00:00").replace(tzinfo=pytz.UTC)
                search = i_searchtag_item.save()

                # Filling d_fixedprice and d_hourlyrate tables.
                if j['type'] == 1:
                    d_fixedprice_item = d_fixedpriceItem()
                    d_fixedprice_item['id_i_searchtag'] = search
                    d_fixedprice_item['budget'] = j['amount']['amount']
                    d_fixedprice_item.save()
                elif j['type'] == 2:
                    d_hourlyrate_item = d_hourlyrateItem()
                    d_hourlyrate_item['id_i_searchtag'] = search
                    d_hourlyrate_item['hours_per_week'] = j['engagement']
                    d_hourlyrate_item['duration'] = j['duration']
                    d_hourlyrate_item.save()

                # Filling i_searchaltertags table.
                if len(j['skills']) > 0:
                    for s in j['skills']:
                        print(s['name'])
                        print(m_tag.objects.filter(name=s['name']).first())
                        print(len(m_tag.objects.filter(name=s['name'])))
                        skillTag = s['name']
                        tagQuery = m_tag.objects.filter(name=skillTag)

                        # Saving in case it is a skill that isn't in the db.
                        if len(tagQuery) == 0:
                            skillTag = save_tag(skillTag).name

                        i_searchaltertags_item = i_searchaltertagsItem()
                        i_searchaltertags_item['id_m_tag'] = m_tag.objects.filter(name=skillTag).first()
                        i_searchaltertags_item['id_i_searchtag'] = search
                        i_searchaltertags_item.save()

                self.counter += 1

        # Getting last date of the current jobs list.
        lastTimeStr = jobs[-1]['createdOn']
        lastTime =  dt.datetime.strptime(lastTimeStr, "%Y-%m-%dT%H:%M:%S+00:00")

        # Recursive calls for next pages.
        if lastTime > self.timeLimit:
            self.pages["{}".format(skill)] += 1
            url = 'https://www.upwork.com/o/jobs/browse/?page={}&q={}'.format(self.pages["{}".format(skill)], skill)
            request = scrapy.Request(url=url, callback=self.parse, dont_filter=True)
            request.meta['skill'] = skill
            yield request
        else:
            print "\n{} job(s) added\n".format(self.counter)        


class TagsSpider(CrawlSpider):
    name = 'tags_finder'
    allowed_domains = ['https://www.upwork.com']
    
    def __init__(self, skill='scrapy', massive_search=False, *args, **kwargs):
        super(TagsSpider, self).__init__(*args, **kwargs)
        self.skills = [skill] if not massive_search\
                      else set(m_tag.objects.all().order_by('-pk').values_list('name', flat=True))

    def start_requests(self):
        urls = ['https://www.upwork.com/o/jobs/browse/?q=skills%3A%28{}%29&sort=create_time%2Bdesc'.format(s) 
                for s in self.skills]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)    

    def parse(self, response):
        # TODO: This 403 status handling doesn't work. 
        if response.status == 403:
            print "Letting Upwork rest..."
            sleep(600)
        else:
            # Getting the tags from the db.
            all_tags = set(m_tag.objects.all().values_list('name', flat=True))

            # Getting the search results.
            hay = response.css('script')[4].extract()
            needle = json.loads(hay.split('var phpVars = ')[1].split('var angularCache')[0].strip()[:-1])
            jobs = needle['jobs']

            # Collecting all the tags in the response.
            tags = []
            skills = [j['skills'] for j in jobs]
            for s in skills: tags.extend([skill['name'] for skill in s])
            tags = set(tags)

            #Saving tags in the django model
            counter = 0
            for t in [t for t in tags if t not in all_tags]:
                item = m_tagItem()
                item['name'] = t
                item.save()
                print "Tag \"{}\" added.".format(t)
                counter += 1

            # Reporting.
            print ""
            print "{} tag(s) added.".format(counter)
            print "The db has {} skill tags".format(m_tag.objects.count())
            print ""


def save_tag(tag):
    item = m_tagItem()
    item['name'] = tag
    return item.save()

# def uprint(*objects, sep=' ', end='\n', file=sys.stdout):
#     enc = file.encoding
#     if enc == 'UTF-8':
#         print(*objects, sep=sep, end=end, file=file)
#     else:
#         f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
#         print(*map(f, objects), sep=sep, end=end, file=file)


        
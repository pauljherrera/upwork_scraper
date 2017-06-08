# -*- coding: utf-8 -*-
import django
django.setup()
import json

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.shell import inspect_response

from scrapy_djangoitem import DjangoItem

from data.models import m_tag, m_search, i_searchtag, d_fixedprice
from data.models import	d_hourlyrate, d_avghourlyrate



class SearchTagItem(DjangoItem):
    django_model = m_tag


class SearchSpider(CrawlSpider):
    name = 'search'
    allowed_domains = ['https://www.upwork.com/o/jobs/browse/skill/']

    def start_requests(self):
    	skills = ['javascript']
    	urls = ['https://www.upwork.com/o/jobs/browse/?q=skills:({})&sort=create_time%2Bdesc'.format(s) for s in skills]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        print 'parsing'
        inspect_response(response, self)
        # Searching the Javascript fragment that contains the API response.
        hay = response.css('script')[4].extract()
        needle = json.loads(hay.split('var phpVars = ')[1].split('var angularCache')[0].strip()[:-1])
        jobs = needle['jobs']
        


class TagsSpider(CrawlSpider):
    name = 'tags_finder'
    allowed_domains = ['https://www.upwork.com']
    
    def __init__(self, skill='', massive_search=False, *args, **kwargs):
        super(TagsSpider, self).__init__(*args, **kwargs)
        self.skills = skills if not massive_search\
                             else set(m_tag.objects.all().order_by('-pk').values_list('name', flat=True))

    def start_requests(self):
        urls = ['https://www.upwork.com/o/jobs/browse/?q=skills%3A%28{}%29&sort=create_time%2Bdesc'.format(s) 
                for s in self.skills]

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)    

    def parse(self, response):
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
            item = SearchTagItem()
            item['name'] = t
            item.save()
            print "Tag \"{}\" added.".format(t)
            counter += 1

        # Reporting.
        print ""
        print "{} tag(s) added.".format(counter)
        print "The db has {} skill tags".format(m_tag.objects.count())
        print ""



        
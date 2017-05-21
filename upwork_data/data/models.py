# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class m_tag(models.Model):
	name = models.CharField(max_length=80)

class m_search(models.Model):
	date = models.DateField(auto_now_add=True)

class i_searchtag(models.Model):
	id_m_tag = models.ForeignKey(m_tag, related_name='i_searchtag')
	id_m_search = models.ForeignKey(m_search, related_name='i_searchtag')
	experience_level = models.CharField(max_length=50, choices=['Entry', 'Intermediate', 'Expert'])
	proposals_number = models.CharField(max_length=50)
	jobs_posted = models.IntegerField()
	hires_number = models.IntegerField()
	hire_rate = models.DecimalField(max_digits=5, decimal_places=2)
	total_spent = models.DecimalField(max_digits=12, decimal_places=2)
	payment_verified = models.IntegerField()
	location = models

class d_fixedprice(models.Model)
	id_i_searchtag = models.ForeignKey(i_searchtag, related_name='d_fixedprice')
	budget = models.DecimalField(max_digits=8, decimal_places=2)

class d_hourlyrate(models.Model)
	id_i_searchtag = models.ForeignKey(i_searchtag, related_name='d_hourlyrate')
	hours_per_week = models.CharField(max_length=80)
	duration = models.CharField(max_length=80)

class d_avghourlyrate(models.Model)
	id_i_searchtag = models.ForeignKey(i_searchtag, related_name='d_hourlyrate')
	rate = models.DecimalField(max_digits=6, decimal_places=2)
	hired_hours = models.IntegerField()


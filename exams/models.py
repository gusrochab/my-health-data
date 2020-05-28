from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
# from PIL import Image


class Exam(models.Model):
	title = models.CharField(max_length=200)
	description = models.TextField()
	image = models.ImageField(upload_to='exam_pics')
	text_from_img = models.TextField(blank=True)
	date_posted = models.DateTimeField(default=timezone.now)
	author = models.ForeignKey(User, on_delete=models.CASCADE)


	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse('exam-detail', kwargs={'pk': self.pk})

	# def save(self, *args, **kwargs):
	# 	super().save(*args, **kwargs)
	#
	# 	img = Image.open(self.image.path)
	# 	img.save(self.image.path)
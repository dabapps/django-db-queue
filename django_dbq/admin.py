from django.contrib import admin

# Register your models here.

from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'state', 'queue_name', 'priority', 'run_after')
#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.models import ArbiusImage
from django.db.models.functions import Length

# Apply the same filtering as in the views
valid_images = ArbiusImage.objects.annotate(
    prompt_length=Length('prompt')
).exclude(
    prompt__startswith="<|begin_of_text|>"
).exclude(
    prompt__startswith="<|end_of_text|>"
).exclude(
    prompt__startswith='{"System prompt"'
).exclude(
    prompt__startswith='{"MessageHistory"'
).exclude(
    prompt_length__gt=5000
).filter(is_accessible=True)

distinct_models = valid_images.filter(model_id__isnull=False).exclude(model_id='').values('model_id').distinct()

print("PRODUCTION DATABASE ANALYSIS:")
print("Total distinct models:", distinct_models.count())

unique_models = set()
for model in distinct_models:
    unique_models.add(model['model_id'])

print("Model IDs found:")
for i, model_id in enumerate(sorted(unique_models), 1):
    count = valid_images.filter(model_id=model_id).count()
    short_id = model_id[:8] + "..." + model_id[-8:]
    print(str(i) + ". " + short_id + " (" + str(count) + " images)")

null_models = valid_images.filter(model_id__isnull=True).count()
empty_models = valid_images.filter(model_id='').count()
print("Null model_id:", null_models)
print("Empty model_id:", empty_models)
print("Total valid images:", valid_images.count()) 
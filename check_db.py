import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arbius_gallery.settings')
django.setup()

from gallery.models import ArbiusImage

# Check images with model info
images_with_models = ArbiusImage.objects.filter(model_id__isnull=False)
print(f'Images with model info: {images_with_models.count()}')

# Check images with prompts
images_with_prompts = ArbiusImage.objects.filter(prompt__isnull=False)
print(f'Images with prompts: {images_with_prompts.count()}')

# Show some examples
print("\nExamples:")
for img in images_with_models[:5]:
    print(f'CID: {img.cid[:20]}...')
    print(f'  Model: {img.short_model_id}')
    print(f'  Prompt: {img.prompt or "None"}')
    print(f'  Input params: {img.input_parameters or "None"}')
    print() 
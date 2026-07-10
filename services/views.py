# views.py
import json
from django.http import JsonResponse
from .models import AuthorSpecial, Complex, KramItem, KramSection, Service

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache

@cache_page(60 * 5)
def services_get(request):
    def category(arr):
        dict = {"drinks": "Напої", "additional": "Додатково", "massagers": "Масажери", "snacks": "Снеки", "souvenirs": "Сувеніри"}
        arr["category"] = dict[arr["section"]]
        return arr


    return JsonResponse({
        "author_specials": list(
            AuthorSpecial.objects.values("id", "name")
        ),
        "complexes": list(
            Complex.objects.values("id", "name")
        ),
        "services": [
            {
                "id": s.id,
                "name": s.name,

                "types": list(s.types.values("id", "name")),
            }
            for s in Service.objects.prefetch_related("types").all()
        ],
        "kram": {
            section: list(map(category, list(
                KramItem.objects.filter(section=section).values("id", "name", 'section')
            )))
            for section in KramSection.values
        },
    })



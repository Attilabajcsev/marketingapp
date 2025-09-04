from django.urls import path
from .views import ingest_text, search


urlpatterns = [
    path("ingest/", ingest_text, name="vectorstore_ingest"),
    path("search/", search, name="vectorstore_search"),
]



from django.urls import path
from .views import ingest_text, search, chat, generate


urlpatterns = [
    path("ingest/", ingest_text, name="vectorstore_ingest"),
    path("search/", search, name="vectorstore_search"),
    path("chat/", chat, name="vectorstore_chat"),
    path("generate/", generate, name="vectorstore_generate"),
]



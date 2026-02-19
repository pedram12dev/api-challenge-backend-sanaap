from django.urls import path, include

urlpatterns = [
    path('users/', include(('apichallenge.users.urls', 'users'))),
    path('auth/', include(('apichallenge.authentication.urls', 'auth'))),
    path('documents/', include(('apichallenge.documents.urls', 'documents'))),
]

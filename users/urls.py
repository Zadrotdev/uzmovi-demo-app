from django.urls import path
from .serializers import SignUpSerializer
from .views import CreateUserView

urlpatterns = [
    path('signup/', CreateUserView.as_view(), name='signup'),
]
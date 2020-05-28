from django.urls import path
from .views import ExamDetailView, ExamCreateView, ExamUpdateView, ExamDeleteView, ExamListView, home
from . import views


urlpatterns = [
    path('', home, name='exam-home'),
    path('user/<str:username>', ExamListView.as_view(), name='exam-list'),
    path('exam/<int:pk>/', ExamDetailView.as_view(), name='exam-detail'),
    path('exam/new/', ExamCreateView, name='exam-create'),
    path('exam/<int:pk>/update/', ExamUpdateView.as_view(), name='exam-update'),
    path('exam/<int:pk>/delete/', ExamDeleteView.as_view(), name='exam-delete'),
    path('about/', views.about, name='exam-about'),
]




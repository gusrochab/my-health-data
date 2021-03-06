import logging
from django_q.tasks import async_task
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.urls import reverse
from django.http import HttpResponse
from .forms import ExamForm
from .models import Exam
from .exam_to_text import get_text

# logging.basicConfig(filename="views.log", level=logging.DEBUG,
#                    format='%(asctime)s:%(levelname)s:%(message)s')


def home(request):
    return render(request, 'exams/home.html')


class ExamListView(LoginRequiredMixin, ListView):
    model = Exam
    context_object_name = 'exams'
    paginate_by = 5

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Exam.objects.filter(author=user).order_by('-date_posted')


class ExamDetailView(DetailView):
    model = Exam


@login_required
def ExamCreateView(request):
    if request.method == 'POST':
        exam_form = ExamForm(data=request.POST, files=request.FILES)
        if exam_form.is_valid():
            instance = exam_form.save(commit=False)
            instance.author = request.user
            instance.save()
            async_task(get_text, instance)
            # TODO parse_text(text_from_image)
            messages.success(request, f'We are analyzing your exam.')
            return redirect(reverse('exam-list', kwargs={'username': request.user.username}))
        else:
            return HttpResponse("{}".format(exam_form.errors))
    else:
        exam_form = ExamForm()

    return render(request, 'exams/exam_form.html', {'form': exam_form})


class ExamUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Exam
    fields = ['title', 'description', 'image']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


class ExamDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Exam

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False

    def get_success_url(self):
        return "/"


def about(request):
    return render(request, 'exams/about.html', {'title': 'About'})







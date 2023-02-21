from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required(login_url='signin')
def index(request):

    return render(request, 'templates/home/home_index.html')

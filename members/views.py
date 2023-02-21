from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages


def index(request):

    return render(request, 'templates/members/member_index.html')


def signin(request):
    next_link = request.GET.get('next')
    if request.method == 'POST':

        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request=request, user=user)
            messages.success(request, f' Welcome {username} !!')
            if next_link:
                return redirect(next_link)
            else:
                return render(request, 'templates/members/member_index.html')
        else:
            messages.info(request, f'account done not exit')

    return render(request, 'templates/members/member_index.html', {'full_url': request.get_full_path()})

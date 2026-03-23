from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def index(request):
    return render(request, "index.html")  # landing page


def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect("dashboard")  # go to dashboard
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")


def signUp(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("signup")

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        messages.success(request, "Account created successfully")
        return redirect("login")

    return render(request, "signup.html")


@login_required
def dashboard(request):
    return render(request, "dashboard.html")

@login_required
def organizations(request):
    return render(request, "organisations.html")

@login_required
def tasks(request):
    return render(request, "task.html")


def logout_user(request):
    logout(request)
    return redirect("login")
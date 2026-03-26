from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Organization, Membership


def index(request):
    return render(request, "index.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect("dashboard")
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
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
        else:
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
    user_orgs = Organization.objects.filter(membership__user=request.user)
    return render(request, "dashboard.html", {
        "active_page": "dashboard",
        "organizations": user_orgs
    })


def is_big_four(user, organization):
    return Membership.objects.filter(
        user=user,
        organization=organization,
        role__in=["PRES", "VPI", "VPE", "SEC", "TRE"]
    ).exists()


@login_required
def organizations(request):
    user_orgs = Organization.objects.filter(membership__user=request.user)
    return render(request, "organizations.html", {
        "organizations": user_orgs,
        "active_page": "organizations"
    })


@login_required
def organization_detail(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    members = Membership.objects.filter(organization=org).select_related("user")
    is_president = Membership.objects.filter(
        user=request.user, organization=org, role="PRES"
    ).exists()

    return render(request, "organization_detail.html", {
        "org": org,
        "members": members,
        "is_president": is_president,
        "active_page": "organizations"
    })


@login_required
def create_organization(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        has_vp = request.POST.get("has_vp") == "on"
        logo = request.FILES.get("logo")

        org = Organization.objects.create(
            name=name,
            description=description,
            has_vp=has_vp,
            logo=logo,
            owner=request.user
        )
        Membership.objects.create(user=request.user, organization=org, role="PRES")
    return redirect("organizations")


@login_required
def add_member(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        return redirect("organizations")

    if request.method == "POST":
        username = request.POST.get("username")
        role = request.POST.get("role")
        try:
            user = User.objects.get(username=username)
            Membership.objects.create(user=user, organization=org, role=role)
        except User.DoesNotExist:
            pass

    return redirect("organizations")


@login_required
def remove_member(request, org_id, user_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        return redirect("organizations")

    Membership.objects.filter(organization=org, user_id=user_id).delete()
    return redirect("organizations")


@login_required
def tasks(request):
    user_orgs = Organization.objects.filter(membership__user=request.user)
    return render(request, "task.html", {
        "active_page": "tasks",
        "organizations": user_orgs
    })


def logout_user(request):
    logout(request)
    return redirect("login")


@login_required
def delete_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if request.method == "POST" and org.owner == request.user:
        org.delete()
    return redirect("organizations")
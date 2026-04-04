from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Organization, Membership, Task, Department


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


def is_president(user, organization):
    return Membership.objects.filter(
        user=user, organization=organization, role="PRES"
    ).exists()


def is_big_four(user, organization):
    return Membership.objects.filter(
        user=user,
        organization=organization,
        role__in=["PRES", "VP", "VPI", "VPE", "SEC", "TRE"]
    ).exists()


EXCLUSIVE_ROLES = ["VP", "VPI", "VPE", "SEC", "TRE"]


def role_is_taken(role, organization, exclude_membership_id=None):
    if role not in EXCLUSIVE_ROLES:
        return False
    qs = Membership.objects.filter(organization=organization, role=role)
    if exclude_membership_id:
        qs = qs.exclude(id=exclude_membership_id)
    return qs.exists()


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
    members = Membership.objects.filter(organization=org).select_related("user", "department")
    departments = Department.objects.filter(organization=org)
    user_is_big_four = is_big_four(request.user, org)
    user_is_president = is_president(request.user, org)

    # Members with no department assigned (role=MEM only)
    unassigned_members = members.filter(role="MEM", department__isnull=True)

    return render(request, "organization_detail.html", {
        "org": org,
        "members": members,
        "departments": departments,
        "unassigned_members": unassigned_members,
        "is_president": user_is_president,
        "is_big_four": user_is_big_four,
        "active_page": "organizations"
    })


@login_required
def create_organization(request):
    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description", "")
        has_two_vp = request.POST.get("has_two_vp") == "on"
        logo = request.FILES.get("logo")
        org = Organization.objects.create(
            name=name,
            description=description,
            has_two_vp=has_two_vp,
            logo=logo,
            owner=request.user
        )
        Membership.objects.create(user=request.user, organization=org, role="PRES")
    return redirect("organizations")


@login_required
def join_organization(request):
    if request.method == "POST":
        code = request.POST.get("invitation_code", "").strip().upper()
        try:
            org = Organization.objects.get(invitation_code=code)
        except Organization.DoesNotExist:
            messages.error(request, "Invalid invitation code. Please try again.")
            return redirect("organizations")

        if Membership.objects.filter(user=request.user, organization=org).exists():
            messages.error(request, "You are already a member of this organization.")
            return redirect("organizations")

        Membership.objects.create(user=request.user, organization=org, role="MEM")
        messages.success(request, f"You have successfully joined {org.name}!")
    return redirect("organizations")


@login_required
def edit_member_role(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_president(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        membership_id = request.POST.get("membership_id")
        role = request.POST.get("role")
        membership = get_object_or_404(Membership, id=membership_id, organization=org)

        if membership.role == "PRES":
            messages.error(request, "Cannot change the President's role.")
            return redirect("organization_detail", org_id=org_id)

        if role_is_taken(role, org, exclude_membership_id=membership.id):
            role_display = dict(Membership.ROLE_CHOICES).get(role, role)
            messages.error(request, f"The {role_display} position is already assigned to another member.")
            return redirect("organization_detail", org_id=org_id)

        # If promoted to executive, remove from department
        if role != "MEM":
            membership.department = None

        membership.role = role
        membership.save()
        messages.success(request, f"{membership.user.username}'s role updated to {dict(Membership.ROLE_CHOICES).get(role)}.")

    return redirect("organization_detail", org_id=org_id)


@login_required
def kick_member(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_president(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        membership_id = request.POST.get("membership_id")
        membership = get_object_or_404(Membership, id=membership_id, organization=org)

        if membership.role == "PRES":
            messages.error(request, "Cannot remove the President.")
            return redirect("organization_detail", org_id=org_id)

        username = membership.user.username
        membership.delete()
        messages.success(request, f"{username} has been removed from the organization.")

    return redirect("organization_detail", org_id=org_id)


@login_required
def create_department(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            messages.error(request, "Department name is required.")
            return redirect("organization_detail", org_id=org_id)

        if Department.objects.filter(organization=org, name__iexact=name).exists():
            messages.error(request, f"A department named '{name}' already exists.")
            return redirect("organization_detail", org_id=org_id)

        Department.objects.create(organization=org, name=name, description=description)
        messages.success(request, f"Department '{name}' has been created.")

    return redirect("organization_detail", org_id=org_id)


@login_required
def delete_department(request, org_id, dept_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        dept = get_object_or_404(Department, id=dept_id, organization=org)
        dept.delete()
        messages.success(request, f"Department '{dept.name}' has been deleted.")

    return redirect("organization_detail", org_id=org_id)


@login_required
def assign_department(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        membership_ids = request.POST.getlist("membership_ids")
        dept_id = request.POST.get("department_id")
        dept = get_object_or_404(Department, id=dept_id, organization=org)
        count = 0
        for membership_id in membership_ids:
            try:
                membership = Membership.objects.get(id=membership_id, organization=org, role="MEM")
                membership.department = dept
                membership.save()
                count += 1
            except Membership.DoesNotExist:
                pass
        if count > 0:
            messages.success(request, f"{count} member{'s' if count > 1 else ''} assigned to {dept.name}.")
        else:
            messages.error(request, "No members were selected.")
    return redirect("organization_detail", org_id=org_id)


@login_required
def remove_from_department(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        membership_ids = request.POST.getlist("membership_ids")
        if not membership_ids:
            single = request.POST.get("membership_id")
            if single:
                membership_ids = [single]
        count = 0
        for mid in membership_ids:
            try:
                membership = Membership.objects.get(id=mid, organization=org)
                membership.department = None
                membership.save()
                count += 1
            except Membership.DoesNotExist:
                pass
        if count > 0:
            messages.success(request, f"{count} member{{'s' if count > 1 else ''}} removed from their department.")

    return redirect("organization_detail", org_id=org_id)


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
def delete_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if request.method == "POST" and org.owner == request.user:
        org.delete()
    return redirect("organizations")


@login_required
def tasks(request):
    user_orgs = Organization.objects.filter(membership__user=request.user)
    return render(request, "task.html", {
        "active_page": "tasks",
        "organizations": user_orgs
    })


@login_required
def org_tasks(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not Membership.objects.filter(user=request.user, organization=org).exists():
        return redirect("tasks")

    members = Membership.objects.filter(organization=org).select_related("user")
    user_is_big_four = is_big_four(request.user, org)

    if user_is_big_four:
        org_task_list = Task.objects.filter(organization=org).select_related("assigned_to")
    else:
        org_task_list = Task.objects.filter(organization=org, assigned_to=request.user)

    status_columns = [
        ("TODO", "To Do", "bg-gray-400"),
        ("PROG", "In Progress", "bg-blue-400"),
        ("DONE", "Done", "bg-green-400"),
    ]

    departments = Department.objects.filter(organization=org)

    # Annotate each task with the assigned member's department name
    for task in org_task_list:
        membership = Membership.objects.filter(
            user=task.assigned_to, organization=org
        ).first()
        task.assigned_to_dept = membership.department.name if membership and membership.department else None

    return render(request, "org_tasks.html", {
        "org": org,
        "tasks": org_task_list,
        "members": members,
        "departments": departments,
        "is_big_four": user_is_big_four,
        "status_columns": status_columns,
        "active_page": "tasks"
    })


@login_required
def add_task(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("org_tasks", org_id=org_id)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        assigned_to_id = request.POST.get("assigned_to")
        due_date = request.POST.get("due_date") or None
        priority = request.POST.get("priority", "MED")
        assigned_to = get_object_or_404(User, id=assigned_to_id)

        Task.objects.create(
            organization=org,
            title=title,
            description=description,
            assigned_to=assigned_to,
            created_by=request.user,
            due_date=due_date,
            priority=priority
        )
        messages.success(request, f"Task '{title}' has been added.")

    return redirect("org_tasks", org_id=org_id)


@login_required
def edit_task(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("org_tasks", org_id=org_id)

    if request.method == "POST":
        task_id = request.POST.get("task_id")
        task = get_object_or_404(Task, id=task_id, organization=org)
        task.title = request.POST.get("title")
        task.description = request.POST.get("description", "")
        task.assigned_to = get_object_or_404(User, id=request.POST.get("assigned_to"))
        task.status = request.POST.get("status")
        task.priority = request.POST.get("priority", "MED")
        task.due_date = request.POST.get("due_date") or None
        task.save()
        messages.success(request, f"Task '{task.title}' has been updated.")

    return redirect("org_tasks", org_id=org_id)


@login_required
def delete_task(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("org_tasks", org_id=org_id)

    if request.method == "POST":
        task_id = request.POST.get("task_id")
        task = get_object_or_404(Task, id=task_id, organization=org)
        title = task.title
        task.delete()
        messages.success(request, f"Task '{title}' has been deleted.")

    return redirect("org_tasks", org_id=org_id)


def logout_user(request):
    logout(request)
    return redirect("login")


@login_required
def cycle_task_status(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("org_tasks", org_id=org_id)

    if request.method == "POST":
        task_id = request.POST.get("task_id")
        task = get_object_or_404(Task, id=task_id, organization=org)
        next_status = {"TODO": "PROG", "PROG": "DONE", "DONE": "TODO"}
        task.status = next_status.get(task.status, "TODO")
        task.save()

    return redirect("org_tasks", org_id=org_id)
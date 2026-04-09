from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import Organization, Membership, Task, Department, Announcement, UserProfile


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
    from django.utils import timezone
    from collections import defaultdict

    user_orgs = Organization.objects.filter(membership__user=request.user)
    today = timezone.now().date()
    week_end = today + timezone.timedelta(days=7)

    all_tasks = Task.objects.filter(
        assigned_to=request.user,
        organization__in=user_orgs
    ).select_related("organization").order_by("due_date", "created_at")

    total_tasks = all_tasks.count()
    due_this_week = all_tasks.filter(due_date__gte=today, due_date__lte=week_end).count()
    overdue_count = all_tasks.filter(due_date__lt=today).exclude(status="DONE").count()

    org_stats = []
    for org in user_orgs:
        org_tasks = all_tasks.filter(organization=org)
        total = org_tasks.count()
        done = org_tasks.filter(status="DONE").count()
        percent = round((done / total) * 100) if total > 0 else 0
        org_stats.append({"org": org, "total": total, "done": done, "percent": percent})

    # Announcements from all orgs user belongs to
    announcements = Announcement.objects.filter(
        organization__in=user_orgs
    ).select_related("organization", "created_by").order_by("-created_at")[:10]

    groups_dict = defaultdict(list)
    no_due_date = []

    for task in all_tasks:
        if task.due_date:
            groups_dict[task.due_date].append(task)
        else:
            no_due_date.append(task)

    task_groups = []
    for date in sorted(groups_dict.keys()):
        tasks = groups_dict[date]
        is_today = date == today
        is_overdue = date < today
        if date.year == today.year:
            date_label = date.strftime('%A, %B %d')
        else:
            date_label = date.strftime('%A, %B %d, %Y')

        task_groups.append({
            "date": date,
            "date_label": date_label,
            "is_today": is_today,
            "is_overdue": is_overdue and not is_today,
            "tasks": tasks
        })

    if no_due_date:
        task_groups.append({
            "date": None,
            "date_label": "No Due Date",
            "is_today": False,
            "is_overdue": False,
            "tasks": no_due_date
        })

    return render(request, "dashboard.html", {
        "active_page": "dashboard",
        "organizations": user_orgs,
        "task_groups": task_groups,
        "total_tasks": total_tasks,
        "due_this_week": due_this_week,
        "overdue_count": overdue_count,
        "org_stats": org_stats,
        "announcements": announcements,
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
    unassigned_members = members.filter(role="MEM", department__isnull=True)
    announcements = Announcement.objects.filter(organization=org).select_related("created_by").order_by("-created_at")

    return render(request, "organization_detail.html", {
        "org": org,
        "members": members,
        "departments": departments,
        "unassigned_members": unassigned_members,
        "is_president": user_is_president,
        "is_big_four": user_is_big_four,
        "announcements": announcements,
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
def edit_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_president(request.user, org):
        messages.error(request, "Only the President can edit the organization.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        org.name = request.POST.get("name", org.name)
        org.description = request.POST.get("description", org.description)
        has_two_vp = request.POST.get("has_two_vp") == "on"
        org.has_two_vp = has_two_vp
        if request.FILES.get("logo"):
            org.logo = request.FILES.get("logo")
        org.save()
        messages.success(request, "Organization updated successfully.")

    return redirect("organization_detail", org_id=org_id)


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
def leave_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    membership = Membership.objects.filter(user=request.user, organization=org).first()

    if not membership:
        return redirect("organizations")

    if membership.role == "PRES":
        messages.error(request, "You are the President. Transfer ownership or delete the organization instead.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        membership.delete()
        messages.success(request, f"You have left {org.name}.")
        return redirect("organizations")

    return redirect("organization_detail", org_id=org_id)


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
            messages.success(request, f"{count} member{'s' if count > 1 else ''} removed from their department.")

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


# ─── ANNOUNCEMENTS ────────────────────────────────────────────────────────────

@login_required
def create_announcement(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to post announcements.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        if title and content:
            Announcement.objects.create(
                organization=org,
                created_by=request.user,
                title=title,
                content=content
            )
            messages.success(request, "Announcement posted.")
        else:
            messages.error(request, "Title and content are required.")

    return redirect("organization_detail", org_id=org_id)


@login_required
def delete_announcement(request, org_id, announcement_id):
    org = get_object_or_404(Organization, id=org_id)
    if not is_big_four(request.user, org):
        messages.error(request, "You do not have permission to do this.")
        return redirect("organization_detail", org_id=org_id)

    if request.method == "POST":
        announcement = get_object_or_404(Announcement, id=announcement_id, organization=org)
        announcement.delete()
        messages.success(request, "Announcement deleted.")

    return redirect("organization_detail", org_id=org_id)


# ─── TASKS ────────────────────────────────────────────────────────────────────

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
    departments = Department.objects.filter(organization=org)
    user_is_big_four = is_big_four(request.user, org)

    if user_is_big_four:
        org_task_list = Task.objects.filter(organization=org).select_related("assigned_to")
    else:
        org_task_list = Task.objects.filter(organization=org, assigned_to=request.user).select_related("assigned_to")

    for task in org_task_list:
        membership = Membership.objects.filter(user=task.assigned_to, organization=org).first()
        task.assigned_to_dept = membership.department.name if membership and membership.department else None

    status_columns = [
        ("TODO", "To Do", "bg-gray-400"),
        ("PROG", "In Progress", "bg-blue-400"),
        ("DONE", "Done", "bg-green-400"),
    ]

    return render(request, "org_tasks.html", {
        "org": org,
        "tasks": org_task_list,
        "members": members,
        "departments": departments,
        "is_big_four": user_is_big_four,
        "status_columns": status_columns,
        "active_page": "tasks",
        "current_user_id": request.user.id,
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


@login_required
def member_complete_task(request, org_id, task_id):
    org = get_object_or_404(Organization, id=org_id)
    task = get_object_or_404(Task, id=task_id, organization=org, assigned_to=request.user)

    if request.method == "POST":
        task.status = "DONE"
        task.save()
        messages.success(request, f"'{task.title}' marked as done!")

    return redirect("org_tasks", org_id=org_id)


@login_required
def member_set_task_status(request, org_id, task_id):
    org = get_object_or_404(Organization, id=org_id)
    task = get_object_or_404(Task, id=task_id, organization=org, assigned_to=request.user)

    if request.method == "POST":
        new_status = request.POST.get("status")
        status_labels = {"TODO": "To Do", "PROG": "In Progress", "DONE": "Done"}
        if new_status in status_labels:
            task.status = new_status
            task.save()
            messages.success(request, f"'{task.title}' marked as {status_labels[new_status]}!")

    return redirect("org_tasks", org_id=org_id)


def logout_user(request):
    logout(request)
    return redirect("login")


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        if first_name:
            request.user.first_name = first_name
        if last_name:
            request.user.last_name = last_name
        request.user.save()
        if 'profile_picture' in request.FILES:
            profile_obj.profile_picture = request.FILES['profile_picture']
            profile_obj.save()
        if 'remove_picture' in request.POST and profile_obj.profile_picture:
            profile_obj.profile_picture.delete(save=True)
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    return render(request, 'profile.html', {'profile': profile_obj, 'active_page': 'profile'})
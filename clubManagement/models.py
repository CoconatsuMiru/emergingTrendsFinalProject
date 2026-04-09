from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def get_avatar_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return None


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()



class Organization(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    logo = models.ImageField(upload_to="org_logos/", blank=True, null=True)
    has_two_vp = models.BooleanField(default=False)
    invitation_code = models.CharField(max_length=8, unique=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLE_CHOICES = [
        ("PRES", "President"),
        ("VP",   "Vice President"),
        ("VPI",  "Vice President Internal"),
        ("VPE",  "Vice President External"),
        ("SEC",  "Secretary"),
        ("TRE",  "Treasurer"),
        ("MEM",  "Member"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES, default="MEM")
    department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Department(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class Task(models.Model):
    STATUS_CHOICES = [
        ("TODO", "To Do"),
        ("PROG", "In Progress"),
        ("DONE", "Done"),
    ]

    PRIORITY_CHOICES = [
        ("HIGH", "High"),
        ("MED", "Medium"),
        ("LOW", "Low"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assigned_tasks")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_tasks")
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default="TODO")
    priority = models.CharField(max_length=4, choices=PRIORITY_CHOICES, default="MED")
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date and self.status != "DONE" and self.due_date < timezone.now().date()

    def __str__(self):
        return self.title


class Announcement(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="announcements")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization.name} - {self.title}"
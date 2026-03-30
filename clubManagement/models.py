from django.db import models
from django.contrib.auth.models import User
import uuid


class Organization(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    logo = models.ImageField(upload_to="org_logos/", blank=True, null=True)
    has_two_vp = models.BooleanField(default=False)  # True = VPI + VPE, False = single VP
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

    def __str__(self):
        return f"{self.user.username} - {self.role}"
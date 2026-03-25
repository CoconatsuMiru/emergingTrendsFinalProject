from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLE_CHOICES = [
        ("PRES", "President"),
        ("VPI", "Vice President Internal"),
        ("VPE", "Vice President External"),
        ("SEC", "Secretary"),
        ("TRE", "Treasurer"),
        ("MEM", "Member"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES, default="MEM")

    def __str__(self):
        return f"{self.user.username} - {self.role}"
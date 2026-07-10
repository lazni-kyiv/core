from django.db import models


# ---------------------------------------------------------------------------
# Author Specials
# ---------------------------------------------------------------------------

class AuthorSpecial(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Author Special"
        verbose_name_plural = "Author Specials"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Complexes
# ---------------------------------------------------------------------------

class Complex(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Complex"
        verbose_name_plural = "Complexes"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

class Service(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ServiceType(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="types",
    )
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Service Type"
        verbose_name_plural = "Service Types"
        ordering = ["name"]

    def __str__(self):
        return f"{self.service.name} — {self.name}"


# ---------------------------------------------------------------------------
# Kram
# ---------------------------------------------------------------------------

class KramSection(models.TextChoices):
    ADDITIONAL = "additional", "Additional"
    DRINKS = "drinks", "Drinks"
    MASSAGERS = "massagers", "Massagers"
    SNACKS = "snacks", "Snacks"
    SOUVENIRS = "souvenirs", "Souvenirs"


class KramItem(models.Model):
    id = models.CharField(max_length=10, primary_key=True)
    section = models.CharField(
        max_length=20,
        choices=KramSection.choices,
        db_index=True,
    )
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Kram Item"
        verbose_name_plural = "Kram Items"
        ordering = ["section", "name"]

    def __str__(self):
        return f"[{self.get_section_display()}] {self.name}"
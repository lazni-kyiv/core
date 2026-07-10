from django.db import models


class TextStyle(models.TextChoices):
    LEFT_BOLD = "LeftBold", "Left Bold"
    LEFT_SEMI_BOLD = "LeftSemiBold", "Left Semi Bold"
    LEFT_NORMAL = "LeftNormal", "Left Normal"


class DogovirText(models.Model):
    order = models.PositiveIntegerField(default=0, db_index=True)
    style = models.CharField(max_length=20, choices=TextStyle.choices)
    title = models.TextField()

    class Meta:
        verbose_name = "Dogovir Text"
        verbose_name_plural = "Dogovir Texts"
        ordering = ["order"]

    def __str__(self):
        return f"[{self.order}] {self.title[:60]}"
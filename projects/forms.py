"""Forms for the projects app."""

from django import forms

from projects.models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title", "description", "tags"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "tags": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Space-separated tags (optional)",
                }
            ),
        }

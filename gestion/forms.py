from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Requerido para recibir tus puntos.')

    class Meta:
        model = User
        fields = ("username", "email") # Añadimos el campo email
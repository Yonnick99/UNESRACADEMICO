from django import forms

from .models import (
    estatu,
    Mencion,
    Carrera,
    Tipo_Materia,
    Periodo_Academico,
    Tipo_Contrato,
    Piso,
    aula,
    Asignatura,
    Persona,
)

# gestion_administrativa/forms_persona.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Persona

class PersonaForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = [
            "nombre", "apellido", "cedula",
            "correo", "telefono",
            "fecha_nacimiento", "direccion", "fecha_ingreso",
        ]
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_ingreso": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "apellido": forms.TextInput(attrs={"class": "form-control"}),
            "cedula": forms.NumberInput(attrs={"class": "form-control"}),
            "correo": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data["cedula"]
        if cedula <= 0:
            raise ValidationError("La cédula debe ser un número positivo.")
        return cedula

    def clean_nombre(self):
        return (self.cleaned_data["nombre"] or "").strip().title()

    def clean_apellido(self):
        return (self.cleaned_data["apellido"] or "").strip().title()


# ============================================================
# Base: aplica clases Bootstrap automáticamente
# ============================================================

class BootstrapModelForm(forms.ModelForm):
    """
    Aplica clases Bootstrap 5 a todos los campos.
    - text/number/date/email: form-control
    - select: form-select
    - checkbox: form-check-input
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget

            # Checkbox
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
                continue

            # Select
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
                continue

            # Inputs normales
            widget.attrs.setdefault("class", "form-control")

            # Placeholder por defecto (opcional y útil)
            if not widget.attrs.get("placeholder"):
                widget.attrs["placeholder"] = field.label or name


# ============================================================
# Formularios de Catálogos / Componentes
# ============================================================

class EstatuForm(BootstrapModelForm):
    class Meta:
        model = estatu
        fields = ["nombre"]


class CarreraForm(BootstrapModelForm):
    class Meta:
        model = Carrera
        fields = ["nombre", "descripcion"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class MencionForm(BootstrapModelForm):
    class Meta:
        model = Mencion
        fields = ["id_carrera", "nombre", "descripcion"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }


class TipoMateriaForm(BootstrapModelForm):
    class Meta:
        model = Tipo_Materia
        fields = ["nombre"]


class PeriodoAcademicoForm(BootstrapModelForm):
    class Meta:
        model = Periodo_Academico
        fields = ["nombre", "fecha_inicio", "fecha_fin", "id_estatu"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class TipoContratoForm(BootstrapModelForm):
    class Meta:
        model = Tipo_Contrato
        fields = ["nombre", "descripcion"]

class PisoForm(BootstrapModelForm):
    class Meta:
        model = Piso
        fields = ["nombre"]


class AulaForm(BootstrapModelForm):
    class Meta:
        model = aula
        fields = ["id_piso", "nombre", "capacidad", "estatus"]

    def clean_capacidad(self):
        cap = self.cleaned_data.get("capacidad")
        if cap is not None and cap <= 0:
            raise forms.ValidationError("La capacidad debe ser mayor a 0.")
        return cap


class AsignaturaForm(BootstrapModelForm):
    class Meta:
        model = Asignatura
        fields = ["id_mencion", "id_tipo_materia", "codigo", "nombre", "unidades_credito"]

    def clean_unidades_credito(self):
        uc = self.cleaned_data.get("unidades_credito")
        if uc is not None and uc <= 0:
            raise forms.ValidationError("Las unidades de crédito deben ser mayores a 0.")
        return uc

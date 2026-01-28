# profesor/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from gestion_administrativa.models import Persona, estatu, Tipo_Contrato
from profesor.models import Facilitador


class FacilitadorAltaForm(forms.Form):
    id_persona = forms.IntegerField(widget=forms.HiddenInput())

    id_estatu = forms.ModelChoiceField(
        queryset=estatu.objects.all().order_by("nombre"),
        label="Estatus del Facilitador",
        empty_label="Seleccione...",
    )

    fecha_creacion = forms.DateField(
        label="Fecha de Registro",
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    id_tipo_Contrato = forms.ModelChoiceField(
        queryset=Tipo_Contrato.objects.all().order_by("nombre"),
        label="Tipo de Contrato",
        empty_label="Seleccione...",
    )

    id_estatu_contrato = forms.ModelChoiceField(
        queryset=estatu.objects.all().order_by("nombre"),
        label="Estatus del Contrato",
        empty_label="Seleccione...",
    )

    horas_academicas = forms.IntegerField(
        label="Horas Académicas",
        min_value=1,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs.update({"class": "form-select"})
            else:
                widget.attrs.update({"class": "form-control"})

        # ✅ ID único para profesor (no choca con estudiante)
        self.fields["id_persona"].widget.attrs.update({"id": "personaIdHiddenFac"})

    def clean_id_persona(self):
        persona_id = self.cleaned_data.get("id_persona")
        if not persona_id:
            raise ValidationError("Debe seleccionar una persona.")

        try:
            persona = Persona.objects.get(pk=persona_id)
        except Persona.DoesNotExist:
            raise ValidationError("La persona seleccionada no existe.")

        return persona

    def clean(self):
        cleaned = super().clean()
        persona = cleaned.get("id_persona")

        if persona:
            existe_activo = Facilitador.objects.filter(
                id_persona=persona,
                activo=True,
                fecha_fin__isnull=True,
            ).exists()
            if existe_activo:
                raise ValidationError(
                    "Esta persona ya tiene un Facilitador activo (fecha_fin vacía)."
                )

        return cleaned

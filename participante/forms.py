# participante/forms.py
from django import forms
from .models import Estudiante


class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = [
            "id_persona",
            "id_carrera",
            "id_mencion",
            "activo",
            "fecha_creacion",
            "unidades_cred_aprobadas",
            "unidades_cred_cursadas",
            "unidades_cred_reprobadas",
            "fecha_fin",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bootstrap classes
        for name, field in self.fields.items():
            widget = field.widget

            if isinstance(widget, forms.Select):
                widget.attrs.update({"class": "form-select"})
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({"class": "form-check-input"})
            else:
                widget.attrs.update({"class": "form-control"})

        # Opcional: placeholders útiles
        self.fields["unidades_cred_aprobadas"].widget.attrs.update({"min": 0})
        self.fields["unidades_cred_cursadas"].widget.attrs.update({"min": 0})
        self.fields["unidades_cred_reprobadas"].widget.attrs.update({"min": 0})

# gestion_administrativa/views_persona.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Persona
from .forms import PersonaForm
from .services_persona import crear_user_y_perfil_desde_persona
# gestion_administrativa/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import Persona

# gestion_administrativa/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import Persona

REGEX_SOLO_LETRAS_ESPACIOS = re.compile(r"^[A-Za-zÁÉÍÓÚÜáéíóúüÑñ ]+$")
REGEX_SOLO_NUMEROS = re.compile(r"^\d+$")


class PersonaForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = [
            "nombre",
            "apellido",
            "cedula",
            "sexo",               # ✅ NUEVO (dropdown)
            "fecha_nacimiento",
            "direccion",
            "telefono",
            "correo",
            "fecha_ingreso",
        ]
        widgets = {
            "fecha_ingreso": forms.DateInput(attrs={"type": "date"}),
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ TODOS OBLIGATORIOS (según tu requerimiento)
        for name, field in self.fields.items():
            field.required = True

        # mínimos (UX + backend real en clean)
        self.fields["nombre"].min_length = 3
        self.fields["apellido"].min_length = 2

        # Bootstrap + attrs HTML
        for name, field in self.fields.items():
            widget = field.widget
            css = "form-select" if isinstance(widget, forms.Select) else "form-control"
            widget.attrs.update({"class": css})

        self.fields["nombre"].widget.attrs.update({"minlength": 3, "autocomplete": "off"})
        self.fields["apellido"].widget.attrs.update({"minlength": 3, "autocomplete": "off"})

        # Cédula: solo números (UX)
        self.fields["cedula"].widget.attrs.update({
            "inputmode": "numeric",
            "pattern": r"\d{6,}",
            "min": 0,
            "placeholder": "Solo números (mín. 6 dígitos)",
        })

        # ✅ Teléfono: solo números + mínimo 11 (UX)
        self.fields["telefono"].widget.attrs.update({
            "inputmode": "numeric",
            "pattern": r"\d{11,}",
            "placeholder": "Solo números (mín. 11 dígitos)",
        })

        # Correo (UX)
        self.fields["correo"].widget.attrs.update({"type": "email", "placeholder": "ejemplo@correo.com"})

    # ===== Helpers =====
    def _limpiar_texto(self, value: str) -> str:
        value = (value or "").strip()
        value = " ".join(value.split())
        return value

    def _validar_nombre_apellido(self, value: str, field_label: str) -> str:
        value = self._limpiar_texto(value)

        if len(value) < 3:
            raise ValidationError(f"{field_label} debe tener mínimo 3 caracteres.")

        if not REGEX_SOLO_LETRAS_ESPACIOS.match(value):
            raise ValidationError(f"{field_label} solo puede contener letras y espacios (sin números).")

        return value

    # ===== Validaciones =====
    def clean_nombre(self):
        return self._validar_nombre_apellido(self.cleaned_data.get("nombre"), "Nombre")

    def clean_apellido(self):
        return self._validar_nombre_apellido(self.cleaned_data.get("apellido"), "Apellido")

    def clean_cedula(self):
        cedula = self.cleaned_data.get("cedula")

        if cedula is None:
            raise ValidationError("Cédula es obligatoria.")

        if int(cedula) < 0:
            raise ValidationError("Cédula no puede ser negativa.")

        if len(str(cedula)) < 6:
            raise ValidationError("Cédula debe tener mínimo 6 dígitos.")

        return cedula

    def clean_telefono(self):
        tel = (self.cleaned_data.get("telefono") or "").strip()

        if not tel:
            raise ValidationError("Teléfono es obligatorio.")

        if not REGEX_SOLO_NUMEROS.match(tel):
            raise ValidationError("Teléfono solo debe contener números.")

        # ✅ mínimo 11
        if len(tel) < 11:
            raise ValidationError("Teléfono debe tener mínimo 11 dígitos.")

        return tel

    def clean_correo(self):
        correo = (self.cleaned_data.get("correo") or "").strip()
        if not correo:
            raise ValidationError("Correo es obligatorio.")
        return correo

    def clean_fecha_ingreso(self):
        fecha = self.cleaned_data.get("fecha_ingreso")
        if not fecha:
            raise ValidationError("Fecha de ingreso es obligatoria.")
        if fecha > timezone.localdate():
            raise ValidationError("Fecha de ingreso no puede ser futura.")
        return fecha
    
    
    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get("fecha_nacimiento")
        if not fecha:
            raise ValidationError("Fecha de nacimiento es obligatoria.")

        hoy = timezone.localdate()

        # Calcular edad exacta (considerando mes/día)
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))

        if edad < 15:
            raise ValidationError("Debe tener al menos 15 años para registrarse.")

        if fecha > hoy:
            raise ValidationError("Fecha de nacimiento no puede ser futura.")

        return fecha




def persona_list_create(request):
    """
    Pantalla nueva independiente:
    - Form arriba para crear Persona
    - Tabla abajo con Personas
    - Pagina 15
    - Crea User + PerfilUsuario automáticamente
    """
    if request.method == "POST":
        form = PersonaForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    persona = form.save()
                    user, perfil = crear_user_y_perfil_desde_persona(persona)
                messages.success(
                    request,
                    f"Persona creada. Usuario generado: {user.username}"
                )
                return redirect(request.path)
            except IntegrityError:
                messages.error(request, "No se pudo guardar. Verifica duplicados (cédula/correo).")
        else:
            messages.error(request, "Revisa los campos del formulario.")
    else:
        form = PersonaForm()

    qs = Persona.objects.all().order_by("-id_persona")
    paginator = Paginator(qs, 15)

    page_number = request.GET.get("page") or "1"
    try:
        page_obj = paginator.get_page(page_number)  # robusto (no lanza EmptyPage)
    except Exception:
        page_obj = paginator.get_page(1)

    return render(request, "gestion_administrativa/persona_base.html", {
        "titulo": "Gestión de Personas",
        "form": form,
        "page_obj": page_obj,
    })


def persona_update(request, pk: int):
    persona = get_object_or_404(Persona, pk=pk)

    if request.method == "POST":
        form = PersonaForm(request.POST, instance=persona)
        if form.is_valid():
            try:
                with transaction.atomic():
                    persona = form.save()

                    # si no tenía perfil (caso raro), lo creamos
                    crear_user_y_perfil_desde_persona(persona)

                messages.success(request, "Persona actualizada correctamente.")
                # conservar page si viene en query
                page = request.GET.get("page")
                url = reverse("gestion_administrativa:persona")
                if page:
                    url = f"{url}?page={page}"
                return redirect(url)
            except IntegrityError:
                messages.error(request, "No se pudo actualizar. Verifica duplicados (cédula/correo).")
        else:
            messages.error(request, "Revisa los campos del formulario.")
    else:
        form = PersonaForm(instance=persona)

    return render(request, "gestion_administrativa/persona_editar.html", {
        "titulo": "Editar Persona",
        "form": form,
        "persona": persona,
    })


def persona_delete(request, pk: int):
    if request.method != "POST":
        return redirect(reverse("gestion_administrativa:persona"))

    persona = get_object_or_404(Persona, pk=pk)

    try:
        with transaction.atomic():
            # si existe perfil, borramos primero user/perfil (evita huérfanos)
            if hasattr(persona, "perfil_usuario"):
                user = persona.perfil_usuario.user
                persona.perfil_usuario.delete()
                user.delete()

            persona.delete()

        messages.success(request, "Persona eliminada correctamente.")
    except ProtectedError:
        messages.error(request, "No se pudo eliminar: la persona está relacionada con otros registros.")
    except IntegrityError:
        messages.error(request, "No se pudo eliminar por restricciones de integridad.")

    return redirect(reverse("gestion_administrativa:persona"))

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = "Crea grupos del sistema y asigna permisos (RBAC) de forma idempotente."

    # Define aquí los grupos y los permisos que deben tener (por app_label.codename)
    GRUPOS = {
        "Master": [
            # Master tendrá TODO (lo manejamos abajo en modo total)
        ],
        "Administrador": [
            # Gestión Administrativa (Componentes CRUD)
            "gestion_administrativa.ver_componentes",
            "gestion_administrativa.crear_componentes",
            "gestion_administrativa.editar_componentes",
            "gestion_administrativa.eliminar_componentes",
        ],
        "Profesor": [
            "profesor.ver_secciones",
            "profesor.cargar_notas",
            "profesor.solicitar_cambio_nota",
            "profesor.seleccionar_asignaturas",
            "profesor.gestionar_disponibilidad",
            "profesor.ver_lista_participantes",
        ],
        "Participante": [
            "participante.inscribir",
            "participante.ver_horario",
            "participante.ver_record",
            "participante.ver_promedio",
            "participante.ver_constancia",
        ],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--master-todo",
            action="store_true",
            help="Si se usa, el grupo Master obtiene TODOS los permisos del sistema.",
        )

    def handle(self, *args, **options):
        master_todo = options["master_todo"]

        # 1) Crear grupos si no existen
        for nombre_grupo in self.GRUPOS.keys():
            grupo, creado = Group.objects.get_or_create(name=nombre_grupo)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"✅ Grupo creado: {nombre_grupo}"))
            else:
                self.stdout.write(f"ℹ️ Grupo ya existe: {nombre_grupo}")

        # 2) Asignar permisos por grupo (excepto Master si master_todo)
        for nombre_grupo, permisos in self.GRUPOS.items():
            grupo = Group.objects.get(name=nombre_grupo)

            if nombre_grupo == "Master" and master_todo:
                # Master recibe todos los permisos del sistema
                todos = Permission.objects.all()
                grupo.permissions.set(todos)
                self.stdout.write(self.style.SUCCESS("✅ Master: asignados TODOS los permisos"))
                continue

            if nombre_grupo == "Master":
                # Si no usamos master_todo, asignamos un set mínimo coherente con tu lista
                permisos_minimos = [
                    "seguridad.gestionar_usuarios",
                    "seguridad.asignar_roles",
                    "seguridad.asignar_admin",
                    "seguridad.ver_auditoria",
                    "seguridad.exportar_auditoria",
                    "seguridad.ver_logs_acceso",
                    # y además todo lo de componentes:
                    "gestion_administrativa.ver_componentes",
                    "gestion_administrativa.crear_componentes",
                    "gestion_administrativa.editar_componentes",
                    "gestion_administrativa.eliminar_componentes",
                ]
                permisos = permisos_minimos

            asignados = []
            faltantes = []

            for perm_str in permisos:
                try:
                    app_label, codename = perm_str.split(".", 1)
                except ValueError:
                    faltantes.append(perm_str)
                    continue

                perm = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename=codename,
                ).first()

                if not perm:
                    faltantes.append(perm_str)
                    continue

                grupo.permissions.add(perm)
                asignados.append(perm_str)

            self.stdout.write(self.style.SUCCESS(f"\n🔐 Grupo: {nombre_grupo}"))
            self.stdout.write(f"   ✅ Permisos asignados: {len(asignados)}")
            for p in asignados:
                self.stdout.write(f"      - {p}")

            if faltantes:
                self.stdout.write(self.style.WARNING(f"   ⚠️ Permisos NO encontrados: {len(faltantes)}"))
                for p in faltantes:
                    self.stdout.write(f"      - {p}")

        self.stdout.write(self.style.SUCCESS("\n🎉 Proceso completado."))

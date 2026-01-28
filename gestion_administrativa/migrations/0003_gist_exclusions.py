from django.db import migrations

FORWARD_SQL = """
CREATE EXTENSION IF NOT EXISTS btree_gist;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'excl_aula_horario_periodo'
  ) THEN
    ALTER TABLE "Temp_Asignaturas_has_Facilitador_has_aula"
    ADD CONSTRAINT excl_aula_horario_periodo
    EXCLUDE USING gist (
      id_aula WITH =,
      id_periodo WITH =,
      tstzrange(horario_inicio, horario_fin, '[)') WITH &&
    );
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'excl_facilitador_horario_periodo'
  ) THEN
    ALTER TABLE "Temp_Asignaturas_has_Facilitador_has_aula"
    ADD CONSTRAINT excl_facilitador_horario_periodo
    EXCLUDE USING gist (
      id_facilitador WITH =,
      id_periodo WITH =,
      tstzrange(horario_inicio, horario_fin, '[)') WITH &&
    );
  END IF;
END $$;
"""

REVERSE_SQL = """
ALTER TABLE "Temp_Asignaturas_has_Facilitador_has_aula"
  DROP CONSTRAINT IF EXISTS excl_aula_horario_periodo;

ALTER TABLE "Temp_Asignaturas_has_Facilitador_has_aula"
  DROP CONSTRAINT IF EXISTS excl_facilitador_horario_periodo;
"""

class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ("gestion_administrativa", "0002_initial"),
        ("profesor", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]

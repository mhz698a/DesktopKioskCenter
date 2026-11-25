"""Catálogos predeterminados y compartidos de usuarios."""

FACULTY_DEFAULTS = (
    "Facultad de Artes",
    "Facultad de Ciencias Naturales",
    "Facultad de Ciencias Políticas y Sociales",
    "Facultad de Contaduría y Administración",
    "Facultad de Derecho",
    "Facultad de Enfermería",
    "Facultad de Filosofía",
    "Facultad de Informática",
    "Facultad de Ingeniería",
    "Facultad de Lenguas y Letras",
    "Facultad de Medicina",
    "Facultad de Psicología y Educación",
    "Facultad de Química",
)

INTERNAL_STAFF_TYPES = ("Docente", "Administrativo")

# Los tipos y universidades se administran desde DesktopKioskCenter. Estos
# valores solo se usan para sembrar por primera vez la base SQLite en AppData.
EXTERNAL_USER_TYPE_DEFAULTS = (
    ("Estudiante Externo", True),
    ("Trabajador Interno", False),
    ("Público en general", False),
)

UNIVERSITY_DEFAULTS = (
    "Instituto Tecnológico de Querétaro (ITQ)",
    "Universidad Tecnológica de Querétaro (UTEQ)",
    "Universidad Politécnica de Querétaro (UPQ)",
    "Universidad Aeronáutica en Querétaro (UNAQ)",
    "Universidad Nacional Autónoma de México (UNAM - Campus Juriquilla)",
    "Universidad Tecnológica de San Juan del Río (UTSJR)",
    "Universidad Politécnica de Santa Rosa Jáuregui (UPSRJ)",
    "Escuela Normal Superior de Querétaro – ENSQ",
    "Tecnológico de Monterrey (Campus Querétaro)",
    "Universidad Anáhuac (Sede Querétaro)",
    "Universidad Tecnológica de México (UNITEC)",
    "Universidad Marista de Querétaro",
    "Universidad Cuauhtémoc (Plantel Querétaro)",
    "Arkansas State University (Campus Querétaro)",
    "Universidad de Estudios Avanzados (UNEA)",
    "Universidad Tecmilenio",
    "Otra institución externa",
)

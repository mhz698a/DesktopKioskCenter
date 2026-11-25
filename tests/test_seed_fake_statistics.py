"""Pruebas del generador de datos ficticios para estadísticas."""

import tempfile
import unittest
from pathlib import Path

from database import Database
from devtools.seed_fake_statistics import remove_previous_demo_data, seed_demo_data


class FakeStatisticsSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.database = Database(
            db_path=root / "appdata" / "desktopkioskcenter.sqlite3",
            legacy_dir=root / "legacy",
        )
        self.database.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seed_includes_docentes_and_administrativos(self):
        generated = seed_demo_data(self.database, days=90, seed=7085)
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT tipo_usuario, COUNT(*) AS total
                FROM access_logs
                WHERE kiosk_name LIKE 'DEMO_STATS:%'
                GROUP BY tipo_usuario
                """
            ).fetchall()
        totals = {row["tipo_usuario"]: int(row["total"]) for row in rows}

        self.assertGreater(generated, 0)
        self.assertGreater(totals.get("Docente", 0), 0)
        self.assertGreater(totals.get("Administrativo", 0), 0)
        self.assertGreater(totals.get("Alumno interno", 0), 0)

    def test_remove_previous_seed_keeps_real_accesses(self):
        self.database.record_access_log(
            kiosk_name="PC real",
            nombres="Usuario",
            apellidos="Real",
            tipo_usuario="Público en general",
        )
        seed_demo_data(self.database, days=5, seed=7085)
        removed_accesses, removed_requests = remove_previous_demo_data(self.database)

        self.assertGreater(removed_accesses, 0)
        self.assertGreater(removed_requests, 0)
        self.assertEqual(
            [row["kiosk_name"] for row in self.database.list_access_logs(limit=None)],
            ["PC real"],
        )


if __name__ == "__main__":
    unittest.main()

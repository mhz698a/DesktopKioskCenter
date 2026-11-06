"""Pruebas de agregación para los gráficos de estadísticas."""
import unittest

from tabs.statistics.report_data import (
    PUBLIC_GENERAL_LABEL,
    UAQ_FULL_NAME,
    build_chart_data,
)


class StatisticsChartDataTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "period": "2026-11-02",
                "origin": "UAQ",
                "source": "Facultad de Informática",
                "total": 4,
            },
            {
                "period": "2026-11-02",
                "origin": "UAQ",
                "source": "Facultad de Artes",
                "total": 3,
            },
            {
                "period": "2026-11-02",
                "origin": "UAQ",
                "source": "Trabajador interno",
                "total": 2,
            },
            {
                "period": "2026-11-02",
                "origin": "Universidad",
                "source": "Universidad X",
                "total": 5,
            },
            {
                "period": "2026-11-03",
                "origin": "Público en general",
                "source": "Público en general",
                "total": 6,
            },
        ]

    def test_general_origin_chart_collapses_all_uaq_faculties(self):
        _periods, general, _faculties = build_chart_data(self.rows, "day")
        self.assertEqual(
            dict(general),
            {
                UAQ_FULL_NAME: 9,
                "Universidad X": 5,
                PUBLIC_GENERAL_LABEL: 6,
            },
        )
        self.assertNotIn("Facultad de Informática", dict(general))
        self.assertNotIn("Facultad de Artes", dict(general))
        self.assertNotIn("UAQ", dict(general))

    def test_faculty_chart_keeps_faculties_separate_and_excludes_workers(self):
        _periods, _general, faculties = build_chart_data(self.rows, "day")
        self.assertEqual(
            dict(faculties),
            {
                "Facultad de Informática": 4,
                "Facultad de Artes": 3,
            },
        )
        self.assertNotIn("Trabajador interno", dict(faculties))

    def test_period_chart_uses_requested_grouping_label(self):
        daily, _general, _faculties = build_chart_data(self.rows, "day")
        self.assertEqual(dict(daily), {"02/11": 14, "03/11": 6})

        weekly, _general, _faculties = build_chart_data(self.rows, "week")
        self.assertEqual(dict(weekly), {"Sem 02/11": 20})

        monthly, _general, _faculties = build_chart_data(self.rows, "month")
        self.assertEqual(dict(monthly), {"11/2026": 20})

    def test_invalid_grouping_is_rejected(self):
        with self.assertRaises(ValueError):
            build_chart_data(self.rows, "year")


if __name__ == "__main__":
    unittest.main()

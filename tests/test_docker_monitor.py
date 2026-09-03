# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el módulo core de Monitoreo de Recursos Docker (core/docker_monitor.py).
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.core.docker_monitor import (
    parse_bytes_str,
    format_bytes,
    parse_cpu_percent,
    parse_memory_usage,
    identify_container_project,
    get_live_docker_stats
)


class TestDockerMonitor(unittest.TestCase):
    def test_parse_bytes_str(self):
        self.assertEqual(parse_bytes_str("100B"), 100.0)
        self.assertEqual(parse_bytes_str("1kB"), 1000.0)
        self.assertEqual(parse_bytes_str("1KiB"), 1024.0)
        self.assertEqual(parse_bytes_str("10MB"), 10000000.0)
        self.assertEqual(parse_bytes_str("10MiB"), 10 * 1024 * 1024.0)
        self.assertEqual(parse_bytes_str("2GiB"), 2 * (1024 ** 3))
        self.assertEqual(parse_bytes_str(""), 0.0)
        self.assertEqual(parse_bytes_str(None), 0.0)

    def test_format_bytes(self):
        self.assertEqual(format_bytes(500), "500 B")
        self.assertEqual(format_bytes(2048), "2.0 KiB")
        self.assertEqual(format_bytes(10 * 1024 * 1024), "10.0 MiB")
        self.assertEqual(format_bytes(2 * (1024 ** 3)), "2.00 GiB")

    def test_parse_cpu_percent(self):
        self.assertEqual(parse_cpu_percent("0.36%"), 0.36)
        self.assertEqual(parse_cpu_percent("12.5%"), 12.5)
        self.assertEqual(parse_cpu_percent("0%"), 0.0)
        self.assertEqual(parse_cpu_percent(""), 0.0)

    def test_parse_memory_usage(self):
        res = parse_memory_usage("188.6MiB / 31.2GiB")
        self.assertGreater(res["used_bytes"], 100 * 1024 * 1024)
        self.assertGreater(res["limit_bytes"], 30 * (1024 ** 3))
        self.assertEqual(res["used_str"], "188.6MiB")
        self.assertEqual(res["limit_str"], "31.2GiB")
        self.assertGreater(res["percent"], 0.0)
        self.assertLess(res["percent"], 5.0)

    def test_identify_container_project(self):
        # DDEV Project web
        pname, sname, scope = identify_container_project("ddev-multisitio-web")
        self.assertEqual(pname, "multisitio")
        self.assertEqual(sname, "web")
        self.assertEqual(scope, "project")

        # DDEV Project db
        pname, sname, scope = identify_container_project("ddev-multisitio-db")
        self.assertEqual(pname, "multisitio")
        self.assertEqual(sname, "db")
        self.assertEqual(scope, "project")

        # DDEV Project addon
        pname, sname, scope = identify_container_project("ddev-multisitio-cloudbeaver")
        self.assertEqual(pname, "multisitio")
        self.assertEqual(sname, "cloudbeaver")
        self.assertEqual(scope, "project")

        # DDEV System router
        pname, sname, scope = identify_container_project("ddev-router")
        self.assertEqual(pname, "DDEV Sistema")
        self.assertEqual(sname, "router")
        self.assertEqual(scope, "system")

        # DDEV System ssh agent
        pname, sname, scope = identify_container_project("ddev-ssh-agent")
        self.assertEqual(pname, "DDEV Sistema")
        self.assertEqual(sname, "ssh-agent")
        self.assertEqual(scope, "system")

        # External container
        pname, sname, scope = identify_container_project("portainer")
        self.assertEqual(pname, "Otros Contenedores")
        self.assertEqual(sname, "portainer")
        self.assertEqual(scope, "external")

    def test_get_live_docker_stats_structure(self):
        stats = get_live_docker_stats(timeout=5)
        self.assertIsInstance(stats, dict)
        self.assertIn("is_docker_available", stats)
        self.assertIn("containers", stats)
        self.assertIn("projects", stats)
        self.assertIn("global_summary", stats)


if __name__ == "__main__":
    unittest.main()

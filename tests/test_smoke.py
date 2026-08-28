# -*- coding: utf-8 -*-
"""
Smoke tests for DDEV Studio modular package.
"""

import os
import sys
import unittest
import tempfile
import shutil

# Ensure root directory is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.constants import (
    FRAMEWORKS,
    DRUPAL_VERSIONS,
    DEFAULT_SITES_DIR,
    CUSTOM_CSS,
    ICONS_DIR
)
from ddev_studio.core.detector import detect_project_details, inspect_project_stack, sanitize_project_name, detect_sqlite_database
from ddev_studio.core.terminal import find_terminal_command


class TestSanitizeName(unittest.TestCase):
    def test_hostname_sanitization(self):
        self.assertEqual(sanitize_project_name("test_next"), "test-next")
        self.assertEqual(sanitize_project_name("My_Awesome_App"), "my-awesome-app")
        self.assertEqual(sanitize_project_name("_leading_and_trailing_"), "leading-and-trailing")
        self.assertEqual(sanitize_project_name("special@chars#123"), "special-chars-123")
        self.assertEqual(sanitize_project_name("multiple---dashes"), "multiple-dashes")
        self.assertEqual(sanitize_project_name(""), "")


class TestConstants(unittest.TestCase):
    def test_frameworks_structure(self):
        self.assertIsInstance(FRAMEWORKS, list)
        self.assertGreater(len(FRAMEWORKS), 0)
        for fw in FRAMEWORKS:
            self.assertIn("id", fw)
            self.assertIn("name", fw)
            self.assertIn("category", fw)
            self.assertIn("icon", fw)

    def test_drupal_versions(self):
        self.assertIsInstance(DRUPAL_VERSIONS, list)
        self.assertGreaterEqual(len(DRUPAL_VERSIONS), 5)
        for dv in DRUPAL_VERSIONS:
            self.assertIn("id", dv)
            self.assertIn("label", dv)
            self.assertIn("php", dv)
            self.assertIn("docroot", dv)

    def test_icons_dir(self):
        self.assertTrue(os.path.isdir(ICONS_DIR))
        self.assertTrue(os.path.exists(os.path.join(ICONS_DIR, "ddev.svg")))
        self.assertTrue(os.path.exists(os.path.join(ICONS_DIR, "nextjs.svg")))


class TestDetector(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_invalid_path(self):
        res = detect_project_details("/non/existent/path/12345")
        self.assertFalse(res["valid"])

    def test_nextjs_detection_with_config(self):
        next_config = os.path.join(self.test_dir, "next.config.mjs")
        with open(next_config, "w") as f:
            f.write("/** @type {import('next').NextConfig} */\nconst nextConfig = {};\nexport default nextConfig;")
            
        det = detect_project_details(self.test_dir)
        self.assertTrue(det["valid"])
        self.assertEqual(det["type"], "nextjs")
        self.assertEqual(det["docroot"], ".")

    def test_nextjs_detection_with_package_json(self):
        pkg_json = os.path.join(self.test_dir, "package.json")
        with open(pkg_json, "w") as f:
            f.write('{"name": "my-next-app", "dependencies": {"next": "^14.2.0", "react": "^18.3.0", "react-dom": "^18.3.0"}}')
            
        det = detect_project_details(self.test_dir)
        self.assertTrue(det["valid"])
        self.assertEqual(det["type"], "nextjs")

        tech, has_db, is_php, is_py, is_js, is_static = inspect_project_stack(self.test_dir, {}, {})
        self.assertEqual(tech, "nextjs")
        self.assertTrue(is_js)
        self.assertFalse(has_db)

    def test_drupal_detection_with_sites_dir(self):
        docroot = os.path.join(self.test_dir, "web")
        sites_dir = os.path.join(docroot, "sites")
        os.makedirs(sites_dir)
        
        det = detect_project_details(self.test_dir)
        self.assertTrue(det["valid"])
        self.assertIn("drupal", det["type"])
        self.assertEqual(det["docroot"], "web")

    def test_wordpress_detection(self):
        wp_file = os.path.join(self.test_dir, "wp-config.php")
        with open(wp_file, "w") as f:
            f.write("<?php // WordPress configuration")
            
        det = detect_project_details(self.test_dir)
        self.assertTrue(det["valid"])
        self.assertEqual(det["type"], "wordpress")
        self.assertEqual(det["docroot"], ".")

    def test_laravel_detection(self):
        artisan_file = os.path.join(self.test_dir, "artisan")
        with open(artisan_file, "w") as f:
            f.write("#!/usr/bin/env php\n<?php")
        os.makedirs(os.path.join(self.test_dir, "public"))
        
        det = detect_project_details(self.test_dir)
        self.assertTrue(det["valid"])
        self.assertEqual(det["type"], "laravel")
        self.assertEqual(det["docroot"], "public")

    def test_django_detection(self):
        manage_py = os.path.join(self.test_dir, "manage.py")
        with open(manage_py, "w") as f:
            f.write("#!/usr/bin/env python\nimport django")
            
        det = detect_project_details(self.test_dir)
        self.assertTrue(det["valid"])
        self.assertEqual(det["type"], "django")

    def test_inspect_stack_frontend(self):
        pkg_json = os.path.join(self.test_dir, "package.json")
        with open(pkg_json, "w") as f:
            f.write('{"name": "test-react", "dependencies": {"react": "^18.0.0"}}')
            
        tech, has_db, is_php, is_py, is_js, is_static = inspect_project_stack(self.test_dir, {}, {})
        self.assertEqual(tech, "react")
        self.assertTrue(is_js)
        self.assertFalse(has_db)

    def test_inspect_stack_no_db(self):
        tech, has_db, is_php, is_py, is_js, is_static = inspect_project_stack(
            self.test_dir,
            {"database_type": "none"},
            {}
        )
        self.assertFalse(has_db)

    def test_sqlite_detection(self):
        self.assertIsNone(detect_sqlite_database(self.test_dir))
        
        sqlite_file = os.path.join(self.test_dir, "db.sqlite3")
        with open(sqlite_file, "w") as f:
            f.write("sqlite database content")
            
        sql_info = detect_sqlite_database(self.test_dir)
        self.assertIsNotNone(sql_info)
        self.assertEqual(sql_info["rel_path"], "db.sqlite3")
        self.assertTrue(sql_info["size_kb"] >= 0)


class TestTerminal(unittest.TestCase):
    def test_terminal_detection(self):
        term = find_terminal_command()
        self.assertTrue(term is None or isinstance(term, str))


class TestImports(unittest.TestCase):
    def test_all_modules_importable(self):
        import ddev_studio
        import ddev_studio.constants
        import ddev_studio.core
        import ddev_studio.core.terminal
        import ddev_studio.core.process
        import ddev_studio.core.detector
        import ddev_studio.recipes
        import ddev_studio.recipes.runner
        import ddev_studio.ui
        import ddev_studio.ui.helpers
        import ddev_studio.ui.dialogs.progress
        import ddev_studio.ui.dialogs.db_containers
        import ddev_studio.ui.views.details
        import ddev_studio.ui.views.subsites
        import ddev_studio.ui.window
        import ddev_studio.main
        self.assertIsNotNone(ddev_studio.__version__)


if __name__ == "__main__":
    unittest.main()

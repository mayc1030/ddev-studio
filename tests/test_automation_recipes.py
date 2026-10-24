# -*- coding: utf-8 -*-
"""
Pruebas unitarias para las recetas y detección de n8n y OpenClaw
(ddev_studio.recipes.automation, registry, detector).
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ddev_studio.recipes.automation import N8nRecipe, OpenClawRecipe
from ddev_studio.recipes.registry import get_recipe, list_recipes
from ddev_studio.recipes.context import RecipeContext
from ddev_studio.core.detector import detect_project_details, inspect_project_stack


class TestAutomationRecipes(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_registry_contains_automation_recipes(self):
        recipes = list_recipes()
        self.assertIn("n8n", recipes)
        self.assertIn("openclaw", recipes)

        r_n8n = get_recipe("n8n")
        self.assertIsInstance(r_n8n, N8nRecipe)
        self.assertEqual(r_n8n.fw_id, "n8n")

        r_claw = get_recipe("openclaw")
        self.assertIsInstance(r_claw, OpenClawRecipe)
        self.assertEqual(r_claw.fw_id, "openclaw")

    @patch.object(RecipeContext, "run_cmd", return_value=0)
    @patch.object(N8nRecipe, "restart_ddev")
    @patch.object(N8nRecipe, "setup_daemon")
    @patch.object(N8nRecipe, "setup_nginx_proxy")
    @patch.object(N8nRecipe, "start_ddev")
    @patch.object(N8nRecipe, "configure_ddev")
    def test_n8n_recipe_execution(self, mock_cfg, mock_start, mock_proxy, mock_daemon, mock_restart, mock_run_cmd):
        recipe = N8nRecipe()
        ctx = RecipeContext(
            parent_window=None,
            raw_name="My n8n",
            slug="my-n8n",
            target_dir=self.test_dir,
            fw={"id": "n8n", "name": "n8n (Automatización)", "nodejs": "22"},
            drupal_ver_info={},
            php_version="8.3",
            db_type="none",
            node_version="22",
            auto_install=True,
            is_multisite_enabled=False,
            dialog=None,
            primary_url="https://my-n8n.ddev.site",
        )

        recipe.execute(ctx)

        mock_cfg.assert_called_once()
        args, kwargs = mock_cfg.call_args
        self.assertEqual(kwargs.get("project_type"), "generic")
        self.assertEqual(kwargs.get("node_version"), "24")
        self.assertEqual(kwargs.get("db_type"), "none")
        self.assertIn("--webimage-extra-packages=python3-setuptools,build-essential", kwargs.get("extra_args", []))

        mock_start.assert_called_once_with(ctx)
        mock_proxy.assert_called_once_with(ctx, port=5678)
        mock_daemon.assert_called_once_with(ctx, name="n8n-server", command="bash -lc 'npx n8n start'")
        mock_restart.assert_called_once()
        self.assertGreaterEqual(mock_run_cmd.call_count, 2)

    @patch.object(RecipeContext, "run_cmd", return_value=0)
    @patch.object(OpenClawRecipe, "restart_ddev")
    @patch.object(OpenClawRecipe, "setup_daemon")
    @patch.object(OpenClawRecipe, "setup_nginx_proxy")
    @patch.object(OpenClawRecipe, "start_ddev")
    @patch.object(OpenClawRecipe, "configure_ddev")
    def test_openclaw_recipe_execution(self, mock_cfg, mock_start, mock_proxy, mock_daemon, mock_restart, mock_run_cmd):
        recipe = OpenClawRecipe()
        ctx = RecipeContext(
            parent_window=None,
            raw_name="My OpenClaw",
            slug="my-openclaw",
            target_dir=self.test_dir,
            fw={"id": "openclaw", "name": "OpenClaw (Agente IA)", "nodejs": "24.22.1"},
            drupal_ver_info={},
            php_version="8.3",
            db_type="none",
            node_version="24.22.1",
            auto_install=True,
            is_multisite_enabled=False,
            dialog=None,
            primary_url="https://my-openclaw.ddev.site",
        )

        recipe.execute(ctx)

        mock_cfg.assert_called_once()
        args, kwargs = mock_cfg.call_args
        self.assertEqual(kwargs.get("project_type"), "generic")
        self.assertEqual(kwargs.get("node_version"), "24.22.1")
        self.assertEqual(kwargs.get("db_type"), "none")
        self.assertIn("--webimage-extra-packages=python3-setuptools,build-essential", kwargs.get("extra_args", []))

        mock_start.assert_called_once_with(ctx)
        mock_proxy.assert_called_once_with(ctx, port=18789)
        mock_daemon.assert_called_once_with(
            ctx,
            name="openclaw-gateway",
            command="bash -lc 'npx openclaw gateway run --port 18789 --bind loopback --auth none --allow-unconfigured'"
        )
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, ".openclaw", "openclaw.json")))
        mock_restart.assert_called_once()
        self.assertGreaterEqual(mock_run_cmd.call_count, 2)

    def test_detector_identifies_n8n_project(self):
        pkg_file = os.path.join(self.test_dir, "package.json")
        with open(pkg_file, "w") as f:
            json.dump({"name": "n8n-workflows", "dependencies": {"n8n": "^1.70.0"}}, f)

        details = detect_project_details(self.test_dir)
        self.assertEqual(details["type"], "n8n")
        self.assertIn("n8n", details["summary"])

    def test_detector_identifies_openclaw_project(self):
        pkg_file = os.path.join(self.test_dir, "package.json")
        with open(pkg_file, "w") as f:
            json.dump({"name": "my-agent", "dependencies": {"openclaw": "^1.0.0"}}, f)

        details = detect_project_details(self.test_dir)
        self.assertEqual(details["type"], "openclaw")
        self.assertIn("OpenClaw", details["summary"])

    def test_inspect_project_stack_identifies_n8n_and_openclaw(self):
        # n8n
        n8n_dir = os.path.join(self.test_dir, "n8n_proj")
        os.makedirs(n8n_dir, exist_ok=True)
        with open(os.path.join(n8n_dir, "package.json"), "w") as f:
            json.dump({"dependencies": {"n8n": "latest"}}, f)

        tech_type, has_db, is_php, is_python, is_js, is_static = inspect_project_stack(
            n8n_dir, {"name": "n8n-proj", "type": "generic"}, {}
        )
        self.assertEqual(tech_type, "n8n")

        # openclaw
        claw_dir = os.path.join(self.test_dir, "claw_proj")
        os.makedirs(claw_dir, exist_ok=True)
        with open(os.path.join(claw_dir, "package.json"), "w") as f:
            json.dump({"dependencies": {"openclaw": "latest"}}, f)

        tech_type_c, has_db_c, is_php_c, is_python_c, is_js_c, is_static_c = inspect_project_stack(
            claw_dir, {"name": "claw-proj", "type": "generic"}, {}
        )
        self.assertEqual(tech_type_c, "openclaw")


if __name__ == "__main__":
    unittest.main()

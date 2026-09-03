# -*- coding: utf-8 -*-
"""
Smoke tests for DDEV Studio modular package.
"""

import os
import sys
import logging
import unittest
import tempfile
import shutil

from ddev_studio.logger import setup_logger, logger


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
from ddev_studio.core.detector import (
    detect_project_details,
    inspect_project_stack,
    sanitize_project_name,
    detect_sqlite_database,
    read_ddev_config
)

from ddev_studio.core.terminal import find_terminal_command, build_terminal_args, open_terminal
from unittest.mock import patch



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

    def test_read_ddev_config_nonexistent(self):
        self.assertIsNone(read_ddev_config("/non/existent/path/12345"))
        self.assertIsNone(read_ddev_config(""))

    def test_read_ddev_config_structured_yaml(self):
        ddev_dir = os.path.join(self.test_dir, ".ddev")
        os.makedirs(ddev_dir, exist_ok=True)
        cfg_file = os.path.join(ddev_dir, "config.yaml")
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write("""# DDEV Configuration File
name: sample-project # inline comment
type: laravel
docroot: public
php_version: "8.3"
nodejs_version: '22'
database:
  type: postgres
  version: "16"
omit_containers:
  - db
""")
        cfg = read_ddev_config(self.test_dir)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("name"), "sample-project")
        self.assertEqual(cfg.get("type"), "laravel")
        self.assertEqual(cfg.get("docroot"), "public")
        self.assertEqual(str(cfg.get("php_version")), "8.3")
        self.assertIn("db", cfg.get("omit_containers", []))

        # Test detect_project_details using this config
        det = detect_project_details(self.test_dir)
        self.assertTrue(det["valid"])
        self.assertEqual(det["name"], "sample-project")
        self.assertEqual(det["type"], "laravel")
        self.assertEqual(det["docroot"], "public")
        self.assertEqual(det["db"], "none")

        # Test inspect_project_stack respecting omit_containers: [db]
        tech, has_db, is_php, is_py, is_js, is_static = inspect_project_stack(self.test_dir, {}, {})
        self.assertEqual(tech, "laravel")
        self.assertFalse(has_db)

    def test_read_ddev_config_inline_bracket_omit(self):
        ddev_dir = os.path.join(self.test_dir, ".ddev")
        os.makedirs(ddev_dir, exist_ok=True)
        cfg_file = os.path.join(ddev_dir, "config.yaml")
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write("""name: drupal-site
type: drupal10
docroot: web
php_version: 8.3
database:
  type: mariadb
  version: "10.11"
""")
        cfg = read_ddev_config(self.test_dir)
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.get("name"), "drupal-site")
        det = detect_project_details(self.test_dir)
        self.assertTrue(det["valid"])
        self.assertEqual(det["db"], "mariadb:10.11")
        self.assertTrue(det["is_drupal"])


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

    def test_build_terminal_args_no_command(self):
        args, cwd = build_terminal_args("mate-terminal", "/tmp/my project")
        self.assertEqual(args[0], "mate-terminal")
        self.assertIn("--working-directory=/tmp/my project", args)
        self.assertNotIn("-e", args)
        self.assertEqual(cwd, "/tmp/my project")

    def test_build_terminal_args_with_command_and_quotes(self):
        # Escaping test: command with single and double quotes
        cmd = "echo 'Hello DDEV' && echo \"Success\""
        args, cwd = build_terminal_args("mate-terminal", "/tmp/project", cmd)
        self.assertIn("-e", args)
        e_idx = args.index("-e")
        bash_arg = args[e_idx + 1]
        self.assertTrue(bash_arg.startswith("bash -c "))
        self.assertIn("exec bash", bash_arg)

    def test_build_terminal_args_generic_xterm(self):
        cmd = "drush status"
        args, cwd = build_terminal_args("/usr/bin/xterm", "/var/www/html", cmd)
        self.assertEqual(args[0], "/usr/bin/xterm")
        self.assertIn("-e", args)
        self.assertEqual(cwd, "/var/www/html")

    def test_build_terminal_args_konsole(self):
        cmd = "ddev ssh"
        args, cwd = build_terminal_args("konsole", "/home/user/project", cmd)
        self.assertEqual(args[0], "konsole")
        self.assertIn("--workdir", args)
        self.assertIn("/home/user/project", args)

    @patch("subprocess.Popen")
    @patch("ddev_studio.core.terminal.find_terminal_command", return_value="mate-terminal")
    def test_open_terminal_mock(self, mock_find, mock_popen):
        res = open_terminal("/tmp", "ls -la")
        self.assertIsNotNone(res)
        mock_popen.assert_called_once()
        call_args, call_kwargs = mock_popen.call_args
        self.assertEqual(call_kwargs["cwd"], "/tmp")



class TestCITemplates(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_git_repo_detection(self):
        from ddev_studio.core.ci_templates import detect_git_repo
        info = detect_git_repo(self.test_dir)
        self.assertFalse(info["has_git"])

    def test_workflow_generation(self):
        from ddev_studio.core.ci_templates import generate_ci_workflow, save_ci_workflow, detect_existing_workflows
        
        # 1. Drupal
        drupal_yml = generate_ci_workflow("drupal")
        self.assertIn("ddev/github-action", drupal_yml)
        
        # 2. Laravel
        laravel_yml = generate_ci_workflow("laravel")
        self.assertIn("artisan test", laravel_yml)
        
        # 3. Django
        django_yml = generate_ci_workflow("django")
        self.assertIn("pytest", django_yml)
        
        # 4. Next.js
        next_yml = generate_ci_workflow("nextjs")
        self.assertIn("npm", next_yml)
        
        # 5. Save workflow
        ok, path = save_ci_workflow(self.test_dir, drupal_yml, "ci.yml")
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(path))
        
        # 6. Detect existing
        wfs = detect_existing_workflows(self.test_dir)
        self.assertEqual(len(wfs), 1)
        self.assertEqual(wfs[0]["filename"], "ci.yml")


class TestImports(unittest.TestCase):
    def test_all_modules_importable(self):
        import ddev_studio
        import ddev_studio.constants
        import ddev_studio.core
        import ddev_studio.core.terminal
        import ddev_studio.core.process
        import ddev_studio.core.detector
        import ddev_studio.core.ci_templates
        import ddev_studio.core.drupal_tools
        import ddev_studio.recipes
        import ddev_studio.recipes.runner
        import ddev_studio.ui
        import ddev_studio.ui.helpers
        import ddev_studio.ui.dialogs.progress
        import ddev_studio.ui.dialogs.db_containers
        import ddev_studio.ui.dialogs.ci_dialog
        import ddev_studio.ui.dialogs.drupal_tools
        import ddev_studio.core.addons
        import ddev_studio.ui.views.details
        import ddev_studio.ui.views.subsites
        import ddev_studio.ui.views.drupal_tools
        import ddev_studio.ui.views.addons
        import ddev_studio.core.docker_monitor
        import ddev_studio.ui.views.docker_monitor
        import ddev_studio.ui.window
        import ddev_studio.main
        self.assertIsNotNone(ddev_studio.__version__)

    def test_drupal_tools_view_instantiation(self):
        from ddev_studio.ui.views.drupal_tools import DrupalToolsView
        view = DrupalToolsView(main_app=None)
        self.assertIsNotNone(view)
        
        # Test loading project
        demo_proj = {
            "name": "drupal-demo",
            "approot": "/tmp/drupal-demo",
            "docroot": "web"
        }
        view.load_project(demo_proj, from_view="details")
        self.assertEqual(view.project_name, "drupal-demo")
        self.assertEqual(view.from_view, "details")
        self.assertEqual(view.btn_back_lbl.get_text(), "Volver a Detalles")

    def test_addons_view_instantiation(self):
        from ddev_studio.ui.views.addons import AddonsMarketplaceView
        view = AddonsMarketplaceView(main_app=None)
        self.assertIsNotNone(view)
        demo_projects = [
            {"name": "demo-proj", "status": "running", "approot": "/tmp/demo-proj"}
        ]
        view.update_projects(demo_projects)
        self.assertEqual(len(view.projects), 1)

    def test_docker_monitor_view_instantiation(self):
        from ddev_studio.ui.views.docker_monitor import DockerMonitorView
        view = DockerMonitorView(main_app=None)
        self.assertIsNotNone(view)
        demo_projects = [
            {"name": "multisitio", "status": "running", "approot": "/tmp/multisitio"}
        ]
        view.update_projects(demo_projects)
        self.assertIn("multisitio", view.known_projects)
        view.stop_polling()

    def test_tools_view_instantiation(self):
        from ddev_studio.ui.views.tools import GlobalToolsView
        view = GlobalToolsView(main_app=None)
        self.assertIsNotNone(view)
        self.assertIsNotNone(view.docker_monitor_view)
        self.assertIsNotNone(view.lbl_system_info)

    def test_new_project_view_instantiation(self):
        from ddev_studio.ui.views.new_project import NewProjectView
        view = NewProjectView(main_app=None)
        self.assertIsNotNone(view)
        self.assertIsNotNone(view.flowbox_fw)
        self.assertIsNotNone(view.btn_mode_create)
        self.assertIsNotNone(view.btn_mode_import)
        self.assertTrue(view.btn_mode_create.get_active())
        view.switch_mode("import")
        self.assertTrue(view.btn_mode_import.get_active())



class TestLogger(unittest.TestCase):
    def test_setup_logger_default(self):
        log = setup_logger(verbose=False)
        self.assertEqual(log.name, "ddev_studio")
        self.assertTrue(len(log.handlers) > 0)

    def test_setup_logger_debug(self):
        log = setup_logger(verbose=True)
        self.assertEqual(log.level, logging.DEBUG)

    def test_setup_logger_env(self):
        with patch.dict(os.environ, {"DDEV_STUDIO_DEBUG": "1"}):
            log = setup_logger()
            self.assertEqual(log.level, logging.DEBUG)


class TestRecipesStrategy(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_recipe_registry(self):
        from ddev_studio.recipes import get_recipe
        from ddev_studio.recipes.php import DrupalRecipe, WordPressRecipe, LaravelRecipe, GenericPhpRecipe
        from ddev_studio.recipes.node import NextjsRecipe, ReactRecipe
        from ddev_studio.recipes.python import DjangoRecipe, FlaskRecipe

        self.assertIsInstance(get_recipe("drupal"), DrupalRecipe)
        self.assertIsInstance(get_recipe("wordpress"), WordPressRecipe)
        self.assertIsInstance(get_recipe("laravel"), LaravelRecipe)
        self.assertIsInstance(get_recipe("nextjs"), NextjsRecipe)
        self.assertIsInstance(get_recipe("react"), ReactRecipe)
        self.assertIsInstance(get_recipe("django"), DjangoRecipe)
        self.assertIsInstance(get_recipe("flask"), FlaskRecipe)
        self.assertIsInstance(get_recipe("unknown-fw"), GenericPhpRecipe)

    def test_recipe_templates_helpers(self):
        from ddev_studio.recipes import get_recipe, RecipeContext

        recipe = get_recipe("nextjs")
        ctx = RecipeContext(
            parent_window=None,
            raw_name="test-app",
            slug="test-app",
            target_dir=self.test_dir,
            fw={"id": "nextjs", "name": "Next.js"},
            drupal_ver_info={},
            php_version="8.3",
            db_type="none",
            node_version="22",
            auto_install=False,
            is_multisite_enabled=False,
            dialog=None,
            primary_url="https://test-app.ddev.site"
        )
        recipe.setup_nginx_proxy(ctx, port=3000)
        proxy_conf = os.path.join(self.test_dir, ".ddev", "nginx_full", "nginx-site.conf")
        self.assertTrue(os.path.exists(proxy_conf))
        with open(proxy_conf, "r") as f:
            content = f.read()
        self.assertIn("127.0.0.1:3000", content)

        recipe.setup_daemon(ctx, name="test-daemon", command="npm start")
        daemon_conf = os.path.join(self.test_dir, ".ddev", "config.daemon.yaml")
        self.assertTrue(os.path.exists(daemon_conf))
        with open(daemon_conf, "r") as f:
            d_content = f.read()
        self.assertIn("name: test-daemon", d_content)
        self.assertIn('command: "npm start"', d_content)


if __name__ == "__main__":
    unittest.main()



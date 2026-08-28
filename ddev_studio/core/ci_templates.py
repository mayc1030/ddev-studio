# -*- coding: utf-8 -*-
"""
Motor de generación de plantillas de Integración Continua (CI/CD) con GitHub Actions
personalizadas para frameworks web y proyectos DDEV.
"""

import os
import re
import subprocess


def detect_git_repo(approot):
    """
    Determina si un proyecto tiene inicializado un repositorio Git y extrae su URL remota y rama actual.
    """
    if not approot or not os.path.exists(approot):
        return {"has_git": False, "remote_url": "", "github_url": "", "branch": ""}
        
    git_dir = os.path.join(approot, ".git")
    if not os.path.exists(git_dir):
        return {"has_git": False, "remote_url": "", "github_url": "", "branch": ""}
        
    branch = "main"
    remote_url = ""
    github_url = ""
    
    try:
        # Get current branch
        res_b = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=approot,
            capture_output=True,
            text=True,
            timeout=2
        )
        if res_b.returncode == 0 and res_b.stdout.strip():
            branch = res_b.stdout.strip()
            
        # Get origin remote URL
        res_r = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=approot,
            capture_output=True,
            text=True,
            timeout=2
        )
        if res_r.returncode == 0 and res_r.stdout.strip():
            remote_url = res_r.stdout.strip()
            # Parse GitHub URL
            if "github.com" in remote_url:
                gh_clean = remote_url
                if gh_clean.startswith("git@github.com:"):
                    gh_clean = gh_clean.replace("git@github.com:", "https://github.com/")
                if gh_clean.endswith(".git"):
                    gh_clean = gh_clean[:-4]
                github_url = gh_clean
    except Exception:
        pass
        
    return {
        "has_git": True,
        "remote_url": remote_url,
        "github_url": github_url,
        "branch": branch
    }


def detect_existing_workflows(approot):
    """
    Busca flujos de trabajo de GitHub Actions existentes en .github/workflows/
    """
    workflows = []
    if not approot or not os.path.exists(approot):
        return workflows
        
    wf_dir = os.path.join(approot, ".github", "workflows")
    if os.path.isdir(wf_dir):
        for f in sorted(os.listdir(wf_dir)):
            if f.endswith(".yml") or f.endswith(".yaml"):
                full_p = os.path.join(wf_dir, f)
                workflows.append({
                    "filename": f,
                    "rel_path": os.path.join(".github", "workflows", f),
                    "full_path": full_p
                })
    return workflows


def generate_ci_workflow(tech_type, options=None):
    """
    Genera el contenido YAML del workflow de GitHub Actions adaptado a la tecnología.
    """
    options = options or {}
    include_tests = options.get("include_tests", True)
    include_lint = options.get("include_lint", True)
    include_security = options.get("include_security", True)
    use_ddev_action = options.get("use_ddev_action", True)
    
    tech_lower = (tech_type or "generic").lower()
    
    # 1. DRUPAL (con ddev/github-action)
    if "drupal" in tech_lower:
        if use_ddev_action:
            steps = """    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up DDEV environment
        uses: ddev/github-action@v1
        with:
          ddev-version: stable

      - name: Start DDEV
        run: ddev start -y
"""
            if include_tests:
                steps += """
      - name: Run Drupal Tests & Status Checks
        run: |
          ddev drush status
          if [ -f vendor/bin/phpunit ]; then
            ddev exec vendor/bin/phpunit -c web/core --testsuite=unit || true
          fi
"""
            if include_lint:
                steps += """
      - name: Run Code Style & Linter (PHPCS)
        run: |
          if [ -f vendor/bin/phpcs ]; then
            ddev exec vendor/bin/phpcs --standard=Drupal,DrupalPractice web/modules/custom || true
          fi
"""
            if include_security:
                steps += """
      - name: Security & Vulnerabilities Audit
        run: ddev composer audit
"""
            return f"""name: CI - Drupal

on:
  push:
    branches: [ "main", "master", "develop" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  drupal-ci:
    name: Drupal CI (DDEV Environment)
    runs-on: ubuntu-latest

{steps}"""
        else:
            return """name: CI - Drupal PHP

on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          extensions: mbstring, xml, ctype, iconv, mysql, gd
      - name: Validate composer.json
        run: composer validate --strict
      - name: Install dependencies
        run: composer install --prefer-dist --no-progress
      - name: Security Audit
        run: composer audit
"""

    # 2. LARAVEL
    elif "laravel" in tech_lower:
        return """name: CI - Laravel

on:
  push:
    branches: [ "main", "master", "develop" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  laravel-tests:
    name: Tests & Code Quality (PHP 8.3)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          extensions: mbstring, dom, fileinfo, mysql, sqlite3, pdo_sqlite, bcmath
          coverage: none

      - name: Copy .env
        run: php -r "file_exists('.env') || copy('.env.example', '.env');"

      - name: Install Dependencies
        run: composer install -q --no-ansi --no-interaction --no-scripts --no-progress --prefer-dist

      - name: Generate key
        run: php artisan key:generate

      - name: Set Directory Permissions
        run: chmod -R 777 storage bootstrap/cache

      - name: Create SQLite Database
        run: |
          mkdir -p database
          touch database/database.sqlite

      - name: Execute Tests (PHPUnit / Pest)
        env:
          DB_CONNECTION: sqlite
          DB_DATABASE: database/database.sqlite
        run: php artisan test

      - name: Security Audit
        run: composer audit || true
"""

    # 3. WORDPRESS
    elif "wordpress" in tech_lower:
        return """name: CI - WordPress

on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  wordpress-ci:
    name: WordPress Test & Validation
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: '8.2'
          extensions: mysqli, zip, gd, mbstring

      - name: Check PHP Syntax
        run: find . -name "*.php" -not -path "./wp-content/uploads/*" -exec php -l {} +
"""

    # 4. SYMFONY
    elif "symfony" in tech_lower:
        return """name: CI - Symfony

on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  symfony-tests:
    name: Symfony Tests (PHP 8.3)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - name: Setup PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          extensions: mbstring, xml, ctype, iconv, intl, pdo_sqlite
      - name: Validate composer.json
        run: composer validate --strict
      - name: Install dependencies
        run: composer install --prefer-dist --no-progress
      - name: Security Audit
        run: composer audit
      - name: Run Tests
        run: |
          if [ -f bin/phpunit ]; then
            bin/phpunit
          fi
"""

    # 5. DJANGO / FLASK / PYTHON
    elif any(k in tech_lower for k in ["django", "flask", "python", "fastapi"]):
        framework_title = "Django" if "django" in tech_lower else ("Flask" if "flask" in tech_lower else "Python")
        return f"""name: CI - {framework_title}

on:
  push:
    branches: [ "main", "master", "develop" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  python-ci:
    name: Tests & Lint (Python 3.12)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest flake8

      - name: Lint with flake8
        run: |
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

      - name: Run Tests
        run: |
          if [ -f manage.py ]; then
            python manage.py test
          else
            pytest || true
          fi
"""

    # 6. NODE.JS (Next.js, React, Vue, Angular)
    elif any(k in tech_lower for k in ["next", "react", "vue", "angular", "node", "nuxt", "svelte"]):
        framework_title = tech_type.upper() if tech_type else "Node.js"
        return f"""name: CI - {framework_title}

on:
  push:
    branches: [ "main", "master", "develop" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  node-ci:
    name: Build, Lint & Test (Node.js 22)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: 'npm'

      - name: Install dependencies
        run: npm ci || npm install

      - name: Run Linter
        run: npm run lint --if-present

      - name: Run Tests
        run: npm test --if-present

      - name: Build Project
        run: npm run build --if-present
"""

    # 7. GENERIC PHP / DEFAULT
    else:
        return """name: CI - PHP Project

on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  php-ci:
    name: PHP Validation (8.3)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          extensions: mbstring, xml, ctype, iconv, pdo, gd

      - name: Validate composer.json
        run: |
          if [ -f composer.json ]; then
            composer validate --strict
            composer install --prefer-dist --no-progress
            composer audit || true
          fi

      - name: Check PHP Syntax
        run: find . -name "*.php" -not -path "./vendor/*" -exec php -l {} +
"""


def save_ci_workflow(approot, content, filename="ci.yml"):
    """
    Guarda el archivo de workflow en .github/workflows/<filename>
    """
    if not approot or not os.path.exists(approot):
        return False, "Directorio del proyecto no encontrado"
        
    wf_dir = os.path.join(approot, ".github", "workflows")
    os.makedirs(wf_dir, exist_ok=True)
    target_file = os.path.join(wf_dir, filename)
    
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
        return True, target_file
    except Exception as ex:
        return False, str(ex)

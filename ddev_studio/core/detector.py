# -*- coding: utf-8 -*-
"""
Detección inteligente de proyectos locales, tecnologías, docroots, pilas de ejecución y configuraciones DDEV.
"""

import json
import os
import re
from typing import Optional, Dict, Any

from ddev_studio.logger import logger

try:
    import yaml
except ImportError:
    yaml = None



def read_ddev_config(folder_or_path: str) -> Optional[Dict[str, Any]]:
    """
    Lee y parsea de forma estructurada y segura el archivo .ddev/config.yaml de un proyecto.
    Utiliza yaml.safe_load cuando PyYAML está disponible, con fallback tolerante a fallos.
    Retorna un diccionario con la configuración o None si no existe o es inválido.
    """
    if not folder_or_path:
        return None

    cfg_path = folder_or_path
    if not cfg_path.endswith("config.yaml") and not cfg_path.endswith("config.yml"):
        cfg_path = os.path.join(folder_or_path, ".ddev", "config.yaml")
        if not os.path.exists(cfg_path):
            cfg_path = os.path.join(folder_or_path, ".ddev", "config.yml")

    if not os.path.isfile(cfg_path):
        return None

    try:
        with open(cfg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if yaml is not None:
            try:
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as ex:
                logger.debug(f"PyYAML no pudo parsear {cfg_path}, aplicando parser resiliente: {ex}")


        # Fallback tolerante si yaml falla o no está instalado
        data: Dict[str, Any] = {}
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Remover comentarios inline si las comillas están balanceadas
            if "#" in stripped:
                parts = stripped.split("#", 1)
                if parts[0].count('"') % 2 == 0 and parts[0].count("'") % 2 == 0:
                    stripped = parts[0].strip()
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"\'')
                if k and v:
                    data[k] = v

        # Extracción adicional para estructura anidada de database
        m_db = re.search(r'^\s*database:\s*\n\s*type:\s*([^\s#]+)', content, re.MULTILINE)
        m_db_ver = re.search(r'^\s*database:\s*\n(?:\s*type:\s*[^\s#]+\n)?\s*version:\s*([^\s#]+)', content, re.MULTILINE)
        if m_db:
            data["database"] = {
                "type": m_db.group(1).strip().strip('"\''),
                "version": m_db_ver.group(1).strip().strip('"\'') if m_db_ver else ""
            }

        # Extracción adicional para omit_containers
        m_omit = re.search(r'^\s*omit_containers:\s*\[(.*?)\]', content, re.MULTILINE)
        if m_omit:
            data["omit_containers"] = [x.strip().strip('"\'') for x in m_omit.group(1).split(",") if x.strip()]
        else:
            m_omit_list = re.findall(r'^\s*-\s*([^\s#]+)', content, re.MULTILINE)
            if "omit_containers:" in content and m_omit_list:
                data["omit_containers"] = m_omit_list

        return data if data else None
    except Exception as ex:
        logger.debug(f"Error leyendo configuración DDEV en {cfg_path}: {ex}")
        return None



def sanitize_project_name(raw_name: str) -> str:
    """
    Sanitiza el nombre del proyecto para que sea un hostname DNS RFC 1123 válido para DDEV
    (solo caracteres alfanuméricos en minúsculas y guiones, sin guiones bajos ni guiones al inicio/final).
    """
    if not raw_name:
        return ""
    slug = str(raw_name).replace("_", "-")
    slug = re.sub(r'[^a-zA-Z0-9-]', '-', slug).lower()
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def detect_project_details(folder_path):
    """
    Analiza un directorio local y autodetecta el framework, docroot, versiones de PHP/Node y base de datos.
    """
    if not folder_path or not os.path.exists(folder_path):
        return {
            "name": "",
            "type": "drupal10",
            "docroot": "docroot",
            "php": "8.3",
            "nodejs": "22",
            "db": "mariadb:10.11",
            "is_drupal": True,
            "is_multisite": True,
            "summary": "Directorio no encontrado",
            "valid": False
        }

    pname = os.path.basename(folder_path.rstrip("/"))
    slug = sanitize_project_name(pname)

    # 1. Detect Docroot
    docroot = "."
    for dr in ["docroot", "web", "public", "dist"]:
        if os.path.isdir(os.path.join(folder_path, dr)):
            docroot = dr
            break

    # 2. Check if .ddev/config.yaml exists
    cfg = read_ddev_config(folder_path)
    if cfg:
        p_type = str(cfg.get("type") or "drupal10").strip()
        cfg_name = cfg.get("name")
        if cfg_name:
            slug = sanitize_project_name(str(cfg_name))
        docroot = str(cfg.get("docroot") or docroot).strip()
        php_v = str(cfg.get("php_version") or "8.3").strip()
        node_v = str(cfg.get("nodejs_version") or "22").strip()

        # Parse database
        omit = cfg.get("omit_containers") or []
        if isinstance(omit, str):
            omit = [omit]

        db_conf = cfg.get("database")
        if "db" in omit:
            db_v = "none"
        elif isinstance(db_conf, dict):
            db_type = str(db_conf.get("type", "mariadb")).strip()
            db_ver = str(db_conf.get("version", "10.11")).strip()
            if db_type.lower() in ["none", "", "null"]:
                db_v = "none"
            elif db_ver:
                db_v = f"{db_type}:{db_ver}"
            else:
                db_v = db_type
        elif isinstance(db_conf, str) and db_conf.strip():
            db_v = db_conf.strip()
        else:
            db_v = "mariadb:10.11"

        is_dr = "drupal" in p_type
        return {
            "name": slug,
            "type": p_type,
            "docroot": docroot,
            "php": php_v,
            "nodejs": node_v,
            "db": db_v,
            "is_drupal": is_dr,
            "is_multisite": is_dr,
            "summary": f"Configuración DDEV detectada ({p_type}, docroot: {docroot})",
            "valid": True
        }


    # 3. Check composer.json
    composer_file = os.path.join(folder_path, "composer.json")
    if os.path.exists(composer_file):
        try:
            with open(composer_file, "r") as f:
                cdata = json.load(f)
            req = cdata.get("require", {})
            req_dev = cdata.get("require-dev", {})
            all_req = {**req, **req_dev}
            
            for k, v in all_req.items():
                if "drupal/core" in k:
                    if "11" in str(v):
                        return {"name": slug, "type": "drupal11", "docroot": docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Drupal 11 detectado (docroot: {docroot})", "valid": True}
                    elif "9" in str(v):
                        return {"name": slug, "type": "drupal9", "docroot": docroot, "php": "8.1", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Drupal 9 detectado (docroot: {docroot})", "valid": True}
                    elif "8" in str(v):
                        return {"name": slug, "type": "drupal8", "docroot": docroot, "php": "7.4", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Drupal 8 detectado (docroot: {docroot})", "valid": True}
                    else:
                        return {"name": slug, "type": "drupal10", "docroot": docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Drupal 10 detectado (docroot: {docroot})", "valid": True}
                        
            if "laravel/framework" in all_req:
                return {"name": slug, "type": "laravel", "docroot": "public" if os.path.exists(os.path.join(folder_path, "public")) else docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "Laravel detectado", "valid": True}
            if "symfony/" in str(all_req):
                return {"name": slug, "type": "symfony", "docroot": "public" if os.path.exists(os.path.join(folder_path, "public")) else docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "Symfony detectado", "valid": True}
            if "roots/bedrock" in all_req or "wordpress" in str(all_req):
                return {"name": slug, "type": "wordpress", "docroot": docroot, "php": "8.2", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "WordPress (Composer) detectado", "valid": True}
        except Exception as ex:
            logger.debug(f"Error procesando composer.json en {folder_path}: {ex}")


    # 4. Check filesystem structures
    if os.path.exists(os.path.join(folder_path, docroot, "sites")) or os.path.exists(os.path.join(folder_path, "sites", "default")):
        return {"name": slug, "type": "drupal10", "docroot": docroot, "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": True, "is_multisite": True, "summary": f"Estructura Drupal detectada (docroot: {docroot})", "valid": True}
    if os.path.exists(os.path.join(folder_path, "wp-config.php")) or os.path.exists(os.path.join(folder_path, "wp-content")):
        return {"name": slug, "type": "wordpress", "docroot": ".", "php": "8.2", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "WordPress detectado", "valid": True}
    if os.path.exists(os.path.join(folder_path, "artisan")):
        return {"name": slug, "type": "laravel", "docroot": "public", "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "Laravel detectado", "valid": True}
    if os.path.exists(os.path.join(folder_path, "angular.json")):
        return {"name": slug, "type": "angular", "docroot": "dist", "php": "8.2", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Angular detectado (Node.js/Vite)", "valid": True}
    if os.path.exists(os.path.join(folder_path, "manage.py")):
        return {"name": slug, "type": "django", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "postgres:16", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Django detectado (Python 3)", "valid": True}
    if os.path.exists(os.path.join(folder_path, "app.py")) or os.path.exists(os.path.join(folder_path, "wsgi.py")):
        return {"name": slug, "type": "flask", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "mariadb:10.11", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Flask detectado (Python 3)", "valid": True}

    if os.path.exists(os.path.join(folder_path, "next.config.js")) or os.path.exists(os.path.join(folder_path, "next.config.mjs")) or os.path.exists(os.path.join(folder_path, "next.config.ts")):
        return {"name": slug, "type": "nextjs", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Next.js detectado (React Full-Stack)", "valid": True}

    if os.path.exists(os.path.join(folder_path, "package.json")) and not os.path.exists(os.path.join(folder_path, "composer.json")):
        try:
            with open(os.path.join(folder_path, "package.json"), "r") as pf:
                pdata = json.load(pf)
            all_deps = {**pdata.get("dependencies", {}), **pdata.get("devDependencies", {})}
            if "next" in all_deps:
                return {"name": slug, "type": "nextjs", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Next.js detectado (React Full-Stack)", "valid": True}
            if "react" in all_deps:
                return {"name": slug, "type": "react", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto React detectado (Vite/Node)", "valid": True}
            if "vue" in all_deps:
                return {"name": slug, "type": "vue", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Vue detectado (Vite/Node)", "valid": True}
        except Exception as ex:
            logger.debug(f"Error procesando package.json en {folder_path}: {ex}")
        return {"name": slug, "type": "generic", "docroot": ".", "php": "8.3", "nodejs": "22", "db": "none", "is_drupal": False, "is_multisite": False, "summary": "Proyecto Node.js / Frontend detectado", "valid": True}


    return {
        "name": slug,
        "type": "php",
        "docroot": docroot,
        "php": "8.3",
        "nodejs": "22",
        "db": "mariadb:10.11",
        "is_drupal": False,
        "is_multisite": False,
        "summary": f"Proyecto PHP estándar (docroot: {docroot})",
        "valid": True
    }


def inspect_project_stack(approot, raw_data, proj_dict):
    """
    Inspecciona archivos de proyecto, dependencias, package.json, composer.json y configuración DDEV
    para detectar con precisión el framework, uso de base de datos y entorno de ejecución.
    """
    pname = raw_data.get("name") or proj_dict.get("name", "")
    ddev_type = (raw_data.get("type") or proj_dict.get("type", "generic")).lower()
    tech_type = ddev_type
    has_db = True
    
    # 1. Inspect ddev config if approot exists
    if approot and os.path.exists(approot):
        cfg = read_ddev_config(approot)
        if cfg:
            if ddev_type in ["generic", ""] and cfg.get("type"):
                ddev_type = str(cfg.get("type")).strip().lower()
                tech_type = ddev_type
            omit = cfg.get("omit_containers") or []
            if isinstance(omit, str):
                omit = [omit]
            if "db" in omit:
                has_db = False
            db_conf = cfg.get("database")
            if isinstance(db_conf, dict):
                if str(db_conf.get("type", "")).strip().lower() in ["none", "", "null"]:
                    has_db = False
            elif isinstance(db_conf, str) and db_conf.strip().lower() in ["none", "", "null"]:
                has_db = False


                
        # 2. Check package.json for Frontend JS frameworks
        if os.path.exists(os.path.join(approot, "next.config.js")) or os.path.exists(os.path.join(approot, "next.config.mjs")) or os.path.exists(os.path.join(approot, "next.config.ts")):
            tech_type = "nextjs"
            
        pkg_json = os.path.join(approot, "package.json")
        if os.path.exists(pkg_json):
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    pdata = json.load(f)
                deps = {**pdata.get("dependencies", {}), **pdata.get("devDependencies", {})}
                if "next" in deps:
                    tech_type = "nextjs"
                elif "@angular/core" in deps or "@angular/cli" in deps:
                    tech_type = "angular"
                elif "react" in deps or "react-dom" in deps:
                    tech_type = "react"
                elif "vue" in deps:
                    tech_type = "vue"
                elif "nuxt" in deps:
                    tech_type = "nuxt"
                elif "svelte" in deps:
                    tech_type = "svelte"
                elif "astro" in deps:
                    tech_type = "astro"
            except Exception as ex:
                logger.debug(f"Error leyendo dependencias de package.json en {approot}: {ex}")

                
        # 3. Check Python indicators (Django, Flask, FastAPI)
        if os.path.exists(os.path.join(approot, "manage.py")):
            tech_type = "django"
        else:
            py_candidates = ["app.py", "main.py", "wsgi.py", "server.py", "application.py"]
            for py_f in py_candidates:
                py_path = os.path.join(approot, py_f)
                if os.path.exists(py_path):
                    try:
                        with open(py_path, "r", encoding="utf-8", errors="ignore") as f:
                            py_code = f.read(4096).lower()
                        if "flask" in py_code:
                            tech_type = "flask"
                            break
                        elif "fastapi" in py_code:
                            tech_type = "fastapi"
                            break
                        elif "django" in py_code:
                            tech_type = "django"
                            break
                        else:
                            tech_type = "python"
                    except Exception:
                        tech_type = "python"
                        
            req_file = os.path.join(approot, "requirements.txt")
            if os.path.exists(req_file):
                try:
                    with open(req_file, "r", encoding="utf-8", errors="ignore") as f:
                        req_text = f.read().lower()
                    if "flask" in req_text:
                        tech_type = "flask"
                    elif "fastapi" in req_text:
                        tech_type = "fastapi"
                    elif "django" in req_text:
                        tech_type = "django"
                    elif tech_type == ddev_type:
                        tech_type = "python"
                except Exception as ex:
                    logger.debug(f"Error inspeccionando requirements.txt en {approot}: {ex}")

                
        # 4. Check composer.json for PHP frameworks
        composer_file = os.path.join(approot, "composer.json")
        if os.path.exists(composer_file):
            try:
                with open(composer_file, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                creq = {**cdata.get("require", {}), **cdata.get("require-dev", {})}
                if "drupal/core" in creq or "drupal/core-recommended" in creq:
                    tech_type = "drupal"
                elif "laravel/framework" in creq:
                    tech_type = "laravel"
                elif "symfony/framework-bundle" in creq:
                    tech_type = "symfony"
                elif "roots/bedrock" in creq or "wordpress" in pname.lower():
                    tech_type = "wordpress"
            except Exception as ex:
                logger.debug(f"Error leyendo composer.json en {approot}: {ex}")


    # Name-based fallback for created projects
    pname_lower = pname.lower()
    for cand in ["angular", "react", "vue", "nextjs", "nuxt", "svelte", "django", "flask", "fastapi", "laravel", "symfony", "wordpress", "drupal"]:
        if cand in pname_lower and tech_type in ["generic", "php", "default", "python"]:
            tech_type = cand
            break
            
    is_python = any(k in tech_type for k in ["python", "django", "flask", "fastapi"])
    is_js = any(k in tech_type for k in ["angular", "react", "vue", "next", "nuxt", "node", "express", "svelte", "astro"])
    is_static = (tech_type in ["html", "static", "apache", "nginx"])
    is_php = not (is_python or is_js or is_static)
    
    # 5. Check DDEV describe data for DB container status
    database_type = (raw_data.get("database_type") or "").lower()
    if database_type in ["none", "empty", "null"]:
        has_db = False

    # Pure frontend / static apps don't have database
    if is_js or is_static:
        has_db = False
        
    return tech_type, has_db, is_php, is_python, is_js, is_static


def detect_sqlite_database(approot):
    """
    Busca si el proyecto utiliza una base de datos SQLite local y retorna su ruta relativa y tamaño si existe.
    """
    if not approot or not os.path.exists(approot):
        return None
        
    candidates = [
        "database/database.sqlite",
        "database.sqlite",
        "db.sqlite3",
        "app.db",
        "dev.db",
        "prisma/dev.db",
        "instance/app.db",
        "data.db"
    ]
    for c in candidates:
        full_p = os.path.join(approot, c)
        if os.path.isfile(full_p):
            size_bytes = os.path.getsize(full_p)
            size_kb = round(size_bytes / 1024, 1)
            return {
                "rel_path": c,
                "full_path": full_p,
                "size_kb": size_kb,
                "size_human": f"{size_kb} KB" if size_kb < 1024 else f"{round(size_kb/1024, 2)} MB"
            }
            
    # Check .env for sqlite
    env_p = os.path.join(approot, ".env")
    if os.path.exists(env_p):
        try:
            with open(env_p, "r", encoding="utf-8", errors="ignore") as ef:
                content = ef.read()
            if "DB_CONNECTION=sqlite" in content or "sqlite:" in content.lower():
                return {
                    "rel_path": "database.sqlite (según .env)",
                    "full_path": "",
                    "size_kb": 0,
                    "size_human": "SQLite"
                }
        except Exception:
            pass
    return None

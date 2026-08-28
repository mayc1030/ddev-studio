# -*- coding: utf-8 -*-
"""
Detección inteligente de proyectos locales, tecnologías, docroots, pilas de ejecución y configuraciones DDEV.
"""

import json
import os
import re


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
    ddev_cfg = os.path.join(folder_path, ".ddev", "config.yaml")
    if os.path.exists(ddev_cfg):
        try:
            with open(ddev_cfg, "r") as f:
                content = f.read()
            m_name = re.search(r'^name:\s*([^\s]+)', content, re.MULTILINE)
            m_type = re.search(r'^type:\s*([^\s]+)', content, re.MULTILINE)
            m_docroot = re.search(r'^docroot:\s*([^\s]+)', content, re.MULTILINE)
            m_php = re.search(r'^php_version:\s*([^\s]+)', content, re.MULTILINE)
            m_node = re.search(r'^nodejs_version:\s*([^\s]+)', content, re.MULTILINE)
            m_db = re.search(r'^database:\s*\n\s*type:\s*([^\s]+)', content, re.MULTILINE)
            
            p_type = m_type.group(1).strip().strip('"\'') if m_type else "drupal10"
            if m_name:
                slug = m_name.group(1).strip().strip('"\'')
            if m_docroot:
                docroot = m_docroot.group(1).strip().strip('"\'')
            php_v = m_php.group(1).strip().strip('"\'') if m_php else "8.3"
            node_v = m_node.group(1).strip().strip('"\'') if m_node else "22"
            db_v = m_db.group(1).strip().strip('"\'') if m_db else "mariadb:10.11"
            if "omit_containers" in content and "db" in content:
                db_v = "none"
            
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
        except Exception:
            pass

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
        except Exception:
            pass

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
        except Exception:
            pass
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
        ddev_cfg = os.path.join(approot, ".ddev", "config.yaml")
        if os.path.exists(ddev_cfg):
            try:
                with open(ddev_cfg, "r", encoding="utf-8") as f:
                    cfg_text = f.read()
                    
                # Check omit_containers for db
                m_omit = re.search(r"^\s*omit_containers:\s*\[(.*?)\]", cfg_text, re.MULTILINE)
                if m_omit and "db" in m_omit.group(1):
                    has_db = False
                    
                # Check database type
                m_db_type = re.search(r"^\s*database:\s*\n\s*type:\s*([^\s]+)", cfg_text, re.MULTILINE)
                if m_db_type and m_db_type.group(1).strip().strip('"\'').lower() in ["", "none", "null"]:
                    has_db = False
            except Exception:
                pass
                
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
            except Exception:
                pass
                
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
                except Exception:
                    pass
                
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
            except Exception:
                pass

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

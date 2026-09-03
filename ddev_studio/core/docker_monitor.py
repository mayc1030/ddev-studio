# -*- coding: utf-8 -*-
"""
Módulo core para la inspección, parsing y agregación de métricas de rendimiento
en tiempo real de contenedores Docker y proyectos DDEV.
"""

import json
import re
import subprocess
from typing import Dict, List, Tuple, Any, Optional


def parse_bytes_str(val: str) -> float:
    """
    Convierte cadenas de tamaño con sufijos (B, kB, MB, MiB, GB, GiB, etc.) a bytes numéricos.
    Ejemplos: '188.6MiB' -> 197761433.6, '31.2GiB' -> 33499424358.4, '74.8kB' -> 74800.0
    """
    if not val or not isinstance(val, str):
        return 0.0
        
    val = val.strip().replace(",", "")
    match = re.match(r'^([\d.]+)\s*([a-zA-Z]+)?$', val)
    if not match:
        return 0.0
        
    num = float(match.group(1))
    unit = (match.group(2) or "B").lower()
    
    multipliers = {
        "b": 1.0,
        "k": 1000.0,
        "kb": 1000.0,
        "kib": 1024.0,
        "m": 1000.0 ** 2,
        "mb": 1000.0 ** 2,
        "mib": 1024.0 ** 2,
        "g": 1000.0 ** 3,
        "gb": 1000.0 ** 3,
        "gib": 1024.0 ** 3,
        "t": 1000.0 ** 4,
        "tb": 1000.0 ** 4,
        "tib": 1024.0 ** 4,
    }
    
    return num * multipliers.get(unit, 1.0)


def format_bytes(num_bytes: float) -> str:
    """
    Formatea un valor en bytes a una representación legible (B, KiB, MiB, GiB).
    """
    if num_bytes < 1024:
        return f"{num_bytes:.0f} B"
    elif num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.1f} KiB"
    elif num_bytes < 1024 ** 3:
        return f"{num_bytes / (1024 ** 2):.1f} MiB"
    else:
        return f"{num_bytes / (1024 ** 3):.2f} GiB"


def parse_cpu_percent(val: str) -> float:
    """
    Parsea cadenas como '0.36%' o '12.50%' a un número flotante.
    """
    if not val:
        return 0.0
    try:
        clean = str(val).replace("%", "").strip()
        return float(clean)
    except Exception:
        return 0.0


def parse_memory_usage(val: str) -> Dict[str, Any]:
    """
    Parsea '188.6MiB / 31.2GiB' extrayendo bytes usados, límite total y porcentaje.
    """
    result = {
        "used_bytes": 0.0,
        "limit_bytes": 0.0,
        "used_str": "0 B",
        "limit_str": "0 B",
        "percent": 0.0
    }
    if not val or "/" not in val:
        return result
        
    parts = val.split("/")
    if len(parts) == 2:
        u_str = parts[0].strip()
        l_str = parts[1].strip()
        u_bytes = parse_bytes_str(u_str)
        l_bytes = parse_bytes_str(l_str)
        pct = (u_bytes / l_bytes * 100.0) if l_bytes > 0 else 0.0
        
        result["used_bytes"] = u_bytes
        result["limit_bytes"] = l_bytes
        result["used_str"] = u_str
        result["limit_str"] = l_str
        result["percent"] = round(pct, 2)
        
    return result


def identify_container_project(container_name: str) -> Tuple[str, str, str]:
    """
    Clasifica un contenedor identificando si pertenece a un proyecto DDEV, al sistema DDEV o es externo.
    Retorna: (project_name, service_name, container_scope)
    scope puede ser: 'project', 'system', o 'external'.
    
    Ejemplos:
      'ddev-multisitio-web' -> ('multisitio', 'web', 'project')
      'ddev-multisitio-db'  -> ('multisitio', 'db', 'project')
      'ddev-router'         -> ('DDEV Sistema', 'router', 'system')
      'ddev-ssh-agent'      -> ('DDEV Sistema', 'ssh-agent', 'system')
      'portainer'           -> ('Otros Contenedores', 'portainer', 'external')
    """
    if not container_name:
        return ("Desconocido", "desconocido", "external")
        
    name = container_name.strip()
    
    if name in ["ddev-router", "ddev-ssh-agent"]:
        service = name.replace("ddev-", "")
        return ("DDEV Sistema", service, "system")
        
    if name.startswith("ddev-"):
        # Formato: ddev-<project>-<service>
        parts = name[5:].split("-")
        if len(parts) >= 2:
            service = parts[-1]
            project = "-".join(parts[:-1])
            return (project, service, "project")
        elif len(parts) == 1:
            return (parts[0], "web", "project")
            
    return ("Otros Contenedores", name, "external")


def get_live_docker_stats(timeout: int = 5) -> Dict[str, Any]:
    """
    Ejecuta `docker stats --no-stream --format '{{json .}}'` y estructura las métricas
    tanto a nivel global como agrupadas por proyecto DDEV.
    """
    response: Dict[str, Any] = {
        "is_docker_available": False,
        "error_message": "",
        "containers": [],
        "projects": {},
        "global_summary": {
            "total_cpu_pct": 0.0,
            "total_mem_bytes": 0.0,
            "total_mem_limit_bytes": 0.0,
            "total_mem_str": "0 B",
            "total_limit_str": "0 B",
            "mem_percent": 0.0,
            "container_count": 0,
            "ddev_container_count": 0,
            "total_net_in_bytes": 0.0,
            "total_net_out_bytes": 0.0,
            "total_net_str": "0 B / 0 B",
            "total_block_str": "0 B / 0 B"
        }
    }
    
    try:
        res = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if res.returncode != 0:
            response["error_message"] = res.stderr.strip() or "Docker no está en ejecución."
            return response
            
        response["is_docker_available"] = True
        
        lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
        
        total_cpu = 0.0
        total_mem = 0.0
        max_limit = 0.0
        net_in = 0.0
        net_out = 0.0
        block_in = 0.0
        block_out = 0.0
        ddev_count = 0
        
        containers_list = []
        projects_map: Dict[str, Dict[str, Any]] = {}
        
        for line in lines:
            try:
                data = json.loads(line)
            except Exception:
                continue
                
            raw_name = data.get("Name", "")
            cid = data.get("ID", data.get("Container", ""))[:12]
            cpu_pct = parse_cpu_percent(data.get("CPUPerc", "0%"))
            mem_info = parse_memory_usage(data.get("MemUsage", ""))
            mem_pct = parse_cpu_percent(data.get("MemPerc", "0%")) or mem_info["percent"]
            
            pids = 0
            try:
                pids = int(data.get("PIDs", 0))
            except Exception:
                pass
                
            net_io = data.get("NetIO", "0B / 0B")
            block_io = data.get("BlockIO", "0B / 0B")
            
            # Parsing de I/O de red
            if "/" in net_io:
                n_parts = net_io.split("/")
                net_in += parse_bytes_str(n_parts[0])
                net_out += parse_bytes_str(n_parts[1])
                
            # Parsing de I/O de disco
            if "/" in block_io:
                b_parts = block_io.split("/")
                block_in += parse_bytes_str(b_parts[0])
                block_out += parse_bytes_str(b_parts[1])
                
            project_name, service_name, scope = identify_container_project(raw_name)
            if scope in ["project", "system"]:
                ddev_count += 1
                
            container_entry = {
                "id": cid,
                "name": raw_name,
                "project": project_name,
                "service": service_name,
                "scope": scope,
                "cpu_percent": cpu_pct,
                "mem_used_bytes": mem_info["used_bytes"],
                "mem_limit_bytes": mem_info["limit_bytes"],
                "mem_used_str": mem_info["used_str"],
                "mem_limit_str": mem_info["limit_str"],
                "mem_percent": mem_pct,
                "net_io": net_io,
                "block_io": block_io,
                "pids": pids
            }
            containers_list.append(container_entry)
            
            # Acumular en proyecto
            if project_name not in projects_map:
                projects_map[project_name] = {
                    "project_name": project_name,
                    "scope": scope,
                    "container_count": 0,
                    "total_cpu_pct": 0.0,
                    "total_mem_bytes": 0.0,
                    "total_mem_limit_bytes": mem_info["limit_bytes"],
                    "total_mem_str": "0 B",
                    "mem_percent": 0.0,
                    "containers": []
                }
                
            proj = projects_map[project_name]
            proj["container_count"] += 1
            proj["total_cpu_pct"] += cpu_pct
            proj["total_mem_bytes"] += mem_info["used_bytes"]
            proj["containers"].append(container_entry)
            
            total_cpu += cpu_pct
            total_mem += mem_info["used_bytes"]
            if mem_info["limit_bytes"] > max_limit:
                max_limit = mem_info["limit_bytes"]
                
        # Finalizar cálculos por proyecto
        for pname, pinfo in projects_map.items():
            pinfo["total_cpu_pct"] = round(pinfo["total_cpu_pct"], 2)
            pinfo["total_mem_str"] = format_bytes(pinfo["total_mem_bytes"])
            if max_limit > 0:
                pinfo["mem_percent"] = round((pinfo["total_mem_bytes"] / max_limit) * 100.0, 2)
                
        # Ordenar contenedores por consumo de CPU descendente
        containers_list.sort(key=lambda c: (0 if c["scope"] == "project" else 1, -c["cpu_percent"]))
        
        # Resumen global
        global_mem_pct = round((total_mem / max_limit * 100.0), 2) if max_limit > 0 else 0.0
        
        response["containers"] = containers_list
        response["projects"] = projects_map
        response["global_summary"] = {
            "total_cpu_pct": round(total_cpu, 2),
            "total_mem_bytes": total_mem,
            "total_mem_limit_bytes": max_limit,
            "total_mem_str": format_bytes(total_mem),
            "total_limit_str": format_bytes(max_limit),
            "mem_percent": global_mem_pct,
            "container_count": len(containers_list),
            "ddev_container_count": ddev_count,
            "total_net_in_bytes": net_in,
            "total_net_out_bytes": net_out,
            "total_net_str": f"{format_bytes(net_in)} / {format_bytes(net_out)}",
            "total_block_str": f"{format_bytes(block_in)} / {format_bytes(block_out)}"
        }
        
    except FileNotFoundError:
        response["error_message"] = "El comando 'docker' no está instalado en el sistema."
    except Exception as ex:
        response["error_message"] = f"Error al consultar Docker: {str(ex)}"
        
    return response

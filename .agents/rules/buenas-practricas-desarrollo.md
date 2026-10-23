---
trigger: always_on
---

# PRIME DIRECTIVE – Arquitectura y Calidad de Software

## PRIME DIRECTIVE
Actúa como un **Arquitecto de Sistemas Principal**.  
Tu objetivo es maximizar la velocidad de desarrollo (**Vibe**) sin sacrificar la integridad estructural (**Solidez**).

Estás operando en un entorno **multiagente**; tus cambios deben ser:
- Atómicos
- Explicables
- No destructivos

---

## I. INTEGRIDAD ESTRUCTURAL (The Backbone)

### Separación Estricta de Responsabilidades (SoC)
Nunca mezcles **Lógica de Negocio**, **Capa de Datos** y **UI** en el mismo bloque o archivo.

**Regla:**
- La UI es “tonta” (solo muestra datos).
- La Lógica es “ciega” (no sabe cómo se muestra).

---

### Agnosticismo de Dependencias
Al importar librerías externas, crea siempre un **wrapper** o una **interfaz intermedia**.

**Motivo:**  
Si cambiamos la librería X por la Y, solo se modifica el wrapper, no toda la aplicación.

---

### Principio de Inmutabilidad por Defecto
Trata los datos como **inmutables** salvo que sea estrictamente necesario mutarlos.

Esto previene *side-effects* impredecibles entre agentes.

---

## II. PROTOCOLO DE CONSERVACIÓN DE CONTEXTO  
*(Multi-Agent Memory)*

### Regla de la “Chesterton’s Fence”
Antes de eliminar o refactorizar código que no creaste (o creado en un prompt anterior), debes **entender por qué existe**.  
No elimines dependencias sin comprenderlas.

---

### Código Auto-Documentado
Los nombres deben ser descriptivos por sí mismos.

Ejemplos:
- `getUserById` ✅  
- `getData` ❌  

**Excepción:**  
Comentarios solo para lógica compleja o decisiones no obvias.

---

### Atomicidad en Cambios
Cada cambio debe ser:
- Completo
- Funcional
- Sin TODOs críticos

---

## III. UI/UX – SISTEMA DE DISEÑO ATÓMICO  
*(Atomic Vibe)*

### Tokenización
Nunca uses *magic numbers* ni colores hardcodeados.

Ejemplos prohibidos:
- `#F00`
- `12px`

Usa tokens semánticos:
- `Colors.danger`
- `Spacing.medium`

---

### Componentización Recursiva
Si un componente:
- Se reutiliza
- O supera 20 líneas de UI  

➡️ Extráelo a un componente aislado.

---

### Resiliencia Visual
Todo componente debe manejar:
- Loading
- Error
- Empty
- Data Overflow

---

## IV. ESTÁNDARES DE CALIDAD GENÉRICOS  
*(Clean Code)*

### S.O.L.I.D. Simplificado
- **S:** Una función/clase = una responsabilidad
- **O:** Abierto a extensión, cerrado a modificación  
  (prefiere composición)

---

### Early Return Pattern
Evita el *Arrow Code*.

- Valida errores primero
- Retorna temprano
- Camino feliz al final

---

### Manejo Global de Errores
Nunca silencies errores.

- Maneja localmente o
- Propaga a una capa que informe al usuario

---

## V. META-INSTRUCCIÓN DE AUTO-CORRECCIÓN

Antes de entregar código, pregúntate:

> “¿Rompo la arquitectura del paso I?”  
> “¿Respeto el sistema de diseño del paso III?”

Si la respuesta es **no**, refactoriza antes de continuar.

---

**Fin del documento**

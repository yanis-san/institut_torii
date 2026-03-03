# Django-Tailwind — Configuration Standalone (sans Node.js)

Guide de configuration de **django-tailwind** avec le CLI standalone Tailwind CSS v4.
Pas besoin de Node.js, npm ou webpack.

---

## 1. Installation

```bash
pip install django-tailwind
```

> Le package `pytailwindcss` est installé automatiquement comme dépendance.
> Il télécharge le binaire Tailwind CLI standalone au premier build.

---

## 2. Settings Django (`base.py`)

```python
INSTALLED_APPS = [
    # ...
    'tailwind',
    # ...
    'theme',  # L'app Tailwind
]

# Tailwind
TAILWIND_APP_NAME = 'theme'
TAILWIND_USE_STANDALONE_BINARY = True  # ← OBLIGATOIRE pour le mode sans Node.js
```

### Settings optionnels

```python
# Fixer la version du CLI (par défaut : dernière)
TAILWIND_STANDALONE_BINARY_VERSION = "v4.1.16"

# Personnaliser les chemins (rarement nécessaire, ce sont les défauts)
TAILWIND_CSS_PATH = "css/dist/styles.css"
TAILWIND_STANDALONE_BUILD_COMMAND_ARGS = "-i static_src/src/styles.css -o static/css/dist/styles.css --minify"
TAILWIND_STANDALONE_START_COMMAND_ARGS = "-i static_src/src/styles.css -o static/css/dist/styles.css --watch"
```

> **Important :** Ces chemins sont relatifs au dossier de l'app `theme/`.

---

## 3. Structure de l'app `theme`

```
theme/
├── __init__.py
├── apps.py
├── static/
│   └── css/
│       └── dist/
│           └── styles.css    ← CSS compilé (généré automatiquement)
├── static_src/
│   └── src/
│       └── styles.css        ← CSS SOURCE (c'est ici qu'on écrit)
└── templates/                ← (optionnel)
```

> Le `tailwind.config.js` n'est **PAS utilisé** par Tailwind v4.
> Toute la config se fait dans le fichier CSS source.

---

## 4. Fichier CSS source — `theme/static_src/src/styles.css`

C'est le fichier **le plus important**. Tailwind v4 utilise ce fichier comme point d'entrée unique.

### Syntaxe Tailwind v4 (OBLIGATOIRE)

```css
@import "tailwindcss";

/* Scanner les templates Django pour détecter les classes utilisées */
@source "../../../templates/**/*.html";

/* Tokens custom (couleurs, fonts, etc.) */
@theme {
    --color-deep-black: #050505;
    --font-noto: "Noto Sans JP", sans-serif;
    --font-inter: Inter, sans-serif;
}

/* Styles de base custom */
@layer base {
    [x-cloak] {
        display: none !important;
    }

    a, button, select, [role="button"], label[for],
    input[type="checkbox"], input[type="radio"],
    [x-on\:click], [\@click], [hx-get], [hx-post] {
        cursor: pointer;
    }
}
```

### ⚠️ Erreur courante : ancienne syntaxe v3

```css
/* ❌ NE FONCTIONNE PAS avec Tailwind v4 */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ✅ Tailwind v4 utilise @import */
@import "tailwindcss";
```

---

## 5. Directive `@source` — Scanner les templates

Tailwind v4 ne lit plus `tailwind.config.js` pour le `content`. Il faut déclarer les chemins des templates directement dans le CSS avec `@source`.

Les chemins sont **relatifs au fichier CSS source** (`theme/static_src/src/styles.css`).

```css
/* Templates du projet (BASE_DIR/templates/) */
@source "../../../templates/**/*.html";

/* Templates dans les apps Django (BASE_DIR/<app>/templates/) */
@source "../../../home/templates/**/*.html";
@source "../../../courses/templates/**/*.html";

/* Ou plus simplement, scanner tout le projet */
@source "../../../**/templates/**/*.html";
```

### Calcul du chemin relatif

```
theme/static_src/src/styles.css
  ↑ ../  = theme/static_src/
  ↑ ../../  = theme/
  ↑ ../../../  = BASE_DIR (racine du projet)
```

---

## 6. Directive `@theme` — Variables custom

Remplace la section `theme.extend` de l'ancien `tailwind.config.js` :

```css
@theme {
    /* Couleurs custom → utilisables : bg-deep-black, text-deep-black, etc. */
    --color-deep-black: #050505;
    --color-torii-red: #dc2626;

    /* Fonts custom → utilisables : font-noto, font-inter */
    --font-noto: "Noto Sans JP", sans-serif;
    --font-inter: Inter, sans-serif;

    /* Spacing, border-radius, etc. */
    --radius-pill: 9999px;
}
```

---

## 7. Template tag — Charger le CSS

Dans le template `<head>` :

```html
{% load tailwind_tags %}
{% tailwind_css %}
```

Cela génère un `<link>` vers `theme/static/css/dist/styles.css`.

---

## 8. Commandes

```bash
# Build production (minifié)
python manage.py tailwind build

# Watch mode (recompile automatiquement à chaque changement)
python manage.py tailwind start

# Si le binaire ne se télécharge pas (erreur de permission) :
# Supprimer manuellement le dossier du binaire et relancer
# Emplacement : .venv/Lib/site-packages/pytailwindcss/bin/
```

---

## 9. Troubleshooting

### Le CSS compilé fait ~250 bytes (quasi vide)

**Cause :** Tailwind ne scanne aucun template → aucune classe détectée → CSS minimal.

**Solutions :**
1. Vérifier que `@import "tailwindcss";` est présent (pas l'ancienne syntaxe `@tailwind`)
2. Vérifier les chemins `@source` (relatifs au fichier CSS, pas à la racine du projet)
3. Vérifier que `TAILWIND_USE_STANDALONE_BINARY = True` est dans les settings

### `PermissionError` lors de `tailwind install`

Le binaire existe déjà et ne peut pas être remplacé.

```bash
# Solution : supprimer le binaire manuellement
Remove-Item -Recurse -Force .venv\Lib\site-packages\pytailwindcss\bin\
# Puis relancer
python manage.py tailwind install
```

### Le build ne prend pas en compte les changements

```bash
# Utiliser le watch mode en développement
python manage.py tailwind start
```

---

## 10. Résumé — Checklist nouveau projet

1. `pip install django-tailwind`
2. Ajouter `'tailwind'` et `'theme'` dans `INSTALLED_APPS`
3. `TAILWIND_APP_NAME = 'theme'`
4. `TAILWIND_USE_STANDALONE_BINARY = True`
5. Créer `theme/static_src/src/styles.css` avec :
   - `@import "tailwindcss";`
   - `@source "../../../templates/**/*.html";`
   - `@theme { ... }` pour les tokens custom
6. Créer `theme/static/css/dist/` (le dossier de sortie)
7. `{% load tailwind_tags %}` + `{% tailwind_css %}` dans le `<head>`
8. `python manage.py tailwind build` → vérifier que le CSS fait > 10 KB
9. `python manage.py tailwind start` pour le watch mode en dev

---

## Migration v3 → v4

| Tailwind v3 (ancien) | Tailwind v4 (actuel) |
|---|---|
| `@tailwind base;` | `@import "tailwindcss";` |
| `tailwind.config.js` `content: [...]` | `@source "...";` dans le CSS |
| `tailwind.config.js` `theme.extend.colors` | `@theme { --color-xxx: ...; }` |
| `tailwind.config.js` `plugins: [...]` | Plus nécessaire (forms, typography intégrés) |
| `npm install` / `node_modules` | CLI standalone, zéro Node.js |

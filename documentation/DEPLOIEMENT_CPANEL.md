# Déploiement sur cPanel — Institut Torii

> Guide pas-à-pas pour déployer le site sur un hébergement cPanel avec Passenger.

---

## Table des matières

1. [Pré-requis](#1-pré-requis)
2. [Préparer le projet localement](#2-préparer-le-projet-localement)
3. [Créer l'application Python sur cPanel](#3-créer-lapplication-python-sur-cpanel)
4. [Variables d'environnement](#4-variables-denvironnement)
5. [Transférer les fichiers](#5-transférer-les-fichiers)
6. [Configurer passenger_wsgi.py](#6-configurer-passenger_wsgipy)
7. [Installer les dépendances](#7-installer-les-dépendances)
8. [Base de données MySQL](#8-base-de-données-mysql)
9. [Commandes post-déploiement](#9-commandes-post-déploiement)
10. [Fichiers statiques et media](#10-fichiers-statiques-et-media)
11. [Email SMTP](#11-email-smtp)
12. [Vérification finale](#12-vérification-finale)
13. [Maintenance & mises à jour](#13-maintenance--mises-à-jour)
14. [Dépannage](#14-dépannage)

---

## 1. Pré-requis

- Hébergement cPanel avec **Python** (via "Setup Python App")
- **MySQL** disponible sur l'hébergement
- Accès **SSH** au serveur (recommandé, sinon terminal cPanel)
- Domaine configuré et pointant vers l'hébergement
- **SSL/HTTPS** activé sur le domaine (Let's Encrypt gratuit via cPanel)

---

## 2. Préparer le projet localement

Avant de transférer, exécutez ces commandes en local :

```bash
# 1. S'assurer que tous les tests passent
python manage.py test

# 2. Builder Tailwind CSS (version production, minifiée)
python manage.py tailwind build

# 3. Vérifier qu'il n'y a pas d'erreur
python manage.py check

# 4. Vérifier la checklist de déploiement
python manage.py check --deploy
```

### Fichiers/dossiers à NE PAS transférer

| Fichier/Dossier | Raison |
|-----------------|--------|
| `.venv/` | L'environnement sera créé sur le serveur |
| `db.sqlite3` | On utilise MySQL en prod |
| `__pycache__/` | Fichiers compilés Python |
| `node_modules/` | Pas utilisé (standalone Tailwind binary) |
| `.git/` | Pas nécessaire en prod |
| `ancien_code/` | Archive, pas nécessaire en prod |
| `test_*.txt` | Fichiers de tests temporaires |
| `.vscode/` | Configuration éditeur |

### Fichiers/dossiers à TRANSFÉRER

| Fichier/Dossier | Obligatoire | Description |
|-----------------|:-----------:|-------------|
| `config/` | ✅ | Configuration Django |
| `home/`, `courses/`, `contact/`, `registration/` | ✅ | Applications Django |
| `cms/`, `marketing/` | ✅ | CMS et email marketing |
| `templates/` | ✅ | Tous les templates |
| `static/` | ✅ | JS (Alpine, htmx) + images |
| `theme/static/css/dist/styles.css` | ✅ | CSS compilé Tailwind |
| `theme/__init__.py`, `theme/apps.py` | ✅ | App Tailwind (skeleton) |
| `manage.py` | ✅ | Script de gestion Django |
| `requirements.txt` | ✅ | Dépendances Python |
| `logs/` | ✅ | Dossier pour les logs (vide ok) |
| `documentation/` | ❌ | Optionnel, pour référence |

---

## 3. Créer l'application Python sur cPanel

1. Connectez-vous à **cPanel**
2. Cherchez **"Setup Python App"** (ou "Application Python")
3. Cliquez **"Create Application"**
4. Configurez :
   - **Python version** : 3.12+ (la plus récente disponible)
   - **Application root** : nom du dossier (ex: `institut_torii`)
   - **Application URL** : votre domaine
   - **Application startup file** : `passenger_wsgi.py`
   - **Application Entry point** : `application`

5. Cliquez **"Create"** — cPanel crée l'environnement virtuel

---

## 4. Variables d'environnement

Dans l'interface "Setup Python App", ajoutez **toutes** ces variables d'environnement :

### Variables obligatoires

| Variable | Valeur | Description |
|----------|--------|-------------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | **CRITIQUE** — Pointe vers les settings de production |
| `DJANGO_SECRET_KEY` | *(voir ci-dessous)* | Clé secrète unique et aléatoire |
| `DJANGO_ALLOWED_HOSTS` | `institut-torii.com www.institut-torii.com` | Domaines autorisés, séparés par des espaces |

### Base de données

| Variable | Valeur | Description |
|----------|--------|-------------|
| `DB_NAME` | *(nom de la base MySQL cPanel)* | Ex: `cpuser_institut` |
| `DB_USER` | *(utilisateur MySQL cPanel)* | Ex: `cpuser_torii` |
| `DB_PASSWORD` | *(mot de passe MySQL)* | Le mot de passe de l'utilisateur MySQL |
| `DB_HOST` | `localhost` | Normalement toujours `localhost` sur cPanel |

### Email SMTP

| Variable | Valeur | Description |
|----------|--------|-------------|
| `EMAIL_HOST` | `mail.institut-torii.com` | Serveur SMTP (souvent `mail.votre-domaine.com`) |
| `EMAIL_PORT` | `465` | Port SMTP (465 pour SSL, 587 pour TLS) |
| `EMAIL_USE_SSL` | `True` | `True` pour le port 465, `False` pour 587 |
| `EMAIL_HOST_USER` | `contact@institut-torii.com` | Adresse email d'authentification SMTP |
| `EMAIL_HOST_PASSWORD` | *(mot de passe email)* | Mot de passe du compte email |

### Générer la SECRET_KEY

Exécutez cette commande en local pour générer une clé :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copiez le résultat et collez-le comme valeur de `DJANGO_SECRET_KEY`.

> ⚠️ **Ne jamais partager cette clé.** Ne jamais la mettre dans le code source.

---

## 5. Transférer les fichiers

### Option A : Git (recommandé si SSH disponible)

```bash
# Sur le serveur, dans le dossier de l'application
git clone <votre-repo> .
```

### Option B : File Manager cPanel / FTP

1. Créez un `.zip` du projet (sans `.venv/`, `db.sqlite3`, `__pycache__/`, `ancien_code/`)
2. Uploadez via File Manager ou FTP dans le dossier de l'application
3. Décompressez sur le serveur

---

## 6. Configurer passenger_wsgi.py

cPanel crée un fichier `passenger_wsgi.py` à la racine de l'application. **Remplacez son contenu** par :

```python
import os
import sys

# Ajouter le répertoire du projet au path Python
sys.path.insert(0, os.path.dirname(__file__))

# Pointer vers les settings de production
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from config.wsgi import application
```

---

## 7. Installer les dépendances

### Via l'interface cPanel

Dans "Setup Python App", il y a souvent un bouton pour exécuter des commandes pip. Sinon, utilisez le **terminal SSH** :

```bash
# Activer l'environnement virtuel (le chemin est donné par cPanel)
source /home/cpuser/virtualenv/institut_torii/3.12/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### `requirements.txt` du projet

```
Django>=5.2
django-cotton
django-htmx
django-tailwind[reload]
whitenoise[brotli]
Pillow
PyMySQL
cryptography
```

> Note : `django-tailwind[reload]` installe aussi `django-browser-reload`, utilisé seulement en dev. Ça ne pose pas de problème en prod car il n'est pas dans `INSTALLED_APPS` de `prod.py`.

---

## 8. Base de données MySQL

### Créer la base sur cPanel

1. Allez dans **"MySQL Databases"** sur cPanel
2. Créez une **nouvelle base de données** (ex: `institut_torii`)
3. Créez un **nouvel utilisateur** avec un mot de passe fort
4. **Associez l'utilisateur à la base** avec **ALL PRIVILEGES**

> cPanel préfixe souvent le nom : si votre user cPanel est `cpuser`, la base sera `cpuser_institut_torii` et l'utilisateur `cpuser_torii`.

### Configurer les variables

Mettez les bonnes valeurs dans les variables d'environnement `DB_NAME`, `DB_USER`, `DB_PASSWORD` (voir section 4).

---

## 9. Commandes post-déploiement

Exécutez ces commandes **dans l'ordre** via SSH ou le terminal cPanel :

```bash
# 1. Activer l'environnement virtuel
source /home/cpuser/virtualenv/institut_torii/3.12/bin/activate

# 2. Appliquer les migrations (crée toutes les tables en BDD)
python manage.py migrate

# 3. Créer le super-utilisateur (pour le CMS et l'admin)
python manage.py createsuperuser

# 4. Collecter les fichiers statiques
python manage.py collectstatic --noinput

# 5. Vérifier que tout est correct
python manage.py check --deploy
```

### Créer les données initiales

Après le premier `migrate`, connectez-vous au CMS et :
1. Allez dans **Contenu > Paramètres du site** et remplissez les informations
2. Allez dans **Contenu > Page d'accueil** et remplissez le contenu
3. Allez dans **Catalogue** et créez les catégories, langues, formats
4. Créez vos premières **cohortes** (sessions de cours)

---

## 10. Fichiers statiques et media

### Fichiers statiques (CSS, JS, images du thème)

`collectstatic` copie tout dans `staticfiles/`. WhiteNoise les sert directement depuis Django avec compression Brotli — **pas besoin de configurer Apache/Nginx pour les statiques**.

### Fichiers media (uploads utilisateurs : reçus CCP, images)

Les fichiers media (uploads d'images, reçus de paiement) sont stockés dans `media/`.

**Sur cPanel**, les fichiers media ne sont **pas** servis par Django en production (seulement en dev). Vous devez configurer le serveur web pour les servir :

#### Option 1 : Créer un lien symbolique (recommandé)

Dans le File Manager cPanel, créez un lien symbolique ou configurez dans `.htaccess` :

```apache
# .htaccess dans le dossier public_html ou la racine du domaine
RewriteEngine On
RewriteRule ^media/(.*)$ /home/cpuser/institut_torii/media/$1 [L]
```

#### Option 2 : WhiteNoise pour les media (simple)

Ajoutez dans `config/settings/prod.py` :

```python
WHITENOISE_ROOT = BASE_DIR / 'media'
```

> ⚠️ Vérifiez que le dossier `media/` existe et que les sous-dossiers `media/cohorts/` et `media/receipts/` ont les bonnes permissions (755 pour dossiers, 644 pour fichiers).

---

## 11. Email SMTP

### Créer les comptes email sur cPanel

Allez dans **"Email Accounts"** et créez ces 3 adresses :

| Adresse | Usage |
|---------|-------|
| `contact@institut-torii.com` | Marketing, prospects, campagnes email |
| `inscription@institut-torii.com` | Emails transactionnels inscriptions |
| `notification@institut-torii.com` | Alertes système |

### Trouver les paramètres SMTP

Dans cPanel > **"Email Accounts"** > **"Connect Devices"**, vous trouverez :
- **Serveur SMTP** : généralement `mail.votre-domaine.com`
- **Port** : `465` (SSL) ou `587` (TLS/STARTTLS)
- **Authentification** : l'adresse email complète + mot de passe

### Tester l'envoi

Depuis le terminal SSH :

```bash
python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Ceci est un test', 'contact@institut-torii.com', ['votre-email@gmail.com'])
print('Email envoyé !')
"
```

> ⚠️ L'authentification SMTP se fait avec **une seule** adresse (`EMAIL_HOST_USER`), mais Django peut envoyer au nom des 3 adresses si le serveur SMTP le permet (c'est le cas sur cPanel). Sinon, mettez `contact@` comme `EMAIL_HOST_USER` et les 3 adresses comme alias.

---

## 12. Vérification finale

### Checklist avant mise en ligne

| # | Vérification | Commande / Action |
|---|-------------|-------------------|
| 1 | ✅ Tests passent (local) | `python manage.py test` → 296 OK |
| 2 | ✅ Tailwind buildé | `python manage.py tailwind build` |
| 3 | ✅ Settings prod correct | `DJANGO_SETTINGS_MODULE=config.settings.prod` |
| 4 | ✅ `SECRET_KEY` définie | Variable d'environnement non-vide |
| 5 | ✅ `ALLOWED_HOSTS` correct | Contient votre domaine |
| 6 | ✅ MySQL configurée | `DB_NAME`, `DB_USER`, `DB_PASSWORD` |
| 7 | ✅ Migrations appliquées | `python manage.py migrate` |
| 8 | ✅ Super-utilisateur créé | `python manage.py createsuperuser` |
| 9 | ✅ Static collectées | `python manage.py collectstatic --noinput` |
| 10 | ✅ SMTP configuré | `EMAIL_HOST_*` variables |
| 11 | ✅ SSL/HTTPS activé | Let's Encrypt sur cPanel |
| 12 | ✅ `passenger_wsgi.py` correct | Contenu vérifié |
| 13 | ✅ Dossiers `media/` et `logs/` existent | Avec permissions 755 |
| 14 | ✅ `check --deploy` OK | `python manage.py check --deploy` |

### Tests post-déploiement

1. **Page d'accueil** : `https://votre-domaine.com/` → doit s'afficher
2. **Page contact** : soumettre un formulaire → vérifier la réception email
3. **CMS** : se connecter via l'URL UUID → dashboard accessible
4. **Inscription** : s'inscrire à une cohorte → code généré + email reçu
5. **Admin Django** : accessible via l'URL UUID admin
6. **HTTPS** : vérifier que `http://` redirige vers `https://`

### URLs à tester

| Page | URL |
|------|-----|
| Accueil | `https://institut-torii.com/` |
| Japonais | `https://institut-torii.com/japanese/` |
| Chinois | `https://institut-torii.com/chinese/` |
| Coréen | `https://institut-torii.com/korean/` |
| Contact | `https://institut-torii.com/contact/` |
| Inscription | `https://institut-torii.com/registration/` |
| CMS | `https://institut-torii.com/b7d2e4f6-8a13-4c59-9e71-0d3b5a7f9c1e/` |

---

## 13. Maintenance & mises à jour

### Mettre à jour le code

```bash
# 1. Activer le venv
source /home/cpuser/virtualenv/institut_torii/3.12/bin/activate

# 2. Récupérer les changements (si Git)
git pull origin main

# 3. Installer les nouvelles dépendances (si modifiées)
pip install -r requirements.txt

# 4. Appliquer les migrations (si nouvelles)
python manage.py migrate

# 5. Collecter les statiques (si modifiées)
python manage.py collectstatic --noinput

# 6. Redémarrer l'application
touch tmp/restart.txt
```

### Redémarrer l'application

Sur cPanel avec Passenger, il suffit de toucher le fichier `tmp/restart.txt` :

```bash
mkdir -p tmp
touch tmp/restart.txt
```

Ou via l'interface cPanel > "Setup Python App" > bouton "Restart".

### Consulter les logs

```bash
# Logs Django (erreurs WARNING et au-dessus)
cat logs/django.log

# Logs Apache (si disponible)
tail -f ~/logs/error.log
```

---

## 14. Dépannage

### Erreur 500 — Internal Server Error

1. Vérifiez les logs : `cat logs/django.log`
2. Vérifiez que `DJANGO_SETTINGS_MODULE` est bien `config.settings.prod`
3. Vérifiez que toutes les variables d'environnement sont définies
4. Vérifiez que les migrations sont appliquées
5. Essayez : `python manage.py check` depuis le terminal SSH

### Page blanche ou erreur de module

```bash
# Vérifier les modules installés
pip list | grep -i django
pip list | grep -i cotton
pip list | grep -i whitenoise
```

### Fichiers statiques manquants (CSS/JS cassé)

```bash
python manage.py collectstatic --noinput --clear
touch tmp/restart.txt
```

### Problème de base de données

```bash
# Tester la connexion MySQL
python manage.py dbshell

# Voir les migrations en attente
python manage.py showmigrations | grep "\[ \]"
```

### Emails non envoyés

```bash
# Tester directement depuis le shell
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Corps', 'contact@institut-torii.com', ['test@gmail.com'])
```

Vérifiez :
- Le mot de passe SMTP est correct
- Le port (465 SSL vs 587 TLS)
- L'utilisateur SMTP correspond à un compte email existant sur cPanel

### Redirection HTTPS en boucle

Si le site fait une boucle de redirection infinie, cPanel gère peut-être déjà le SSL. Essayez dans `prod.py` :

```python
SECURE_SSL_REDIRECT = False  # cPanel gère déjà la redirection HTTPS
```

---

## Résumé des variables d'environnement

```
DJANGO_SETTINGS_MODULE = config.settings.prod
DJANGO_SECRET_KEY      = votre-cle-secrete-aleatoire-ici
DJANGO_ALLOWED_HOSTS   = institut-torii.com www.institut-torii.com

DB_NAME                = cpuser_institut_torii
DB_USER                = cpuser_torii
DB_PASSWORD            = mot-de-passe-mysql

EMAIL_HOST             = mail.institut-torii.com
EMAIL_PORT             = 465
EMAIL_USE_SSL          = True
EMAIL_HOST_USER        = contact@institut-torii.com
EMAIL_HOST_PASSWORD    = mot-de-passe-email
```

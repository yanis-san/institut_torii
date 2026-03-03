# Documentation Technique — Institut Torii

> Dernière mise à jour : mars 2026
> Django 6.0.2 · Python 3.14 · Tailwind CSS v4 · Alpine.js · htmx · Django Cotton

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture du projet](#2-architecture-du-projet)
3. [Stack technique](#3-stack-technique)
4. [Configuration (Settings)](#4-configuration-settings)
5. [Applications Django](#5-applications-django)
6. [Modèles de données](#6-modèles-de-données)
7. [Système d'inscription](#7-système-dinscription)
8. [Système de contact (Prospects)](#8-système-de-contact-prospects)
9. [CMS — Interface d'administration custom](#9-cms--interface-dadministration-custom)
10. [Marketing — Campagnes email](#10-marketing--campagnes-email)
11. [Notifications transactionnelles](#11-notifications-transactionnelles)
12. [Analytics (Server-side)](#12-analytics-server-side)
13. [Composants Django Cotton](#13-composants-django-cotton)
14. [Frontend — Tailwind / Alpine.js / htmx](#14-frontend--tailwind--alpinejs--htmx)
15. [URLs & Routage](#15-urls--routage)
16. [Sécurité](#16-sécurité)
17. [Tests](#17-tests)
18. [Déploiement](#18-déploiement)
19. [Commandes utiles](#19-commandes-utiles)

---

## 1. Vue d'ensemble

Institut Torii est un site web pour un centre culturel et linguistique asiatique basé en Algérie, spécialisé dans l'enseignement du japonais, chinois et coréen, ainsi que des ateliers artistiques et culinaires.

Le projet est un **monolithe Django** avec rendu côté serveur (SSR), enrichi par **htmx** pour les interactions AJAX et **Alpine.js** pour les comportements côté client. Le style est géré exclusivement par **Tailwind CSS v4**. Tous les composants de template utilisent **Django Cotton**.

### Fonctionnalités principales

- **Site public** : pages vitrine (accueil, langues, ateliers, contact, à propos)
- **Inscription en ligne** : workflow complet avec upload reçu CCP, code de suivi, statut en temps réel
- **CMS custom** : interface admin complète sans dépendre de `django.contrib.admin`
- **Email marketing** : campagnes ciblées, templates, tracking d'ouverture/clic, désinscription
- **Notifications transactionnelles** : emails automatiques à chaque étape de l'inscription
- **Analytics server-side** : tracking des pages vues, sources de trafic, appareils, IA/search/social

---

## 2. Architecture du projet

```
institut_torii/
├── manage.py
├── requirements.txt
├── db.sqlite3                  # Dev uniquement
├── config/                     # Configuration Django
│   ├── urls.py                 # URL racine
│   ├── wsgi.py / asgi.py
│   └── settings/
│       ├── __init__.py         # Import conditionnel dev/prod
│       ├── base.py             # Settings communs
│       ├── dev.py              # DEBUG=True, SQLite, console email
│       └── prod.py             # DEBUG=False, MySQL, SMTP, HTTPS
├── home/                       # App page d'accueil + à propos
├── courses/                    # App catalogue (catégories, langues, formats, cohortes)
├── contact/                    # App formulaire de contact (prospects)
├── registration/               # App inscription en ligne
├── cms/                        # App CMS custom (dashboard, CRUD, analytics)
├── marketing/                  # App email marketing + notifications
├── theme/                      # App Tailwind (django-tailwind)
│   └── static_src/src/styles.css
├── static/
│   └── js/
│       ├── alpine.min.js
│       └── htmx.min.js
├── templates/
│   ├── base.html
│   ├── cotton/                 # Tous les composants Cotton
│   │   ├── layout.html         # Layout public
│   │   ├── cms_layout.html     # Layout CMS
│   │   ├── head.html           # <head> SEO
│   │   ├── navbar.html / footer.html
│   │   ├── btn.html            # Bouton public
│   │   ├── cms_btn.html        # Bouton CMS
│   │   ├── cms_field.html      # Champ de formulaire CMS
│   │   ├── cms_card.html       # Carte CMS
│   │   ├── cms_badge.html      # Badge coloré
│   │   ├── cms_stat_card.html  # Carte KPI
│   │   ├── cms_page_header.html
│   │   ├── cms_nav_item.html
│   │   └── ...
│   ├── home/ courses/ contact/ registration/
│   ├── cms/                    # Templates CMS (dashboard, prospects, enrollments, cohorts, etc.)
│   └── marketing/              # Templates marketing (campaigns, templates, subscribers, notifications)
├── media/                      # Uploads (reçus CCP, images)
├── documentation/              # Fichiers de doc (ce fichier, etc.)
└── ancien_code/                # Archive ancien code (ne pas toucher)
```

---

## 3. Stack technique

| Couche | Technologie | Usage |
|--------|-------------|-------|
| Backend | Django 6.0.2 | Vues, modèles, logique métier |
| Composants | Django Cotton | Templates composants avec props/slots |
| Style | Tailwind CSS v4.1 (standalone binary) | Classes utilitaires uniquement |
| Interactivité client | Alpine.js | Toggles, modals, validation, drag&drop |
| Interactivité serveur | htmx | AJAX, partials, polling |
| Fichiers statiques | WhiteNoise + Brotli | Servir les fichiers sans Nginx |
| Images | Pillow → WebP (qualité 85) | Optimisation auto à l'upload |
| DB dev | SQLite | Légèreté en développement |
| DB prod | MySQL via PyMySQL | Production sur cPanel |
| Email dev | Console backend | Affichage dans le terminal |
| Email prod | SMTP (cPanel) | 3 adresses : contact@, inscription@, notification@ |

### Interdictions

- **Zéro `<style>` inline** → Tailwind uniquement
- **Zéro `<script>` inline** → Alpine.js uniquement
- **Zéro `onclick`** → `@click` (Alpine) ou `hx-*` (htmx)
- **Zéro jQuery/React/Vue** → Alpine.js + htmx uniquement
- **Zéro template sans composant Cotton** → tout est composant

---

## 4. Configuration (Settings)

### Split settings

Le projet utilise 3 fichiers de settings :

- **`base.py`** : apps, middleware, templates, i18n, static/media, email addresses, Tailwind
- **`dev.py`** : `DEBUG=True`, SQLite, console email, `django_browser_reload`
- **`prod.py`** : `DEBUG=False`, MySQL, SMTP, HTTPS, WhiteNoise compressed

`config/settings/__init__.py` importe `from .dev import *` — à changer pour la prod.

### Variables d'environnement (prod)

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Clé secrète (obligatoire, erreur si absent) |
| `DJANGO_ALLOWED_HOSTS` | Domaines séparés par espace |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` | MySQL |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_SSL` | SMTP |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Authentification SMTP |

### URLs d'admin sécurisées

Les URLs d'admin et CMS utilisent des UUID au lieu de `/admin/` ou `/cms/` :

```python
# config/settings/base.py
ADMIN_URL_PREFIX = 'a3f8c1e7-9b42-4d6a-b5e0-7f2a1c3d8e9b'
CMS_URL_PREFIX = 'b7d2e4f6-8a13-4c59-9e71-0d3b5a7f9c1e'
```

### Adresses email

```python
EMAIL_ADDRESSES = {
    'contact': 'contact@institut-torii.com',       # Marketing, prospects
    'inscription': 'inscription@institut-torii.com', # Transactionnel inscriptions
    'notification': 'notification@institut-torii.com', # Alertes système
}
```

---

## 5. Applications Django

### `home` — Page d'accueil

| Vue | URL | Description |
|-----|-----|-------------|
| `home` | `/` | Page d'accueil avec cohortes "mises en avant" |
| `about` | `/about/` | Page à propos |

### `courses` — Catalogue

| Vue | URL | Description |
|-----|-----|-------------|
| `language_detail` | `/japanese/`, `/chinese/`, `/korean/` | Page par langue |
| `workshop_list` | `/workshops/artistic/`, `/workshops/culinary/` | Pages ateliers |
| `cohorts_by_category` | `/api/cohorts/` | API JSON htmx (filtre cohortes) |

### `contact` — Formulaire de contact

| Vue | URL | Description |
|-----|-----|-------------|
| `contact` | `/contact/` | Formulaire prospect |
| `contact_success` | `/contact/success/` | Page de confirmation |

### `registration` — Inscription en ligne

| Vue | URL | Description |
|-----|-----|-------------|
| `cohort_list` | `/registration/` | Liste des cohortes ouvertes |
| `enroll` | `/registration/enroll/<slug>/` | Formulaire d'inscription |
| `enrollment_success` | `/registration/success/<code>/` | Confirmation avec code |
| `check_status` | `/registration/check-status/` | Vérification statut par code |
| `cohort_status_api` | `/registration/api/status/<slug>/` | API JSON stats temps réel |

### `cms` — Interface d'administration

Toutes les vues sont protégées par `@login_required`.

| Section | Routes | Description |
|---------|--------|-------------|
| Auth | `login/`, `logout/` | Connexion/déconnexion CMS |
| Dashboard | `/` (racine CMS) | KPIs, dernières inscriptions, revenus |
| Prospects | `prospects/`, `prospects/<pk>/` | Liste/détail/suppression prospects |
| Inscriptions | `enrollments/`, `enrollments/<pk>/` | Liste/détail + confirmer/rejeter/rembourser |
| Cohortes | `cohorts/`, `cohorts/create/`, `cohorts/<pk>/` | CRUD complet + toggle actif |
| Catalogue | `catalog/`, `catalog/category/`, etc. | Catégories, langues, formats |
| Contenu | `content/homepage/`, `content/settings/` | Édition homepage + paramètres site |
| Analytics | `analytics/` | Dashboard analytics server-side |

### `marketing` — Email marketing

| Section | Routes | Description |
|---------|--------|-------------|
| Templates | `templates/`, `templates/create/`, `templates/<pk>/` | CRUD templates email |
| Campagnes | `campaigns/`, `campaigns/create/`, `campaigns/<pk>/` | CRUD + populate + send + cancel |
| Abonnés | `subscribers/` | Liste des abonnements/désinscriptions |
| Notifications | `notifications/`, `notifications/<pk>/` | Historique emails transactionnels |

**Routes publiques** (préfixe `/email/`) :
- `unsubscribe/<token>/` — page de désinscription
- `track/open/<token>/` — pixel tracking ouverture
- `track/click/<token>/` — redirection tracking clic

---

## 6. Modèles de données

### `courses` app

```
Category (type: language|artistic|culinary, name, slug, icon, order)
    └── Cohort (FK)
Language (name, slug, flag_emoji, flag_image_url, order)
    └── Cohort (FK nullable)
CourseFormat (name, slug, is_online, is_individual, order)
    └── Cohort (FK)

Cohort — Modèle central du catalogue
    ├── Relations : category, language (nullable), format
    ├── Infos : name, slug, description, image, price, registration_fee
    ├── Durée : duration_value, duration_unit (weeks|months), hours_per_session, sessions_per_week
    ├── Dates : start_date, end_date
    ├── Capacité : max_capacity (nullable), min_students
    ├── Inscription en ligne : registration_open_date, registration_close_date, payment_instructions
    ├── Publication : is_active, is_featured, order
    ├── Propriétés : duration_display, is_registration_open
    └── CohortSchedule (day, start_time, end_time) — horaires par jour
```

### `contact` app

```
Prospect — Données prospect capturées via le formulaire
    ├── Identité : first_name, last_name, email, phone
    ├── Profil : birth_date, level (beginner→expert)
    ├── Intérêts : interested_category (FK), interested_language (FK),
    │              interested_cohort (FK), other_interests (M2M)
    ├── Préférences : message, contact_preferences (JSON)
    └── Méta : source, notes, created_at, converted, converted_date
```

### `registration` app

```
Enrollment — Inscription d'un étudiant à une cohorte
    ├── Identité : first_name, last_name (LATIN_ONLY validator), email, phone
    ├── Inscription : cohort (FK → Cohort, PROTECT)
    ├── Paiement : payment_receipt (ImageField upload)
    ├── Statut : status (pending|confirmed|rejected|refunded)
    ├── Code : enrollment_code (8 chars hex unique, auto-généré)
    ├── Validation admin : confirmed_at, confirmed_by (FK → User), rejection_reason
    └── Méta : admin_notes, created_at, updated_at
```

### `cms` app

```
HomePage (singleton pk=1) — Contenu éditable page d'accueil
    ├── Hero : hero_title, hero_subtitle, hero_image, hero_cta_text, hero_cta_url
    ├── À propos : about_title, about_text, about_image
    ├── Stats : stat_students/teachers/languages/years + labels
    ├── Témoignages : testimonial_1/2/3_text/author/role
    └── CTA final : cta_title, cta_text

SiteSettings (singleton pk=1) — Paramètres globaux
    ├── Contact : phone, email, address, google_maps_url
    ├── Réseaux sociaux : facebook/instagram/tiktok/youtube/whatsapp
    ├── SEO : site_name, meta_description, og_image
    └── Horaires : opening_hours

PageView — Tracking analytique serveur
    ├── Requête : path, full_url, method, status_code
    ├── Visiteur : visitor_hash (SHA-256 IP+UA), session_key, is_authenticated
    ├── Source : referrer, referrer_domain, utm_source/medium/campaign
    ├── Appareil : user_agent, device_type, browser, os
    └── Méthodes statiques : classify_referrer, classify_ai_referrer,
                             classify_search_engine, classify_social_media
```

### `marketing` app

```
EmailTemplate — Template email réutilisable
    ├── name, category (welcome|newsletter|notification|promotional|transactional)
    ├── subject, body_html, body_text
    └── is_active, created_at, updated_at

EmailCampaign — Campagne email ciblée
    ├── Identification : name, template (FK → EmailTemplate, PROTECT), subject (override)
    ├── Expéditeur : from_email_type (contact|inscription|notification), reply_to
    ├── Ciblage : segment_type (7 types), segment_filter (JSON)
    ├── Statut : status (draft|scheduled|sending|sent|cancelled), scheduled_at
    ├── Compteurs : total_recipients, sent/failed/opened/clicked_count
    └── Propriétés calculées : effective_subject, open_rate, click_rate, delivery_rate

CampaignRecipient — Suivi individuel par destinataire
    ├── campaign (FK), email, first_name, last_name
    ├── Source : source_type, source_id
    ├── Statut : status (pending|sent|failed|bounced), sent_at, opened_at, clicked_at
    ├── Tokens : open_token (UUID), click_token (UUID)
    └── error_message

EmailSubscription — Gestion désinscription par email
    ├── email (unique), is_subscribed, unsubscribe_token (UUID)
    └── Méthodes de classe : is_email_subscribed(), get_or_create_subscription()

NotificationLog — Historique emails transactionnels
    ├── event_type (5 types : contact_received, enrollment_received/confirmed/rejected/refunded)
    ├── recipient_email, recipient_name, subject, body_html
    ├── Objet lié : related_model ('prospect' ou 'enrollment'), related_id
    ├── status (sent|failed), error_message
    └── sent_at, sent_by (FK → User, nullable si automatique)
```

---

## 7. Système d'inscription

### Workflow complet

```
1. Étudiant visite /registration/
   └── Voit les cohortes ouvertes (is_active + registration dates valides)

2. Étudiant clique sur "S'inscrire" → /registration/enroll/<slug>/
   ├── Vérifie que les inscriptions sont ouvertes (is_registration_open)
   ├── Vérifie la capacité (max_capacity vs pending+confirmed)
   └── Formulaire : nom, prénom, email, téléphone, upload reçu CCP

3. Soumission → Enrollment créé (status='pending')
   ├── Code d'inscription unique généré automatiquement (8 hex : 'ABC12345')
   ├── Email automatique envoyé → notify_enrollment_received()
   └── Redirect vers /registration/success/<code>/

4. Étudiant peut vérifier son statut → /registration/check-status/
   ├── Saisit son code d'inscription
   ├── Voit : statut, nombre confirmés/pending/max dans la cohorte
   └── API JSON disponible pour polling htmx (/registration/api/status/<slug>/)

5. Admin dans le CMS :
   ├── Voit le reçu CCP dans la fiche détail
   ├── Confirmer → enrollment.confirm(), email automatique envoyé
   ├── Rejeter → enrollment.reject(reason=...), email avec motif
   └── Rembourser → status='refunded', email de notification
```

### Validation des noms

Les champs `first_name` et `last_name` utilisent `LATIN_ONLY` validator :
```regex
^[a-zA-ZÀ-ÿœŒæÆçÇ\s\-']+$
```

### Code d'inscription

Généré par `uuid.uuid4().hex[:8].upper()` — 8 caractères hexadécimaux majuscules.
Champ unique, non-éditable, généré automatiquement à la création.

---

## 8. Système de contact (Prospects)

### Modèle `Prospect`

Capture riche : identité + profil (date naissance, niveau) + intérêts (catégorie, langue, cohorte) + message + préférences de contact (JSON list) + source de provenance.

### Workflow

1. Visiteur remplit le formulaire `/contact/` avec sélecteurs dynamiques (catégorie → langue → cohorte via htmx/JSON API)
2. `Prospect` créé → `notify_contact_received()` envoyé automatiquement
3. Admin voit dans le CMS : liste filtrable + détail complet
4. Admin peut ajouter des notes, marquer comme "converti"

---

## 9. CMS — Interface d'administration custom

### Accès

URL : `/<CMS_URL_PREFIX>/` (UUID, jamais `/cms/` en clair).
Authentification via `@login_required` avec `CMSLoginForm` (AuthenticationForm).

### Dashboard

Le dashboard affiche en temps réel :

- **KPIs** : inscriptions actives (confirmées + pending), prospects, cohortes actives, revenus
- **Revenus** : total (confirmés - remboursés), revenus mensuels
- **Dernières données** : 5 dernières inscriptions, 5 derniers prospects
- **Graphiques** : inscriptions par statut, par cohorte, prospects par langue

### Gestion des prospects

- Liste avec filtres : langue, statut (converti/non lu/nouveau), recherche texte
- Détail : toutes les infos + formulaire notes/converti
- Suppression (POST)

### Gestion des inscriptions

- Liste avec filtres : statut, cohorte, recherche (nom/email/code)
- Détail : toutes infos + image du reçu CCP + stats cohorte
- Actions :
  - **Confirmer** (`enrollment_confirm`) → met à jour statut + envoie email de confirmation
  - **Rejeter** (`enrollment_reject`) → motif requis + envoie email de rejet
  - **Rembourser** (`enrollment_refund`) → met à jour statut + envoie email de remboursement

### Gestion des cohortes

- CRUD complet : créer, éditer, supprimer (seulement si aucune inscription existante)
- Inline formset pour les horaires (`CohortSchedule`)
- Toggle actif/inactif via `cohort_toggle`
- Affichage des stats (confirmés/pending/total) dans le formulaire d'édition

### Catalogue (catégories, langues, formats)

- Vue centralisée `catalog_settings` avec compteur de cohortes par item
- Formulaire générique `category_form`, `language_form`, `format_form` (create/edit)

### Contenu (HomePage + SiteSettings)

- Singletons accessibles via `.load()` (pattern `get_or_create(pk=1)`)
- `HomePage` : hero, à propos, statistiques, témoignages (×3), CTA final
- `SiteSettings` : contact, réseaux sociaux, SEO, horaires

### Optimisation d'images

Fonction `optimize_image()` dans `cms/models.py` :
- Resize max 1920×1080 (1200×630 pour OG image)
- Conversion WebP qualité 85
- Aplatit la transparence RGBA sur fond blanc
- Appliquée automatiquement au `save()` des singletons

---

## 10. Marketing — Campagnes email

### Architecture

```
EmailTemplate (modèle réutilisable)
    └── EmailCampaign (cible un segment)
        └── CampaignRecipient (suivi par destinataire)
            ├── open_token → pixel tracking
            └── click_token → redirection tracking

EmailSubscription (désinscription par email)
```

### Segments disponibles

| Segment | Description | Filtre additionnel |
|---------|-------------|-------------------|
| `all_prospects` | Tous les prospects du formulaire contact | — |
| `all_enrolled` | Tous les inscrits (tout statut) | — |
| `all_confirmed` | Inscrits confirmés uniquement | — |
| `prospects_lang` | Prospects par langue d'intérêt | `language_id` |
| `enrolled_cohort` | Inscrits par cohorte spécifique | `cohort_id` |
| `enrolled_lang` | Inscrits par langue de la cohorte | `language_id` |
| `custom` | Liste manuelle (ajout direct en base) | — |

### Workflow d'envoi

1. Créer un template email (HTML + variables Django : `{{ first_name }}`, etc.)
2. Créer une campagne : choisir template, segment, adresse expéditeur
3. **Populate** : construit la liste de destinataires à partir du segment
4. **Preview** : visualise le rendu avec données fictives
5. **Send** : envoi en batch (50 emails, 2s de pause entre batches)
6. Suivi : taux d'ouverture, de clic, de délivrance

### Tracking

- **Ouverture** : pixel 1×1 transparent injecté, endpoint `/email/track/open/<token>/`
- **Clic** : URLs réécrites avec redirection `/email/track/click/<token>/?url=...`
- **Désinscription** : page publique `/email/unsubscribe/<token>/`, header `List-Unsubscribe`

### Services (`marketing/services.py`)

- `get_from_email(type)` → résout l'adresse selon le type (contact/inscription/notification)
- `strip_html(html)` → version texte brut
- `render_email_content(template, context)` → rendu avec Django Template
- `build_recipient_list(campaign)` → construit la liste dédupliquée, exclut désinscrits
- `populate_campaign_recipients(campaign)` → crée les `CampaignRecipient`
- `send_single_email(recipient, campaign)` → envoi individuel avec tracking
- `send_campaign(campaign)` → envoi en batch avec rate limiting

---

## 11. Notifications transactionnelles

### Fonctionnement

Module `marketing/notifications.py` — envoi automatique d'emails sur les événements clés.

| Événement | Fonction | Déclencheur | Adresse expéditeur |
|-----------|----------|-------------|-------------------|
| Contact reçu | `notify_contact_received(prospect)` | `contact/views.py` après `form.save()` | contact@ |
| Inscription reçue | `notify_enrollment_received(enrollment)` | `registration/views.py` après `form.save()` | inscription@ |
| Inscription confirmée | `notify_enrollment_confirmed(enrollment, user)` | `cms/views.py` `enrollment_confirm` | inscription@ |
| Inscription rejetée | `notify_enrollment_rejected(enrollment, user)` | `cms/views.py` `enrollment_reject` | inscription@ |
| Inscription remboursée | `notify_enrollment_refunded(enrollment, user)` | `cms/views.py` `enrollment_refund` | inscription@ |

### Templates par défaut

Les templates sont définies dans `DEFAULT_TEMPLATES` (dict Python) avec des variables Django :
- `{{ first_name }}`, `{{ last_name }}`, `{{ email }}`
- `{{ cohort_name }}`, `{{ enrollment_code }}`, `{{ start_date }}`
- `{{ rejection_reason }}`, `{{ site_name }}`

### Logging

Chaque envoi (réussi ou échoué) crée un `NotificationLog` avec :
- Type d'événement, destinataire, objet, body HTML rendu
- Statut (sent/failed), message d'erreur si échec
- Lien vers l'objet source (prospect ou enrollment)
- Utilisateur admin ayant déclenché l'action (si applicable)

### CMS — Consultation

- Liste : `/marketing/notifications/` — filtrable par type, statut, recherche texte
- Détail : `/marketing/notifications/<pk>/` — preview du contenu HTML envoyé

---

## 12. Analytics (Server-side)

### Middleware

`cms.middleware.AnalyticsMiddleware` — enregistre chaque visite page dans `PageView`.

**Ce qui est tracké** :
- Uniquement les requêtes GET
- Uniquement les pages publiques

**Ce qui est ignoré** :
- Admin (`/<ADMIN_URL_PREFIX>/`)
- CMS (`/<CMS_URL_PREFIX>/`)
- Fichiers statiques (`/static/`, `/media/`)
- Requêtes htmx (`HX-Request` header)
- Favicon

### Données collectées

- **Visiteur** : hash SHA-256 anonymisé (IP + User-Agent), session Django
- **Source** : referrer, domaine referrer, UTM (source, medium, campaign)
- **Appareil** : type (desktop/mobile/tablet/bot), navigateur, OS
- **Timestamp** automatique

### Classification des sources

Le modèle `PageView` contient des dictionnaires statiques pour classifier automatiquement :
- **IA** : ChatGPT, Gemini, Perplexity, Claude, Copilot, DeepSeek, You.com, Phind, Poe, HuggingFace
- **Moteurs de recherche** : Google (.com/.fr/.dz/.co.jp/.co.kr), Bing, Yahoo, DuckDuckGo, Ecosia, Qwant, Baidu, Yandex, Naver
- **Réseaux sociaux** : Facebook, Instagram, X/Twitter, LinkedIn, TikTok, YouTube, Reddit, Pinterest, Snapchat, WhatsApp, Telegram, Threads

### Dashboard Analytics (CMS)

La vue `analytics` `/analytics/` calcule et affiche :
- KPIs : vues totales, visiteurs uniques, sessions, pages/session, bots filtrés
- Graphique trafic quotidien (labels + data JSON pour chart)
- Top 15 pages les plus visitées
- Sources de trafic (domaines, direct/referral/UTM)
- Campagnes UTM
- Breakdown appareils, navigateurs, OS
- Funnel de conversion : accueil → cours → contact → inscription
- Heures de pointe
- Détail par source : IA, moteurs de recherche, réseaux sociaux (visites + top pages)
- Filtre par période : 7, 14, 30, 90 jours

---

## 13. Composants Django Cotton

### Composants publics

| Composant | Fichier | Usage |
|-----------|---------|-------|
| `<c-layout>` | `layout.html` | Layout pages publiques (navbar + footer) |
| `<c-head>` | `head.html` | Balise `<head>` avec SEO, fonts, CSS, JS |
| `<c-navbar>` | `navbar.html` | Barre de navigation responsive |
| `<c-footer>` | `footer.html` | Pied de page |
| `<c-btn>` | `btn.html` | Bouton/lien public (gradient rouge) |
| `<c-section>` | `section.html` | Section avec fond + gradient |
| `<c-section-heading>` | `section_heading.html` | Titre de section |
| `<c-stat-card>` | `stat_card.html` | Carte statistique publique |
| `<c-testimonial>` | `testimonial.html` | Carte témoignage |
| `<c-cohort-card>` | `cohort_card.html` | Carte de cohorte |
| `<c-feature-card>` | `feature_card.html` | Carte fonctionnalité |
| `<c-language-hero>` | `language_hero.html` | Hero page langue |
| `<c-form-field>` | `form_field.html` | Champ formulaire public |

### Composants CMS

| Composant | Fichier | Usage |
|-----------|---------|-------|
| `<c-cms-layout>` | `cms_layout.html` | Layout CMS (sidebar + topbar) |
| `<c-cms-nav-item>` | `cms_nav_item.html` | Item navigation sidebar |
| `<c-cms-page-header>` | `cms_page_header.html` | En-tête de page CMS |
| `<c-cms-card>` | `cms_card.html` | Carte conteneur CMS |
| `<c-cms-stat-card>` | `cms_stat_card.html` | Carte KPI CMS |
| `<c-cms-badge>` | `cms_badge.html` | Badge coloré (statuts) |
| `<c-cms-btn>` | `cms_btn.html` | Bouton CMS (variantes) |
| `<c-cms-field>` | `cms_field.html` | Champ formulaire CMS |

### Conventions Cotton

```html
<!-- Props avec valeurs par défaut -->
<c-vars title="" description="" />

<!-- Slot principal -->
{{ slot }}

<!-- Transmission d'attributs Tailwind du parent -->
{{ attrs }}

<!-- Syntaxe d'utilisation -->
<c-btn href="/contact/">Nous contacter</c-btn>
<c-cms-badge label="Confirmé" color="emerald" />
<c-cms-field :field="form.name" />  <!-- :field → passe le BoundField Python -->
```

**Important** : le préfixe `:` (deux-points) dans Cotton permet de passer des objets Python, pas des strings. `<c-cms-field :field="form.name" />` passe l'objet `BoundField`.

---

## 14. Frontend — Tailwind / Alpine.js / htmx

### Tailwind CSS v4

Configuration : `theme/static_src/src/styles.css`

```css
@import "tailwindcss";
@source "../../../templates/**/*.html";

@theme {
    --color-deep-black: #050505;
    --font-clash: "Clash Display", sans-serif;
}

@layer base {
    [x-cloak] { display: none !important; }
    a, button, select, [role="button"], ... { cursor: pointer; }
}
```

Build : `python manage.py tailwind build` (ou `tailwind start` pour le watch).
Utilise le **standalone binary** (pas de Node.js nécessaire) via `TAILWIND_USE_STANDALONE_BINARY = True`.

### Palette

| Élément (public) | Classes |
|-------------------|---------|
| Fond | `bg-white` ou `bg-deep-black` |
| Texte | `text-gray-800` / `text-gray-600` |
| Accent | `red-500` à `red-600` |
| Arrondis | `rounded-xl` |

| Élément (CMS) | Classes |
|----------------|---------|
| Fond | `bg-zinc-950` |
| Cartes | `bg-zinc-900 border border-zinc-800` |
| Inputs | `bg-zinc-800 border-zinc-700 text-zinc-100` |
| Accent | `red-500` / `red-600` |

### Alpine.js — Patterns utilisés

- Menu mobile : `x-data="{ open: false }"` + `x-show` + `@click`
- Drag & drop upload : `x-data="{ fileName: '', isDragging: false }"`
- Ciblage conditionnel (campagnes marketing) : `x-show` sur les filtres selon le segment type
- Onglets : `x-data="{ tab: 'first' }"` + `:class`
- Validation côté client : `x-model` + `@input="validateField()"`

### htmx — Patterns utilisés

- `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` sur `<body>`
- Filtrage dynamique cohortes dans le formulaire contact : `hx-get` + `hx-target`
- API polling statut inscription : `hx-get` avec intervalle
- Actions CMS (confirm/reject/refund) : formulaires `hx-post`
- Chargement dynamique des options de formulaire

---

## 15. URLs & Routage

### Schéma complet

```
/                                         → home:home
/about/                                   → home:about
/japanese/                                → courses:japanese
/chinese/                                 → courses:chinese
/korean/                                  → courses:korean
/workshops/artistic/                      → courses:workshops_artistic
/workshops/culinary/                      → courses:workshops_culinary
/api/cohorts/                             → courses:api_cohorts
/contact/                                 → contact:contact
/contact/success/                         → contact:success
/registration/                            → registration:cohort_list
/registration/enroll/<slug>/              → registration:enroll
/registration/success/<code>/             → registration:success
/registration/check-status/               → registration:check_status
/registration/api/status/<slug>/          → registration:cohort_status_api
/email/unsubscribe/<token>/               → marketing_public:unsubscribe
/email/track/open/<token>/                → marketing_public:track_open
/email/track/click/<token>/               → marketing_public:track_click
/<ADMIN_UUID>/                            → admin Django
/<CMS_UUID>/                              → cms:dashboard
/<CMS_UUID>/login/                        → cms:login
/<CMS_UUID>/prospects/                    → cms:prospect_list
/<CMS_UUID>/enrollments/                  → cms:enrollment_list
/<CMS_UUID>/cohorts/                      → cms:cohort_list
/<CMS_UUID>/catalog/                      → cms:catalog_settings
/<CMS_UUID>/content/homepage/             → cms:edit_homepage
/<CMS_UUID>/content/settings/             → cms:edit_settings
/<CMS_UUID>/analytics/                    → cms:analytics
/<CMS_UUID>/marketing/templates/          → marketing:template_list
/<CMS_UUID>/marketing/campaigns/          → marketing:campaign_list
/<CMS_UUID>/marketing/subscribers/        → marketing:subscriber_list
/<CMS_UUID>/marketing/notifications/      → marketing:notification_list
```

---

## 16. Sécurité

- **URLs admin/CMS** : UUIDs aléatoires, jamais `/admin/` ou `/cms/`
- **CSRF** : token global via `hx-headers` sur `<body>`, `@require_POST` sur les actions dangereuses
- **Auth CMS** : `@login_required` avec redirection vers login custom
- **Désinscription email** : tokens UUID uniques par utilisateur
- **Réception CCP** : upload via `ImageField` avec accept `image/*` uniquement
- **Noms** : validation `LATIN_ONLY` (regex) sur les noms d'inscription
- **Prod** : `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_*`
- **SECRET_KEY** : depuis variable d'environnement (erreur si absent en prod)
- **Analytics** : visiteurs anonymisés par hash SHA-256 (pas d'IP stockée)

---

## 17. Tests

### Organisation

296 tests au total, répartis ainsi :
- **`cms/tests.py`** : ~169 tests — auth, dashboard, prospects CRUD, enrollments CRUD, cohorts CRUD, catalog, content, analytics
- **`marketing/tests.py`** : ~127 tests — models, services, views, send, tracking, notifications

### Convention

Toute fonctionnalité backend est testée (TDD). Les tests utilisent :
- `TestCase` avec `Client` Django
- `MarketingTestMixin` comme mixin partagé (setup user + fixtures courses)
- `@override_settings(EMAIL_BACKEND='locmem')` pour tester les envois email
- `unittest.mock.patch` pour simuler les erreurs SMTP
- `mail.outbox` pour vérifier le contenu des emails envoyés

### Exécution

```bash
python manage.py test                    # Tous les tests (296)
python manage.py test cms                # Tests CMS uniquement
python manage.py test marketing          # Tests marketing uniquement
python manage.py test cms --verbosity=2  # Avec détails
```

---

## 18. Déploiement

### Cible : cPanel avec Passenger WSGI

1. Configurer le Python App dans cPanel
2. Définir les variables d'environnement (voir §4)
3. `passenger_wsgi.py` :
   ```python
   import os, sys
   from config.wsgi import application
   sys.path.insert(0, os.path.dirname(__file__))
   os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
   ```
4. Basculer `config/settings/__init__.py` vers `from .prod import *`
5. `python manage.py collectstatic --noinput`
6. `python manage.py migrate`
7. `python manage.py createsuperuser`

### Checklist prod

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` depuis env
- [ ] `ALLOWED_HOSTS` correct
- [ ] MySQL configurée
- [ ] SMTP configuré (3 adresses email)
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `collectstatic` exécuté
- [ ] WhiteNoise `CompressedManifestStaticFilesStorage`
- [ ] Tailwind `build` (pas `start`)
- [ ] Tests passent (`python manage.py test`)

---

## 19. Commandes utiles

```bash
# Environnement
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
pip install -r requirements.txt

# Développement
python manage.py runserver
python manage.py tailwind start     # Watch mode CSS

# Base de données
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Production
python manage.py collectstatic --noinput
python manage.py tailwind build
python manage.py check --deploy

# Tests
python manage.py test               # 296 tests
python manage.py test <app>
python manage.py test <app> --verbosity=2
```

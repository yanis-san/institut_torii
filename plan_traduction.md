Plan de traduction — Version simple
Langues : FR (défaut), EN, AR, ZH (chinois), JA (japonais), KO (coréen)
Emails : restent en français, aucun changement
CMS : reste en français, aucun changement

Étape 1 — Infrastructure (0 test cassé)
Ajouter LANGUAGES, LOCALE_PATHS dans base.py
Ajouter LocaleMiddleware dans MIDDLEWARE
Créer le dossier locale/
Wrapper les URLs publiques avec i18n_patterns() → /en/japanese/, /ar/contact/, etc.
L'URL sans préfixe (/) reste en français (pas de /fr/)
Étape 2 — Sélecteur de langue (0 test cassé)
Composant Cotton <c-language-switcher /> dans la navbar
Drapeaux cliquables qui changent la langue via {% url 'set_language' %}
Étape 3 — Textes statiques des templates (risque faible)
Ajouter {% load i18n %} en haut des templates
Remplacer les textes hardcodés par {% trans "texte" %}
Ne toucher que les templates publics (pas le CMS)
python [manage.py](http://_vscodecontentref_/3) makemessages → génère les .po
Remplir les traductions dans les .po
python [manage.py](http://_vscodecontentref_/4) compilemessages → génère les .mo
Étape 4 — Contenu dynamique (cohortes, page d'accueil)
pip install django-modeltranslation
Créer translation.py dans chaque app avec les champs à traduire
python [manage.py](http://_vscodecontentref_/6) makemigrations → ajoute les colonnes _en, _ar, _zh, _ja, _ko
python [manage.py](http://_vscodecontentref_/7) migrate
Le CMS affiche automatiquement les champs par langue
Fallback → français si traduction vide
Modèles concernés :

Modèle	Champs
HomePage	Tous les champs texte
SiteSettings	site_name, meta_description
Cohort	name, description, payment_instructions
Category	name, description
Language	name
CourseFormat	name, description
Étape 5 — RTL arabe (isolé)
dir="rtl" conditionnel sur <html> selon la langue active
Tailwind logical properties (ms-, me-, ps-, pe-)
Test visuel uniquement, aucun test backend impacté
Ce qu'on ne touche PAS
Emails (restent FR)
CMS interface (reste FR)
Tests existants (on adapte seulement si un assertContains("texte français") casse)
URLs du CMS (pas de préfixe langue)
Ordre d'exécution
#	Étape	Tests cassés	Effort
1	Infrastructure	0	30 min
2	Sélecteur langue	0	30 min
3	Textes statiques	~5-10 à adapter	2-3h
4	Contenu dynamique	0 (nouvelles colonnes)	1-2h
5	RTL arabe	0	1-2h
Total : ~1 journée de dev. Les traductions effectives (remplir les .po et les champs CMS) c'est à part.

On attaque l'étape 1 ?
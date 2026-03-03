# Guide d'utilisation — Institut Torii

> Ce guide explique comment utiliser le site Institut Torii : le site public, l'espace d'administration (CMS), les emails et toutes les fonctionnalités disponibles.

---

## Table des matières

1. [Le site public](#1-le-site-public)
2. [Les inscriptions en ligne](#2-les-inscriptions-en-ligne)
3. [Le formulaire de contact](#3-le-formulaire-de-contact)
4. [Accéder au CMS (administration)](#4-accéder-au-cms-administration)
5. [Le tableau de bord](#5-le-tableau-de-bord)
6. [Gérer les prospects](#6-gérer-les-prospects)
7. [Gérer les inscriptions](#7-gérer-les-inscriptions)
8. [Gérer les cohortes (sessions de cours)](#8-gérer-les-cohortes-sessions-de-cours)
9. [Gérer le catalogue](#9-gérer-le-catalogue)
10. [Modifier le contenu du site](#10-modifier-le-contenu-du-site)
11. [Les statistiques (Analytics)](#11-les-statistiques-analytics)
12. [Email marketing — Templates](#12-email-marketing--templates)
13. [Email marketing — Campagnes](#13-email-marketing--campagnes)
14. [Abonnés et désinscriptions](#14-abonnés-et-désinscriptions)
15. [Historique des notifications](#15-historique-des-notifications)
16. [Emails automatiques (notifications)](#16-emails-automatiques-notifications)
17. [Résumé des 3 adresses email](#17-résumé-des-3-adresses-email)

---

## 1. Le site public

Le site public est ce que voient tous les visiteurs. Il comprend plusieurs pages :

### Page d'accueil (`/`)

La vitrine principale de l'institut. Elle affiche :
- Un **héro** (grande bannière) avec un titre, un sous-titre et un bouton d'action
- Une section **à propos** de l'institut
- Des **statistiques** (nombre d'étudiants, professeurs, langues, années)
- Des **témoignages** d'anciens étudiants (jusqu'à 3)
- Les **formations mises en avant** (cohortes marquées comme "featured")
- Un appel à l'action final

> Tout le contenu de cette page est modifiable depuis le CMS (voir section 10).

### Pages de langues

Chaque langue enseignée a sa propre page :
- **Japonais** → `/japanese/`
- **Chinois** → `/chinese/`
- **Coréen** → `/korean/`

Ces pages affichent les cohortes (sessions de cours) ouvertes et actives pour chaque langue.

### Pages d'ateliers

Il existe deux types d'ateliers :
- **Ateliers artistiques** → `/workshops/artistic/`
- **Ateliers culinaires** → `/workshops/culinary/`

### Page À propos (`/about/`)

Page de présentation générale de l'institut.

### Page Contact (`/contact/`)

Formulaire de contact qui enregistre les prospects (voir section 3).

### Page Inscription (`/registration/`)

Système d'inscription en ligne avec paiement CCP (voir section 2).

---

## 2. Les inscriptions en ligne

### Comment ça marche pour l'étudiant

1. L'étudiant visite **`/registration/`** et voit la liste des sessions de cours ouvertes aux inscriptions
2. Il clique sur **"S'inscrire"** pour la session qui l'intéresse
3. Il remplit le formulaire :
   - Prénom et nom (en caractères latins uniquement)
   - Adresse email
   - Numéro de téléphone avec indicatif pays
   - Upload du **reçu de paiement CCP** (photo ou scan)
4. Après soumission, il reçoit :
   - Un **code d'inscription unique** à 8 caractères (ex : `A3F2B1C7`)
   - Un email de confirmation de réception
5. Il peut ensuite **suivre son inscription** via `/registration/check-status/` en saisissant son code

### Les statuts d'une inscription

| Statut | Signification |
|--------|---------------|
| ⏳ **En attente** (pending) | Le dossier est reçu, en cours de vérification |
| ✅ **Confirmée** (confirmed) | Le paiement est validé, l'étudiant est inscrit |
| ❌ **Rejetée** (rejected) | L'inscription est refusée (motif fourni) |
| 💸 **Remboursée** (refunded) | L'inscription a été remboursée |

> À chaque changement de statut, un email est envoyé automatiquement à l'étudiant.

### Quand les inscriptions sont-elles ouvertes ?

Les inscriptions à une cohorte sont ouvertes lorsque :
- La cohorte est **active** (cochée comme active dans le CMS)
- On est entre la **date d'ouverture** et la **date de fermeture** des inscriptions
- Il reste de la **place** (si une capacité maximale est définie)

---

## 3. Le formulaire de contact

### Ce qu'il capture

Le formulaire de contact (`/contact/`) permet aux visiteurs de :
- Laisser leurs coordonnées (nom, email, téléphone)
- Indiquer leur niveau (débutant, intermédiaire, avancé, expert)
- Préciser ce qui les intéresse : la catégorie (langues, ateliers), la langue, une session spécifique
- Écrire un message libre
- Choisir comment ils préfèrent être contactés (email, téléphone, WhatsApp)

### Ce qui se passe après

1. Un **prospect** est créé dans la base de données
2. Un **email de notification** est envoyé automatiquement à l'équipe
3. Le prospect apparait dans le CMS pour suivi (voir section 6)

---

## 4. Accéder au CMS (administration)

### Comment se connecter

L'adresse du CMS n'est **pas** `/admin/` ou `/cms/` — elle utilise une adresse spéciale pour des raisons de sécurité. Pour y accéder, il faut connaître l'URL complète.

1. Rendez-vous à l'adresse du CMS
2. Entrez votre **nom d'utilisateur** et **mot de passe**
3. Vous arrivez sur le tableau de bord

### Navigation

Le CMS a une **sidebar** (barre latérale) à gauche avec les sections suivantes :
- 📊 **Tableau de bord** — Vue d'ensemble
- 👥 **Prospects** — Contacts reçus via le formulaire
- 📝 **Inscriptions** — Inscriptions des étudiants
- 📅 **Cohortes** — Sessions de cours
- 📚 **Catalogue** — Catégories, langues, formats
- 🏠 **Contenu** — Modifier le site (page d'accueil, paramètres)
- 📈 **Analytics** — Statistiques de visite
- ✉️ **Marketing** — Emails et campagnes

Sur mobile, cliquez sur le **menu hamburger** (☰) en haut à gauche pour ouvrir la sidebar.

---

## 5. Le tableau de bord

Le tableau de bord est la première page que vous voyez en vous connectant. Il donne une **vue d'ensemble rapide** :

### Indicateurs clés (KPIs)

- **Inscriptions actives** : nombre d'inscriptions confirmées + en attente
- **Prospects** : nombre total de contacts reçus
- **Cohortes actives** : sessions de cours actuellement ouvertes
- **Revenus** : montant total des inscriptions confirmées, moins les remboursements

### Aperçus rapides

- Les **5 dernières inscriptions** avec leur statut
- Les **5 derniers prospects** reçus

### Graphiques

- Répartition des inscriptions par statut (en attente / confirmée / rejetée / remboursée)
- Inscriptions par session de cours
- Prospects par langue d'intérêt

---

## 6. Gérer les prospects

**Page : Prospects** (dans la sidebar)

### Liste des prospects

Vous voyez la liste de tous les contacts reçus via le formulaire. Vous pouvez :
- **Rechercher** par nom ou email
- **Filtrer** par langue d'intérêt
- **Filtrer** par statut : converti, non lu, nouveau

### Fiche d'un prospect

En cliquant sur un prospect, vous voyez :
- Toutes ses informations de contact
- Ses intérêts (catégorie, langue, session)
- Son message
- Ses préférences de contact

**Vous pouvez :**
- Ajouter des **notes internes** (visibles uniquement par l'équipe)
- Le marquer comme **converti** (il est devenu élève)
- Le **supprimer**

---

## 7. Gérer les inscriptions

**Page : Inscriptions** (dans la sidebar)

### Liste des inscriptions

Vous voyez toutes les inscriptions reçues. Vous pouvez :
- **Rechercher** par nom, email ou code d'inscription
- **Filtrer** par statut (en attente, confirmée, rejetée, remboursée)
- **Filtrer** par session de cours (cohorte)

Chaque inscription affiche un badge de couleur selon son statut :
- 🟡 Jaune = En attente
- 🟢 Vert = Confirmée
- 🔴 Rouge = Rejetée
- 🔵 Bleu = Remboursée

### Fiche d'une inscription

En cliquant sur une inscription, vous voyez le détail complet :
- Informations de l'étudiant (nom, email, téléphone)
- La session de cours choisie
- Le **reçu de paiement CCP** (image uploadée)
- Le code d'inscription unique
- Les statistiques de la cohorte (nombre de confirmés, en attente, places restantes)
- Les dates de création et de modification

### Actions possibles

Depuis la fiche d'une inscription, 3 actions sont disponibles :

#### ✅ Confirmer
- Valide l'inscription de l'étudiant
- Enregistre la date de confirmation et l'admin qui a validé
- **Un email de confirmation est envoyé automatiquement** à l'étudiant
- L'email contient son code, le nom de la session et la date de début

#### ❌ Rejeter
- Vous devez fournir un **motif de rejet**
- **Un email de rejet est envoyé automatiquement** à l'étudiant
- L'email contient le motif du rejet

#### 💸 Rembourser
- Change le statut en "remboursé"
- **Un email de notification est envoyé automatiquement** à l'étudiant
- L'email confirme que le remboursement est en cours

> ⚠️ Chaque action envoie un email automatique. Vérifiez bien le dossier (reçu CCP, informations) avant de confirmer ou rejeter.

---

## 8. Gérer les cohortes (sessions de cours)

**Page : Cohortes** (dans la sidebar)

Une **cohorte** = une session de cours spécifique (par ex : "Japonais N5 — Session Printemps 2026").

### Liste des cohortes

- Toutes les sessions existantes
- Statut : ✅ Active / ⛔ Inactive
- Nombre d'inscrits confirmés + en attente

### Créer une cohorte

Cliquez sur **"Nouvelle cohorte"** et remplissez :

| Champ | Description |
|-------|-------------|
| Nom | Ex : "Japonais N5 — Mars 2026" |
| Catégorie | Langue, Atelier artistique, ou Atelier culinaire |
| Langue | Japonais, Chinois, Coréen (si applicable) |
| Format | En ligne, Présentiel, Individuel, etc. |
| Description | Texte libre de présentation |
| Prix | En DA (dinars) |
| Frais d'inscription | Frais supplémentaires éventuels |
| Durée | Nombre + unité (semaines ou mois) |
| Dates | Début et fin de la session |
| Capacité max | Nombre de places (laisser vide = illimité) |
| Min étudiants | Nombre minimum pour ouvrir la session |
| Dates inscription | Ouverture et fermeture des inscriptions en ligne |
| Instructions paiement | Texte affiché aux étudiants (ex : "Envoyez le paiement au CCP...") |
| Image | Photo/bannière de la session |

#### Horaires

En bas du formulaire, vous pouvez ajouter les **horaires** : jour de la semaine + heure de début/fin. Vous pouvez en ajouter plusieurs (ex : lundi et mercredi).

### Activer / désactiver une cohorte

Un bouton permet de **basculer** une cohorte entre active et inactive. Une cohorte inactive n'apparaît plus sur le site public.

### Supprimer une cohorte

La suppression n'est possible que si **aucune inscription n'est liée** à cette cohorte. Si des inscriptions existent, il faut d'abord les traiter.

---

## 9. Gérer le catalogue

**Page : Catalogue** (dans la sidebar)

Le catalogue contient 3 types d'éléments qui servent à organiser les sessions de cours :

### Catégories

Les grandes familles : **Langues**, **Ateliers artistiques**, **Ateliers culinaires**.
- Chaque catégorie a un nom, un slug (URL), un type et une icône optionnelle
- Vous pouvez en ajouter, modifier ou supprimer (si aucune cohorte n'y est rattachée)

### Langues

Les langues enseignées : **Japonais**, **Chinois**, **Coréen**.
- Chaque langue a un nom, un emoji drapeau et une URL d'image drapeau
- Utilisées pour filtrer les cohortes et les prospects

### Formats de cours

Les modalités d'enseignement : **En ligne**, **Présentiel**, **Individuel**, etc.
- Chaque format peut être marqué comme "en ligne" ou "individuel"
- Sert à catégoriser chaque session de cours

---

## 10. Modifier le contenu du site

**Page : Contenu** (dans la sidebar, sous-sections)

### Page d'accueil

Vous pouvez modifier **tout le contenu** de la page d'accueil :

| Section | Champs modifiables |
|---------|-------------------|
| **Héro** (bannière) | Titre, sous-titre, image de fond, texte du bouton, lien du bouton |
| **À propos** | Titre, texte descriptif, image |
| **Statistiques** | 4 chiffres + labels (ex : "500 étudiants", "15 professeurs") |
| **Témoignages** | 3 témoignages avec texte, nom de l'auteur et son rôle |
| **Appel à l'action** | Titre et texte final de la page |

> 📸 Les images uploadées sont **automatiquement optimisées** : redimensionnées (max 1920×1080) et converties en format WebP pour des chargements rapides.

### Paramètres du site

Ce sont les informations générales du site, utilisées partout :

| Catégorie | Champs |
|-----------|--------|
| **Contact** | Téléphone, email, adresse physique, lien Google Maps |
| **Réseaux sociaux** | Facebook, Instagram, TikTok, YouTube, WhatsApp |
| **SEO** | Nom du site, méta description, image Open Graph |
| **Horaires** | Horaires d'ouverture en texte libre |

---

## 11. Les statistiques (Analytics)

**Page : Analytics** (dans la sidebar)

Le site enregistre automatiquement les visites des pages publiques (pas le CMS ni l'admin). Tout est **anonymisé** : aucune adresse IP n'est stockée.

### Ce que vous pouvez voir

#### Indicateurs principaux
- **Pages vues** : nombre total de pages consultées
- **Visiteurs uniques** : nombre de personnes différentes
- **Sessions** : nombre de visites distinctes
- **Pages/session** : nombre moyen de pages vues par visite

#### Graphique de trafic
Un graphique jour par jour du nombre de visites. Très utile pour voir l'impact d'une campagne marketing.

#### Top 15 pages
Les pages les plus visitées, avec le nombre de vues.

#### Sources de trafic
D'où viennent vos visiteurs :
- **Direct** : ont tapé l'adresse directement
- **Google, Bing, etc.** : moteurs de recherche
- **Facebook, Instagram, etc.** : réseaux sociaux
- **ChatGPT, Gemini, etc.** : intelligences artificielles
- **Campagnes UTM** : liens marketing avec suivi

#### Appareils
Répartition entre :
- 💻 **Ordinateur** (Desktop)
- 📱 **Mobile**
- 📱 **Tablette**
- 🤖 **Bot** (robots de moteurs de recherche)

#### Navigateurs et systèmes d'exploitation
Chrome, Safari, Firefox... / Windows, iOS, Android...

#### Heures de pointe
À quelle heure de la journée vos visiteurs viennent le plus souvent.

#### Funnel de conversion
Le parcours typique des visiteurs :
1. Page d'accueil → 2. Pages de cours → 3. Page contact → 4. Page inscription

Montre le pourcentage de visiteurs qui passent d'une étape à l'autre.

### Filtrer par période

En haut de la page, vous pouvez choisir la période : **7 jours**, **14 jours**, **30 jours** ou **90 jours**.

---

## 12. Email marketing — Templates

**Page : Marketing > Templates** (dans la sidebar)

Un **template** est un modèle d'email réutilisable. Vous créez un template une fois, puis vous l'utilisez dans plusieurs campagnes.

### Créer un template

| Champ | Description |
|-------|-------------|
| Nom | Nom interne (ex : "Newsletter Printemps 2026") |
| Catégorie | welcome, newsletter, notification, promotional, transactional |
| Objet | Objet de l'email (peut être remplacé dans la campagne) |
| Contenu HTML | Le corps de l'email en HTML |
| Contenu texte | Version texte brut (pour les clients email qui ne lisent pas le HTML) |
| Actif | Oui/Non — les templates inactifs n'apparaissent pas dans la liste de sélection |

### Variables disponibles

Vous pouvez utiliser des **variables** dans vos templates. Elles seront automatiquement remplacées par les vraies données de chaque destinataire :

| Variable | Remplacée par |
|----------|--------------|
| `{{ first_name }}` | Prénom du destinataire |
| `{{ last_name }}` | Nom du destinataire |
| `{{ email }}` | Adresse email |
| `{{ site_name }}` | Nom du site (Institut Torii) |
| `{{ unsubscribe_url }}` | Lien de désinscription (ajouté automatiquement) |

### Prévisualiser

Avant d'envoyer, vous pouvez voir à quoi ressemblera l'email avec des données fictives.

---

## 13. Email marketing — Campagnes

**Page : Marketing > Campagnes** (dans la sidebar)

Une **campagne** envoie un template d'email à un groupe ciblé de destinataires.

### Créer une campagne

| Champ | Description |
|-------|-------------|
| Nom | Nom interne (ex : "Promo Chinois Mars 2026") |
| Template | Choisir parmi vos templates actifs |
| Objet | Optionnel — remplace l'objet du template |
| Adresse expéditeur | contact@, inscription@ ou notification@ |
| Répondre à | Adresse de réponse (optionnel) |
| Segment | Le groupe ciblé (voir ci-dessous) |

### Segments (groupes ciblés)

Le **segment** détermine qui recevra l'email :

| Segment | Description |
|---------|-------------|
| **Tous les prospects** | Toutes les personnes ayant rempli le formulaire de contact |
| **Tous les inscrits** | Toutes les personnes inscrites (tout statut) |
| **Inscrits confirmés** | Uniquement les inscrits dont l'inscription est confirmée |
| **Prospects par langue** | Prospects intéressés par une langue spécifique |
| **Inscrits par cohorte** | Inscrits à une session de cours spécifique |
| **Inscrits par langue** | Inscrits à une session de cours d'une langue spécifique |

> Les personnes désinscrites sont automatiquement exclues. Pas besoin de les retirer manuellement.

### Workflow d'envoi

1. **Créer** la campagne (statut : brouillon)
2. **Préparer les destinataires** : cliquez sur "Préparer les destinataires" — le système construit la liste à partir du segment
3. **Prévisualiser** : vérifiez le rendu de l'email
4. **Envoyer** : cliquez sur "Envoyer la campagne"
5. **Suivre** : observez les taux d'ouverture et de clics

### Statuts d'une campagne

| Statut | Signification |
|--------|---------------|
| 📝 Brouillon | En cours de rédaction |
| 📅 Programmée | Envoi prévu à une date future |
| 📤 En cours d'envoi | L'envoi est en cours |
| ✅ Envoyée | Tous les emails ont été envoyés |
| ⛔ Annulée | L'envoi a été annulé |

### Statistiques de campagne

Après envoi, la fiche de la campagne affiche :
- **Nombre total** de destinataires
- **Envoyés** : emails effectivement envoyés
- **Échoués** : emails qui n'ont pas pu être envoyés
- **Ouverts** : combien de personnes ont ouvert l'email
- **Cliqués** : combien ont cliqué sur un lien dans l'email
- **Taux d'ouverture** et **taux de clic** en pourcentage

---

## 14. Abonnés et désinscriptions

**Page : Marketing > Abonnés** (dans la sidebar)

Cette page montre la liste de toutes les adresses email connues et leur statut d'abonnement :
- ✅ **Abonné** : peut recevoir des campagnes
- ❌ **Désabonné** : ne recevra plus de campagnes marketing

### Comment quelqu'un se désinscrit

Chaque email marketing contient un lien **"Se désinscrire"** en bas. En cliquant dessus, la personne arrive sur une page de confirmation. Une fois désabonnée, elle ne recevra plus aucune campagne marketing.

> ⚠️ Les **notifications transactionnelles** (confirmation d'inscription, rejet, etc.) sont toujours envoyées, même si la personne s'est désinscrite des campagnes marketing. Ce sont des emails liés à une action de la personne, pas du marketing.

---

## 15. Historique des notifications

**Page : Marketing > Notifications** (dans la sidebar)

Cette page montre l'**historique complet** de tous les emails automatiques (transactionnels) envoyés par le système.

### Ce que vous voyez

Pour chaque notification :
- **Type** : contact reçu, inscription reçue/confirmée/rejetée/remboursée
- **Destinataire** : nom et email
- **Objet** de l'email
- **Statut** : envoyé ✅ ou échoué ❌
- **Date** d'envoi
- **Envoyé par** : automatique ou par quel administrateur

### Filtres disponibles

- Par **type** d'événement
- Par **statut** (envoyé/échoué)
- **Recherche** par nom ou email

### Détail d'une notification

En cliquant sur une notification, vous pouvez voir le **contenu exact** de l'email qui a été envoyé, tel que le destinataire l'a reçu.

---

## 16. Emails automatiques (notifications)

Le site envoie automatiquement des emails dans 5 situations :

| Quand | Email envoyé | À qui |
|-------|-------------|-------|
| Quelqu'un remplit le **formulaire de contact** | Confirmation de réception | Au visiteur |
| Quelqu'un **s'inscrit** en ligne | Confirmation de réception + code | À l'étudiant |
| Un admin **confirme** une inscription | Confirmation d'admission avec détails | À l'étudiant |
| Un admin **rejette** une inscription | Notification de rejet + motif | À l'étudiant |
| Un admin **rembourse** une inscription | Notification de remboursement | À l'étudiant |

### Ce que contiennent ces emails

**Après un contact :**
- Remerciement pour le message
- Confirmation que l'équipe reviendra rapidement

**Après une inscription :**
- Confirmation de réception du dossier
- Le **code de suivi** pour vérifier le statut
- Le nom de la session choisie

**Après confirmation par l'admin :**
- Félicitations et bienvenue
- Le nom de la session et la date de début
- Le code d'inscription

**Après rejet par l'admin :**
- Information du rejet
- Le **motif** saisi par l'admin
- Invitation à recontacter l'institut

**Après remboursement :**
- Confirmation que le remboursement est en cours
- Le nom de la session concernée

> Tous ces emails sont enregistrés dans l'**historique des notifications** (voir section 15).

---

## 17. Résumé des 3 adresses email

Le site utilise 3 adresses email distinctes :

| Adresse | Usage |
|---------|-------|
| **contact@institut-torii.com** | Campagnes marketing, réponses aux prospects |
| **inscription@institut-torii.com** | Tous les emails liés aux inscriptions (confirmation, rejet, remboursement) |
| **notification@institut-torii.com** | Alertes système, notifications internes |

Quand vous créez une campagne marketing, vous choisissez laquelle utiliser comme expéditeur.

---

## Besoin d'aide ?

Si vous rencontrez un problème ou avez besoin d'ajouter une fonctionnalité, consultez la **documentation technique** destinée aux développeurs, ou contactez l'équipe de développement.

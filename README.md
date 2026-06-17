# MSPR BLOC 2 — RNCP35584 | EPSI 2025/2026
## COFRAP — Plateforme d'Authentification Sécurisée Serverless

### Guide de Déploiement & Documentation Technique et Fonctionnelle Complète
#### K3S Single-Node + OpenFaaS + PostgreSQL + React Frontend sur Kubernetes

---

| Champ | Valeur de Référence |
| :--- | :--- |
| **Projet** | COFRAP — Authentification Sécurisée (MSPR Bloc 2) |
| **Équipe** | Hichem · Jalal · Lynda |
| **Dépôt GitHub** | [github.com/yoyo5053/mspr-cofrap](https://github.com/LyndaALGANI/mspr-auth-serverless.git) (branche `develop` / `main`) |
| **OS Cible** | Ubuntu / Debian (serveur Linux) |
| **Infrastructure** | K3S Single-Node (control-plane + worker sur 1 VM) |
| **Backend** | 3 fonctions OpenFaaS Python (`python3-http`) |
| **Frontend** | React 18 + Vite + Tailwind CSS |
| **Base de données** | PostgreSQL 16 (StatefulSet Kubernetes) |
| **Registre OCI** | Docker Hub |
| **Année** | 2025 / 2026 |

---

## SOMMAIRE
1. [Explication Fonctionnelle](#1-explication-fonctionnelle)
2. [Explication Technique & Architecture](#2-explication-technique--architecture)
3. [Technologies Utilisées & Justifications](#3-technologies-utilisees--justifications)
4. [Documentation Détaillée du Backend (Fonctions OpenFaaS)](#4-documentation-detaillee-du-backend-fonctions-openfaas)
5. [Documentation Détaillée du Frontend (React 18 + Nginx)](#5-documentation-detaillee-du-frontend-react-18--nginx)
6. [Documentation Détaillée de la Base de Données (PostgreSQL 16)](#6-documentation-detaillee-de-la-base-de-donnees-postgresql-16)
7. [Infrastructure, Docker & Orchestration Kubernetes](#7-infrastructure-docker--orchestration-kubernetes)
8. [Étapes de Déploiement Pas-à-Pas](#8-etapes-de-deploiement-pas-a-pas)
9. [Commandes Utiles pour le Debug](#9-commandes-utiles-pour-le-debug)
10. [Checklist Finale Avant la Soutenance](#10-checklist-finale-avant-la-soutenance)
11. [Variables de Référence](#11-variables-de-reference)

---

## 1. EXPLICATION FONCTIONNELLE

La plateforme COFRAP est une solution d'authentification centralisée à haute sécurité. Contrairement aux systèmes traditionnels où l'utilisateur choisit son mot de passe (ce qui conduit souvent à des mots de passe faibles ou réutilisés), COFRAP impose un paradigme de sécurité stricte : **les mots de passe sont générés aléatoirement par le serveur, couplés à une double authentification (2FA/TOTP) obligatoire, et soumis à une expiration automatique de 6 mois**.

### 1.1. Les Trois Parcours Utilisateurs Principaux

```
[ Inscription ] --------> [ Connexion ] <-------- [ Expiration (6 mois) ]
      |                        |                          |
      v                        v                          v
Génération Password     Saisie User + Pw        Blocage de l'accès
      +                        +                          +
Génération TOTP          Saisie Code 2FA      Bouton "Régénérer mot de passe"
      |                        |                          |
      v                        v                          v
  Validation               Connexion                 Redirection 
  et Activation            Réussie                   vers /renew
```

#### A. Inscription (`/register`)
Le processus d'inscription se déroule de manière séquentielle et sécurisée en 3 étapes :
1. **Étape 1 : Saisie de l'identifiant**  
   L'utilisateur choisit un nom d'utilisateur. Le format est validé côté frontend et backend (entre 8 et 20 caractères, uniquement des lettres, chiffres, tirets, underscores ou points).
2. **Étape 2 : Récupération du mot de passe fort**  
   Le serveur génère un mot de passe aléatoire de 24 caractères alphanumériques. Ce mot de passe est présenté à l'utilisateur sous la forme d'un **Code QR unique**. L'utilisateur doit scanner ce code pour obtenir son mot de passe et le coller dans le champ de vérification pour attester qu'il l'a bien enregistré.
3. **Étape 3 : Configuration du double facteur (2FA)**  
   Le serveur génère une clé TOTP unique et présente un second QR Code de configuration. L'utilisateur le scanne avec une application dédiée (comme Google Authenticator ou Microsoft Authenticator) et saisit le code à 6 chiffres généré par son application pour valider la synchronisation. L'inscription est alors finalisée.

#### B. Connexion (`/login`)
L'utilisateur accède à un formulaire unifié :
1. Saisie de son **Identifiant**.
2. Saisie de son **Mot de passe de 24 caractères**.
3. Saisie du **Code 2FA temporaire à 6 chiffres**.
* *Résultat attendu* : Si les trois éléments concordent et que le mot de passe est valide (moins de 180 jours d'existence), l'authentification est approuvée et l'accès est accordé.

#### C. Gestion de l'Expiration et du Renouvellement (`/renew`)
* **Expiration après 180 jours (6 mois)** : À chaque tentative de connexion, le serveur calcule l'âge du mot de passe (en comparant la date actuelle à la date de génération stockée). Si le mot de passe a plus de 180 jours ou si le compte a été marqué comme expiré, la connexion est refusée.
* **Comportement de l'interface utilisateur** : La page de connexion affiche un message d'erreur rouge explicite : *"Votre mot de passe a expiré. Veuillez régénérer votre mot de passe"*. Ce message inclut dynamiquement un bouton **"Régénérer mon mot de passe"** qui redirige automatiquement l'utilisateur vers la page de renouvellement avec son identifiant pré-rempli (`/renew?username=nom_utilisateur`).
* **Renouvellement** : L'accès à la page `/renew` est strictement réservé au processus d'expiration. L'utilisateur y régénère un nouveau mot de passe fort de 24 caractères (QR Code) et reconfigure un nouveau secret TOTP. Cette procédure réinitialise la date de création (`gendate` mise à jour à la date du jour) et remet à zéro le statut d'expiration, accordant à nouveau un cycle de 6 mois d'accès.

---

## 2. EXPLICATION TECHNIQUE & ARCHITECTURE

D'un point de vue technique, le projet COFRAP repose sur une **architecture serverless moderne et découplée**, orchestrée sur un cluster Kubernetes Kubernetes K3s à un seul nœud (Single-Node).

```
               +-------------------------------------------------+
               |             Navigateur Client (React)           |
               +-------------------------------------------------+
                                       |
                                       | (Requêtes HTTP via API REST)
                                       v
               +-------------------------------------------------+
               |            Traefik Ingress Controller           |
               +-------------------------------------------------+
                       /                                 \
                      / (Chemin: /)                       \ (Chemin: /function/)
                     v                                     v
       +----------------------------+        +----------------------------+
       |   Service Frontend (Nginx) |        |    OpenFaaS Gateway Svc    |
       +----------------------------+        +----------------------------+
                     |                                     |
                     v                                     v
       +----------------------------+        +----------------------------+
       |    Pods Frontend (React)   |        |   Pods OpenFaaS Functions  |
       |         2 Répliques        |        |   (python3-http runner)    |
       +----------------------------+        +----------------------------+
                                                           |
                                                           | (Connexion PostgreSQL)
                                                           v
                                             +----------------------------+
                                             |  Service PostgreSQL (5432) |
                                             +----------------------------+
                                                           |
                                                           v
                                             +----------------------------+
                                             |  Pod PostgreSQL (Stateful) |
                                             |    Volume Persistant 10G   |
                                             +----------------------------+
```

### 2.1. Fonctionnement Technique Global

1. **Routage Externe & Ingress** : Le point d'entrée unique de la VM est géré par **Traefik**, le contrôleur d'Ingress par défaut de K3s. Il écoute le trafic HTTP entrant :
   * Les requêtes vers `/` (racine) sont redirigées vers le service **Frontend Nginx**.
   * Les requêtes vers `/function/` sont acheminées vers la **Gateway d'OpenFaaS**.
2. **Le Frontend (React SPA)** : Compilé sous forme d'assets statiques (HTML, JS, CSS) et hébergé dans un serveur **Nginx**. Il s'exécute entièrement dans le navigateur du client.
3. **Le Backend Serverless (OpenFaaS)** : L'infrastructure OpenFaaS écoute les requêtes API asynchrones. Lorsque la Gateway d'OpenFaaS reçoit une requête, elle la transmet au pod de la fonction Python concernée. Si aucun pod n'est actif, le système démarre automatiquement un conteneur pour répondre (Auto-scaling).
4. **Persistance et Chiffrement (PostgreSQL 16)** : Les fonctions Python interrogent le serveur PostgreSQL local via des pilotes natifs. Avant d'écrire le mot de passe dans la base de données, la fonction le chiffre en utilisant l'algorithme symétrique **Fernet**. La clé de chiffrement est récupérée de manière sécurisée depuis les secrets natifs de Kubernetes.

---

## 3. TECHNOLOGIES UTILISÉES & JUSTIFICATIONS

Le choix des technologies répond à des critères stricts de sécurité, d'évolutivité, de légèreté et de facilité de maintenance.

### 3.1. Tableau des Technologies Utilisées

| Catégorie | Technologie | Rôle dans COFRAP | Justification de son Choix |
| :--- | :--- | :--- | :--- |
| **Frontend** | **React 18** | Framework UI principal | Permet de construire une interface réactive à composants réutilisables, idéale pour gérer l'état local complexe des formulaires en 3 étapes. |
| **Frontend** | **Vite** | Outil d'assemblage (Build tool) | Offre un serveur de développement ultra-rapide avec Hot Module Replacement (HMR) et compile les fichiers statiques de production de manière optimisée. |
| **Styling** | **Tailwind CSS** | Framework CSS utilitaire | Permet de designer l'interface moderne (verre dépoli, orbes de couleur, responsive) directement dans le code sans écrire de gros fichiers CSS externes. |
| **Serveur Frontend**| **Nginx (Alpine)** | Hébergement statique du Frontend | Serveur web extrêmement performant et peu gourmand en ressources, configuré pour rediriger toutes les requêtes vers l'index pour préserver le routage React. |
| **Backend / FaaS**  | **OpenFaaS** | Framework Serverless | Permet de découper la logique métier en petites fonctions indépendantes, évitant de maintenir un serveur backend monolithique lourd. |
| **Langage Backend** | **Python 3.10+** | Langage d'écriture des fonctions | Syntaxe claire, démarrage rapide (essentiel en Serverless pour éviter les démarrages à froid lents) et écosystème de sécurité très riche. |
| **Base de Données** | **PostgreSQL 16** | Stockage persistant relationnel | Base de données solide, sécurisée et ACID, déployée avec un volume persistant pour garantir que les données utilisateurs survivent aux redémarrages. |
| **Orchestrateur K8s**| **K3s (Rancher)** | Orchestrateur de conteneurs | Version ultra-légère de Kubernetes, optimisée pour s'exécuter sur un seul serveur avec moins de 512 Mo de RAM consommée par le moteur. |
| **Proxy / Ingress** | **Traefik** | Ingress Controller | Inclus par défaut dans K3s, il gère le routage réseau, l'acheminement CORS, et sert de passerelle d'accès externe unique pour les clients. |
| **Dépendance Python**| **PyOTP** | Moteur de double facteur (TOTP) | Implémente de façon standardisée l'algorithme TOTP (RFC 6238) pour valider les codes de sécurité à 6 chiffres. |
| **Dépendance Python**| **Cryptography** | Moteur de Chiffrement | Fournit l'implémentation robuste de **Fernet** (chiffrement symétrique AES-128/256-CBC authentifié par HMAC-SHA256) pour sécuriser les secrets. |
| **Dépendance Python**| **psycopg2-binary**| Connecteur PostgreSQL | Pilote PostgreSQL natif pour Python permettant d'exécuter rapidement les requêtes et les transactions SQL. |
| **Dépendance Python**| **qrcode** | Générateur de QR Codes | Génère instantanément au format PNG les codes QR du mot de passe brut ou de l'URI OTP pour l'utilisateur. |

---

## 4. DOCUMENTATION DÉTAILLÉE DU BACKEND (FONCTIONS OPENFAAS)

Le backend est segmenté en **3 fonctions indépendantes** basées sur le modèle d'OpenFaaS `python3-http`. Elles partagent un en-tête CORS standard autorisant les méthodes `GET, POST, OPTIONS`.

### 4.1. Fonction : `generate-password`
* **Chemin API** : `/function/generate-password`
* **Fichier source** : [functions/generate-password/handler.py](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/generate-password/handler.py)
* **Objectif** : Validation de l'identifiant, création de l'utilisateur ou mise à jour de son mot de passe lors du renouvellement.
* **Corps de la requête (POST)** :
  ```json
  {
    "username": "nom_utilisateur",
    "renew": true // Optionnel (défaut: false). Indique s'il s'agit d'un renouvellement.
  }
  ```
* **Logique et Algorithme** :
  1. **Validation syntaxique** : Vérifie l'identifiant par expression régulière (`^[a-zA-Z0-9_.-]{8,20}$`).
  2. **Vérification en Base** :
     * **Si `renew: false` (Inscription)** : Si l'utilisateur existe déjà en BDD, la fonction retourne immédiatement `username_already_exists` (HTTP 400).
     * **Si `renew: true` (Renouvellement)** : Si l'utilisateur n'existe pas, retourne `user_not_found` (HTTP 404).
  3. **Génération du mot de passe** : Génère une chaîne aléatoire de 24 caractères alphanumériques (lettres majuscules/minuscules + chiffres).
  4. **Chiffrement** : Chiffre le mot de passe généré en utilisant l'instance **Fernet**.
  5. **Mise à jour / Insertion** :
     * S'il s'agit d'une inscription, insère une ligne : `INSERT INTO users (username, password, mfa, gendate, expired) VALUES (...)`.
     * S'il s'agit d'un renouvellement, met à jour la ligne existante : réinitialise le mot de passe, vide la clé `mfa`, met à jour la date `gendate` à aujourd'hui et réinitialise l'état `expired = 0`.
  6. **Génération du QR Code** : Génère un QR Code contenant le mot de passe en clair pour affichage côté client, convertit l'image PNG en Base64.
* **Réponse (HTTP 200)** :
  ```json
  {
    "qr_code": "iVBORw0KGgoAAAANS..." // Image PNG encodée en Base64
  }
  ```

### 4.2. Fonction : `generate-2fa`
* **Chemin API** : `/function/generate-2fa`
* **Fichier source** : [functions/generate-2fa/handler.py](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/generate-2fa/handler.py)
* **Objectif** : Générer et enregistrer la clé secrète de double authentification (TOTP) de l'utilisateur.
* **Corps de la requête (POST)** :
  ```json
  {
    "username": "nom_utilisateur",
    "password": "mot_de_passe_de_24_caracteres"
  }
  ```
* **Logique et Algorithme** :
  1. Recherche de l'utilisateur et déchiffrement de son mot de passe stocké. S'ils ne correspondent pas, retourne `invalid_password` (HTTP 400).
  2. Génération d'une clé secrète de 32 caractères codée en Base32 (`pyotp.random_base32()`).
  3. Mise à jour de la table `users` en enregistrant ce secret TOTP dans la colonne `mfa`.
  4. Création de l'URI standardisée de provisionnement : `otpauth://totp/COFRAP:username?secret=SECRET&issuer=COFRAP`.
  5. Génération du QR Code de configuration contenant cette URI, encodé en Base64.
* **Réponse (HTTP 200)** :
  ```json
  {
    "qr_code": "iVBORw0KGgoAAAANS..." // QR Code de configuration 2FA
  }
  ```

### 4.3. Fonction : `authenticate`
* **Chemin API** : `/function/authenticate`
* **Fichier source** : [functions/authenticate/handler.py](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/authenticate/handler.py)
* **Objectif** : Authentifier l'utilisateur par triple facteur (nom d'utilisateur, mot de passe et jeton TOTP) et vérifier le statut d'expiration.
* **Corps de la requête (POST)** :
  ```json
  {
    "username": "nom_utilisateur",
    "password": "mot_de_passe_de_24_caracteres",
    "totp_code": "123456"
  }
  ```
* **Logique et Algorithme** :
  1. Recherche de l'utilisateur. Déchiffrement et comparaison du mot de passe. En cas d'échec, retourne `invalid_credentials` (HTTP 401).
  2. **Vérification d'expiration** : 
     * Récupère la date `gendate` et le marqueur `expired`.
     * Calcule la différence en jours entre aujourd'hui et `gendate`.
     * Si la différence dépasse 180 jours (6 mois) ou si `expired == 1`, la fonction renvoie immédiatement une erreur d'expiration : `{"error": "expired_password", "expired": true}` (HTTP 401).
  3. **Vérification 2FA** : 
     * Récupère le secret TOTP dans la base de données.
     * Instancie l'outil de validation OTP : `pyotp.TOTP(mfa_secret)`.
     * Valide le code à 6 chiffres fourni. Si incorrect ou expiré (durée de vie d'un jeton = 30 secondes), retourne `invalid_totp` (HTTP 401).
* **Réponse (HTTP 200)** :
  ```json
  {
    "status": "success",
    "message": "Authentification reussie"
  }
  ```

---

## 5. DOCUMENTATION DÉTAILLÉE DU FRONTEND (REACT 18 + NGINX)

L'application Frontend est construite sous forme de Single Page Application (SPA). Elle s'exécute uniquement dans le navigateur client et utilise des appels asynchrones (`fetch`) vers l'API.

### 5.1. Gestion des Écrans (State Management)
* **Composant unique de contrôle** : [App.jsx](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/src/App.jsx) gère à la fois l'affichage des trois routes de base (`/register`, `/login`, `/renew`) et le cycle interne de chaque vue.
* **Formulaires multi-étapes** : Les écrans d'inscription et de renouvellement partagent un état local `step` (valeurs de 1 à 4). Cela permet d'afficher les éléments au fur et à mesure sans changer d'URL :
  - *Étape 1* : Saisie identifiant $\rightarrow$ Appel API et affichage QR Code mot de passe.
  - *Étape 2* : Saisie et vérification du mot de passe $\rightarrow$ Appel API et affichage QR Code TOTP.
  - *Étape 3* : Saisie du code TOTP $\rightarrow$ Appel API pour validation finale.
  - *Étape 4* : Succès, bouton de redirection vers la connexion.

### 5.2. Compilation & Serveur Nginx Interne
* **Compilation** : Vite compile les fichiers JSX, Tailwind et Javascript en un bundle de fichiers plats hautement optimisés dans le dossier `/dist`.
* **Problématique du Routage SPA** : Dans une SPA, le routage est géré côté navigateur. Si un utilisateur recharge sa page lorsqu'il se trouve sur la route `/renew`, le navigateur interroge le serveur Nginx pour obtenir le fichier physique `/renew` qui n'existe pas.
* **Solution de contournement (nginx.conf)** : Le fichier de configuration Nginx intercepte les requêtes. Grâce à la directive `try_files $uri $uri/ /index.html`, si la ressource demandée n'est pas présente physiquement, Nginx retourne le fichier principal `index.html`. C'est ensuite le routeur JavaScript (`react-router-dom`) qui prend le relais pour afficher la vue `/renew`.

---

## 6. DOCUMENTATION DÉTAILLÉE DE LA BASE DE DONNÉES (POSTGRESQL 16)

La persistance des données repose sur un conteneur PostgreSQL 16 isolé et sécurisé.

### 6.1. Dictionnaire de Données (Table `users`)

| Nom de la Colonne | Type de Données | Contraintes | Rôle / Description |
| :--- | :--- | :--- | :--- |
| **`id`** | `SERIAL` | `PRIMARY KEY` | Identifiant interne auto-incrémenté. |
| **`username`** | `VARCHAR(100)` | `NOT NULL UNIQUE` | Identifiant unique choisi par l'utilisateur. |
| **`password`** | `VARCHAR(255)` | `NOT NULL` | Contient le mot de passe de 24 caractères, chiffré symétriquement au format Fernet. |
| **`mfa`** | `VARCHAR(100)` | `DEFAULT ''` | Contient le secret Base32 brut utilisé par PyOTP pour valider le 2FA. |
| **`gendate`** | `DATE` | `NOT NULL` | Date de génération du mot de passe (mise à jour lors d'une inscription ou d'un renouvellement). |
| **`expired`** | `INTEGER` | `NOT NULL DEFAULT 0`| Indicateur forcé d'expiration (0 = actif, 1 = expiré forcé). |

### 6.2. Chiffrement Fernet Appliqué en Base
* **Confidentialité accrue** : En cas de compromission ou d'extraction brute de la base de données, les mots de passe ne sont pas exploitables car ils sont chiffrés avec une clé de sécurité secrète.
* **Fonctionnement du Chiffrement** : La bibliothèque Python `cryptography` génère une clé secrète Fernet unique. Les fonctions chiffrent la chaîne brute en binaire, la convertissent en texte Base64 et l'enregistrent en BDD. Lors de la connexion, le backend extrait le texte chiffré, applique la clé pour décrypter le mot de passe initial et le compare avec la saisie utilisateur.
* **Cycle de vie de la clé de chiffrement** : La clé est lue en priorité depuis `/var/openfaas/secrets/encryption-key` (secret Kubernetes). Si la clé n'est pas déclarée dans le secret, le système utilise la variable d'environnement `ENCRYPTION_KEY` déclarée par défaut dans la fonction.

---

## 7. INFRASTRUCTURE, DOCKER & ORCHESTRATION KUBERNETES

L'application est conteneurisée et déployée de manière robuste sur un cluster Kubernetes K3s à un nœud.

```
+---------------------------------------------------------------------------------+
|                                 SERVEUR LINUX (VM)                              |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                       K3S LIGHTWEIGHT KUBERNETES                        |   |
|   |                                                                         |   |
|   |   +-------------------+  +-------------------+  +-------------------+   |   |
|   |   | Namespace: cofrap |  | Namespace: openfaas| |Namespace: openfaas-fn|  |   |
|   |   |                   |  |                   |  |                   |   |   |
|   |   | - Pods Frontend   |  | - Pod Gateway     |  | - Pod generate-pw |   |   |
|   |   | - Pod Postgresql  |  | - Pod Traefik     |  | - Pod generate-2fa|   |   |
|   |   |                   |  | - Secrets/Config  |  | - Pod authenticate|   |   |
|   |   +-------------------+  +-------------------+  +-------------------+   |   |
|   +-------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------+
```

### 7.1. Le Serveur
* **Hôte** : VM Linux (Ubuntu/Debian) avec un accès externe sécurisé.
* **Distribution Kubernetes** : **K3s** de Rancher. C'est une distribution certifiée CNCF, conçue pour être très légère, empaquetée dans un seul binaire, et intégrant par défaut Traefik (contrôleur d'Ingress), CoreDNS et les mécanismes de stockage locaux.

### 7.2. Conteneurisation (Docker)
Chaque composant applicatif possède son environnement conteneurisé :
* **Les Fonctions Backend** : Elles sont packagées sous forme d'images OCI. `faas-cli` orchestre le build Docker en utilisant le gabarit de conteneur d'OpenFaaS, installant les paquets du fichier `requirements.txt` sur une base légère Python.
* **Le Frontend** : Il utilise un fichier [Dockerfile](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/Dockerfile) multi-étapes (multi-stage build) :
  1. *Étape 1 (Build)* : Téléchargement de l'image NodeJS, copie du code source, installation des dépendances et compilation via la commande `npm run build` ou `vite build`.
  2. *Étape 2 (Serve)* : Copie uniquement du dossier compilé `/dist` final vers un conteneur Nginx Alpine léger. L'image finale ne contient aucun code source ni outil de développement, réduisant sa taille à moins de 30 Mo et augmentant la sécurité.

### 7.3. Orchestration & Déploiement Kubernetes (k8s)
Le dossier [k8s/](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s) contient les déclarations de l'ensemble des objets Kubernetes nécessaires :

1. **`01-namespace.yaml`** : Crée le namespace de travail isolé `cofrap`.
2. **`02-secrets.yaml`** : Contient de manière centralisée les variables sensibles (`DATABASE_URL` et `ENCRYPTION_KEY`). Ces secrets sont mappés dans les variables d'environnement des pods.
3. **`03-postgres-configmap.yaml`** : Déclare le fichier SQL d'initialisation (`init.sql`) de la base de données. Ce script crée la table `users` et définit ses contraintes.
4. **`04-postgres-pvc.yaml`** : Demande d'allocation de volume persistant (PVC) de 10 Go. Cela garantit que les données de PostgreSQL sont enregistrées sur le disque de la VM hôte et ne sont pas perdues en cas de crash du pod.
5. **`05-postgres-service.yaml`** : Service interne qui expose le port 5432 de PostgreSQL pour que les fonctions backend puissent s'y connecter via l'adresse DNS interne `postgres.cofrap.svc.cluster.local`.
6. **`06-postgres-statefulset.yaml`** : Déploiement de type StatefulSet (dédié aux bases de données) exécutant PostgreSQL 16. Il monte le ConfigMap d'initialisation dans `/docker-entrypoint-initdb.d/` et attache le volume persistant.
7. **`07-frontend-deployment.yaml`** : Déploie 2 répliques (pods) du conteneur Frontend avec l'image construite (version v3, `imagePullPolicy: IfNotPresent` pour forcer l'usage de la nouvelle image déployée).
8. **`08-frontend-service.yaml`** : Service Kubernetes de type ClusterIP exposant le port 80 du frontend.
9. **`09-frontend-ingress.yaml`** : Route d'Ingress gérée par Traefik redirigeant les requêtes HTTP externes vers le service frontend.
10. **`10-openfaas-ingress.yaml`** : Route d'Ingress permettant au frontend d'interroger la Gateway d'OpenFaaS externe via le chemin `/function/`.
11. **`11-traefik-cors-middleware.yaml`** : Middleware Traefik qui configure les en-têtes CORS (Access-Control-Allow-Origin, Methods, Headers) au niveau du proxy pour autoriser les échanges réseau sécurisés cross-origin.

---

## 8. ÉTAPES DE DÉPLOIEMENT PAS-À-PAS

### Étape 1 : Installation K3S (single-node)
**Responsable : P1 — Responsable Infrastructure** | **Durée estimée : ~30 min**

#### 1.1 — Installer K3S
```bash
# Installation en une commande
curl -sfL https://get.k3s.io | sh -

# Attendre ~1 minute puis vérifier
sudo kubectl get nodes
# Résultat attendu : STATUS = Ready
```

#### 1.2 — Configurer kubectl sans sudo
```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config

# Tester sans sudo
kubectl get nodes
```

#### 1.3 — Installer Helm v3
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

#### 1.4 — Installer faas-cli
```bash
curl -sL https://cli.openfaas.com | sudo sh
faas-cli version
```

* **Checkpoint 1** : `kubectl get nodes` $\rightarrow$ 1 node Ready. `helm version` OK. `faas-cli version` OK.

---

### Étape 2 : Déploiement OpenFaaS via Helm
**Responsable : P1 — Responsable Infrastructure** | **Durée estimée : ~30 min**

#### 2.1 — Créer les namespaces OpenFaaS
```bash
kubectl apply -f https://raw.githubusercontent.com/openfaas/faas-netes/master/namespaces.yml

# Vérifier : doit afficher openfaas et openfaas-fn
kubectl get namespaces | grep openfaas
```

#### 2.2 — Ajouter le repo Helm FaaSNetes
```bash
helm repo add openfaas https://openfaas.github.io/faas-netes/
helm repo update
```

#### 2.3 — Générer le mot de passe admin et créer le secret
```bash
# Générer et noter le mot de passe
PASSWORD=$(head -c 12 /dev/urandom | shasum | cut -d' ' -f1)
echo "Mot de passe OpenFaaS : $PASSWORD"

kubectl -n openfaas create secret generic basic-auth \
  --from-literal=basic-auth-user=admin \
  --from-literal=basic-auth-password=$PASSWORD
```

#### 2.4 — Déployer OpenFaaS via Helm
```bash
helm upgrade --install openfaas openfaas/openfaas \
  --namespace openfaas \
  --set functionNamespace=openfaas-fn \
  --set basic_auth=true \
  --set serviceType=NodePort \
  --set faasnetes.imagePullPolicy=Always

# Attendre que les pods soient Running (~2-3 min)
kubectl -n openfaas get pods --watch
```

#### 2.5 — Récupérer l'URL de la gateway et se connecter
```bash
# Construire l'URL de la gateway
NODE_IP=$(hostname -I | awk '{print $1}')
NODE_PORT=$(kubectl -n openfaas get svc gateway-external \
  -o jsonpath='{.spec.ports[0].nodePort}')
export GATEWAY_URL="http://$NODE_IP:$NODE_PORT"
echo "Gateway OpenFaaS : $GATEWAY_URL"

# Login faas-cli
faas-cli login --username admin --password $PASSWORD --gateway $GATEWAY_URL

# Test de connectivité
curl $GATEWAY_URL/healthz
```

* **Checkpoint 2** : `curl $GATEWAY_URL/healthz` répond OK. `faas-cli login` réussi.

---

### Étape 3 : Déploiement PostgreSQL sur Kubernetes
**Responsable : P3 — Responsable Backend** | **Durée estimée : ~20 min**

#### 3.1 — Générer la clé Fernet et mettre à jour le secret
```bash
# Générer la clé de chiffrement Fernet
FERNET_KEY=$(python3 -c \
  "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "Clé Fernet : $FERNET_KEY"
```
Ouvrez le fichier [02-secrets.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/02-secrets.yaml) et remplacez la valeur de `ENCRYPTION_KEY` :
```yaml
stringData:
  ENCRYPTION_KEY: "VOTRE_CLE_FERNET_GENEREE"
  DATABASE_URL: "postgresql://cofrap:cofrap@postgres.cofrap.svc.cluster.local:5432/cofrap"
```

#### 3.2 — Déployer PostgreSQL
```bash
kubectl apply -f k8s/01-namespace.yaml
kubectl apply -f k8s/02-secrets.yaml
kubectl apply -f k8s/03-postgres-configmap.yaml
kubectl apply -f k8s/04-postgres-pvc.yaml
kubectl apply -f k8s/05-postgres-service.yaml
kubectl apply -f k8s/06-postgres-statefulset.yaml

# Attendre que PostgreSQL soit prêt
kubectl wait --for=condition=ready pod \
  -n cofrap -l app=postgres --timeout=300s
```

#### 3.3 — Vérifier la connexion à la BDD
```bash
kubectl exec -it -n cofrap postgres-0 -- psql -U cofrap -d cofrap -c "\dt"
```

* **Checkpoint 3** : `postgres-0` en `Running`. Les tables de la base de données s'affichent correctement.

---

### Étape 4 : Création des secrets OpenFaaS pour les fonctions
**Responsable : P1 — Responsable Infrastructure** | **Durée estimée : ~15 min**

#### 4.1 — Créer le secret encryption-key
```bash
faas-cli secret create encryption-key \
  --from-literal="$FERNET_KEY" \
  --gateway $GATEWAY_URL
```

#### 4.2 — Vérifier les secrets
```bash
faas-cli secret list --gateway $GATEWAY_URL
```

* **Checkpoint 4** : `faas-cli secret list` affiche `encryption-key`.

---

### Étape 5 : Build, Push et Déploiement des 3 fonctions OpenFaaS
**Responsable : P2 — Responsable Backend Fonctions** | **Durée estimée : ~45 min**

#### 5.1 — Préparer Docker Hub et le template python3-http
```bash
docker login
faas-cli template pull https://github.com/openfaas/python-flask-template
```

#### 5.2 — Mettre à jour `stack.yaml`
Modifiez le fichier [stack.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/stack.yaml) pour l'adapter à votre registre d'images Docker Hub et vos paramètres d'URL de Gateway.

#### 5.3 — Déployer les fonctions
```bash
# Builder les images
faas-cli build -f stack.yml

# Pousser sur Docker Hub
faas-cli push -f stack.yml

# Déployer les fonctions
faas-cli deploy -f stack.yml --gateway $GATEWAY_URL

# Vérifier
faas-cli list --gateway $GATEWAY_URL
```

* **Checkpoint 5** : `faas-cli list` retourne les 3 fonctions avec 1 réplique active chacune.

---

### Étape 6 : Déploiement du Frontend React
**Responsable : P4 — Responsable Frontend** | **Durée estimée : ~20 min**

#### 6.1 — Builder l'image frontend avec la bonne URL gateway
```bash
docker build \
  --build-arg VITE_GATEWAY_URL=http://IP_VM:NODE_PORT \
  -t TON_USERNAME/cofrap-frontend:v3 \
  ./frontend

docker push TON_USERNAME/cofrap-frontend:v3
```

#### 6.2 — Appliquer les manifests frontend
Mettez à jour le manifest [07-frontend-deployment.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/07-frontend-deployment.yaml) avec votre identifiant d'image (tag `v3`), puis déployez :
```bash
kubectl apply -f k8s/07-frontend-deployment.yaml
kubectl apply -f k8s/08-frontend-service.yaml
kubectl apply -f k8s/09-frontend-ingress.yaml

kubectl rollout restart deployment frontend -n cofrap
```

#### 6.3 — Exposer et accéder au frontend
```bash
kubectl port-forward -n cofrap svc/frontend 8080:80 --address 0.0.0.0 &
```

* **Checkpoint 6** : Le portail est accessible à l'adresse `http://IP_VM:8080`.

---

### Étape 7 : Tests End-to-End et Validation
**Responsable : Toute l'équipe** | **Durée estimée : ~30 min**

Effectuez les scénarios de test complets détaillés ci-dessous :
1. **Inscription (`/register`)** $\rightarrow$ Génération réussie du mot de passe fort (QR) + configuration TOTP.
2. **Double Facteur (TOTP)** $\rightarrow$ Jeton valide généré par l'application mobile.
3. **Connexion (`/login`)** $\rightarrow$ Authentification réussie et redirection.
4. **Erreurs de sécurité** $\rightarrow$ Rejet des mauvais identifiants ou mauvais TOTP.
5. **Expiration** $\rightarrow$ Blocage au bout de 180 jours (6 mois) et affichage du bouton vers la page `/renew` pour forcer la reconfiguration.

---

## 9. COMMANDES UTILES POUR LE DEBUG

### 9.1. Diagnostics Généraux
```bash
# Vérifier l'état de l'ensemble des pods du cluster
kubectl get pods -A

# Inspecter la description d'un pod en erreur
kubectl describe pod NOM_DU_POD -n NOM_NAMESPACE
```

### 9.2. Logs en direct
```bash
# Logs des fonctions
kubectl logs -n openfaas-fn -l faas_function=authenticate
kubectl logs -n openfaas-fn -l faas_function=generate-password
kubectl logs -n openfaas-fn -l faas_function=generate-2fa

# Logs frontend et BDD
kubectl logs -n cofrap deployment/frontend -f
kubectl logs -n cofrap statefulset/postgres -f
```

---

## 10. CHECKLIST FINALE AVANT LA SOUTENANCE

* [x] **Infrastructure** : K3S installé et node `Ready`. Helm v3 installé. `faas-cli` opérationnel.
* [x] **OpenFaaS** : Gateway accessible en externe. `faas-cli login` réussi. `curl /healthz` répond OK.
* [x] **Base de données** : `postgres-0` en statut Running 1/1. Tables SQL initialisées. Connexions acceptées.
* [x] **Secrets** : Secret `encryption-key` créé dans OpenFaaS. Fichier [02-secrets.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/02-secrets.yaml) mis à jour dans le cluster.
* [x] **Fonctions** : Les 3 images publiées sur Docker Hub. `faas-cli list` affiche les 3 fonctions comme actives.
* [x] **Tests API** : `generate-password` retourne un QR code. `generate-2fa` fournit QR. `authenticate` répond success.
* [x] **Frontend** : Image construite avec `VITE_GATEWAY_URL` correct. Pods en statut Running. Accessible sur `http://IP_VM:8080`.
* [x] **Tests E2E** : Validation des scénarios d'inscriptions, connexion, et expiration.

---

## 11. VARIABLES DE RÉFÉRENCE

Complétez ce tableau avec les valeurs réelles de votre déploiement pour la soutenance :

| Variable | Valeur de Déploiement |
| :--- | :--- |
| **IP du serveur (VM)** | *À compléter* |
| **GATEWAY_URL** | `http://IP_VM:NODE_PORT` |
| **NODE_PORT OpenFaaS** | *À compléter* (via `kubectl -n openfaas get svc gateway-external`) |
| **Mot de passe OpenFaaS admin** | *À noter et conserver précieusement* |
| **Clé Fernet (ENCRYPTION_KEY)** | `Rt9LIv0sl8hVk_UjrxDB2QoACvrPoJmVVxuM5OdM5_o=` (Exemple) |
| **Identifiant Docker Hub** | *À compléter* |
| **URL Frontend de Production** | `http://IP_VM:8080` |
| **DATABASE_URL Interne** | `postgresql://cofrap:cofrap@postgres.cofrap.svc.cluster.local:5432/cofrap` |

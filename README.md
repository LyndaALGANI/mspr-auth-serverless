# MSPR BLOC 2 — RNCP35584 | EPSI 2025/2026
## COFRAP — Plateforme d'Authentification Sécurisée

### Guide de Déploiement & Documentation Technique Complète
#### K3S Single-Node + OpenFaaS + PostgreSQL + React Frontend
##### Architecture Serverless sur Kubernetes

---

| Champ | Valeur de Référence |
| :--- | :--- |
| **Projet** | COFRAP — Authentification Sécurisée (MSPR Bloc 2) |
| **Équipe** | Youssef · Cardinal · Elauriche · Faouz |
| **Dépôt GitHub** | [github.com/yoyo5053/mspr-cofrap](https://github.com/LyndaALGANI/mspr-auth-serverless.git) (branche `develop` / `main`) |
| **OS Cible** | Ubuntu / Debian (serveur Linux) |
| **Infrastructure** | K3S Single-Node (control-plane + worker sur 1 VM) |
| **Backend** | 4 fonctions OpenFaaS Python (`python3-http`) |
| **Frontend** | React 18 + Vite + Tailwind CSS |
| **Base de données** | PostgreSQL 16 (StatefulSet Kubernetes) |
| **Registre OCI** | Docker Hub |
| **Année** | 2025 / 2026 |

---

## SOMMAIRE
1. [Architecture globale de la solution](#1-architecture-globale-de-la-solution)
2. [Prérequis avant de commencer](#2-prerequis-avant-de-commencer)
3. [Documentation de la Base de Données (PostgreSQL)](#3-documentation-de-la-base-de-donnees-postgresql)
4. [Documentation Détaillée du Backend (OpenFaaS) & Fonctions](#4-documentation-detaillee-du-backend-openfaas--fonctions)
5. [Documentation Détaillée du Frontend (React 18 + Nginx)](#5-documentation-detaillee-du-frontend-react-18--nginx)
6. [Étapes de déploiement pas-à-pas](#6-etapes-de-deploiement-pas-a-pas)
7. [Commandes utiles pour le debug](#7-commandes-utiles-pour-le-debug)
8. [Checklist finale avant la soutenance](#8-checklist-finale-avant-la-soutenance)
9. [Variables de référence](#9-variables-de-reference)

---

## 1. ARCHITECTURE GLOBALE DE LA SOLUTION

Le projet COFRAP est déployé en architecture serverless sur Kubernetes K3S. Chaque fonction métier est encapsulée dans une image Docker indépendante et déployée via OpenFaaS Community. Le schéma ci-dessous présente les 4 couches de la solution :

```
               +-------------------------------------------------+
               |             Navigateur Client (React)           |
               +-------------------------------------------------+
                                       |
                                       | (HTTPS / HTTP)
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

### 1.1. Description des Couches de la Solution
* **Frontend (React 18 + Vite - Port 80)** : Interface dynamique mono-page (SPA). Elle gère les pages :
  * `/register` : Inscription sécurisée multi-étapes.
  * `/login` : Connexion par mot de passe serveur et double facteur.
  * `/renew` : Renouvellement forcé des identifiants (mot de passe ou TOTP expirés).
  * `/recover` : Récupération d'accès temporaire via code de secours à usage unique.
* **Backend Serverless (4 fonctions OpenFaaS sur le template `python3-http`)** :
  * `generate-password` : Crée l'utilisateur et génère un mot de passe fort de 24 caractères (transmis sous forme de texte et QR Code).
  * `generate-2fa` : Génère le secret TOTP, l'URI de configuration 2FA (QR Code) et 5 codes de secours chiffrés.
  * `authenticate` : Vérifie l'identité, valide le TOTP, calcule l'expiration (90 jours) et journalise la tentative de connexion.
  * `recover-with-backup-code` : Valide un code de secours non consommé, le marque utilisé, et réinitialise le compte avec un mot de passe temporaire fort.
* **Orchestration (Kubernetes K3S Single-Node)** : Exécution de toutes les charges de travail au sein d'une seule machine virtuelle. Helm gère l'installation d'OpenFaaS. Traefik assure l'accès externe. Les namespaces utilisés sont `cofrap`, `openfaas`, et `openfaas-fn`.
* **Persistance (PostgreSQL 16)** : Base de données relationnelle sécurisée stockant l'état des comptes, les codes de secours chiffrés et les tentatives de connexion.
* **Registre OCI (Docker Hub)** : Hébergement des 4 images backend (`TON_USERNAME/cofrap-generate-password`, `TON_USERNAME/cofrap-generate-2fa`, `TON_USERNAME/cofrap-authenticate`, `TON_USERNAME/cofrap-recover-with-backup-code`) et de l'image frontend (`TON_USERNAME/cofrap-frontend`).

---

## 2. PRÉREQUIS AVANT DE COMMENCER

| Prérequis | Vérification | Valeur attendue |
| :--- | :--- | :--- |
| **VM Ubuntu/Debian** | `lsb_release -a` | Ubuntu 20.04+ ou Debian 11+ |
| **Minimum 2 vCPUs** | `nproc` | 2 ou plus |
| **Minimum 4 Go RAM** | `free -h` | 4 Gi disponibles |
| **Minimum 20 Go disque** | `df -h /` | 20 Gi libres |
| **Accès Internet** | `curl https://get.k3s.io` | 200 OK |
| **Accès root ou sudo** | `whoami` | root ou sudo disponible |
| **Compte Docker Hub** | [hub.docker.com](https://hub.docker.com) | Créé et connexion locale validée |
| **Dépôt cloné** | `ls mspr-auth-serverless-dev-fin/` | Dossier du projet présent |
| **Python 3 installé** | `python3 --version` | Python 3.8+ |

> [!WARNING]
> Ne jamais committer le fichier [02-secrets.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/02-secrets.yaml) avec des valeurs réelles dans Git. Ce fichier contient la clé de chiffrement et la chaîne de connexion brute de la base de données.

---

## 3. DOCUMENTATION DE LA BASE DE DONNÉES (POSTGRESQL)

La persistance des données utilise un serveur PostgreSQL 16 déployé de manière isolée au sein du cluster Kubernetes. Le schéma d'initialisation SQL est déclaré dans [03-postgres-configmap.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/03-postgres-configmap.yaml).

### 3.1. Script d'Initialisation Complet (`init.sql`)
Ce script SQL s'exécute automatiquement lors du premier démarrage du StatefulSet PostgreSQL :
```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    mfa VARCHAR(100) DEFAULT '',
    gendate DATE NOT NULL,
    expired INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS backup_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(100) NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL
);
```

### 3.2. Dictionnaire des Tables & Contraintes

#### Table `users`
Contient l'état et les données d'authentification principaux de l'utilisateur.
* **`id`** (`SERIAL PRIMARY KEY`) : Clé primaire auto-incrémentée unique.
* **`username`** (`VARCHAR(100) NOT NULL UNIQUE`) : Nom de l'utilisateur. Un index unique empêche la création de doublons. Le format de l'identifiant est validé côté backend.
* **`password`** (`VARCHAR(255) NOT NULL`) : Mot de passe généré par le backend. Il est stocké chiffré symétriquement au format Fernet.
* **`mfa`** (`VARCHAR(100) DEFAULT ''`) : Clé secrète TOTP générée en Base32. Stockée chiffrée symétriquement pour protéger l'algorithme TOTP d'une fuite.
* **`gendate`** (`DATE NOT NULL`) : Date de génération du mot de passe actuel, mise à jour à chaque réinitialisation de mot de passe.
* **`expired`** (`INTEGER NOT NULL DEFAULT 0`) : Indicateur binaire d'expiration (0 = Actif, 1 = Expiré forcé).

#### Table `backup_codes`
Contient les codes de secours permettant de réinitialiser le compte en cas de perte du module TOTP.
* **`id`** (`SERIAL PRIMARY KEY`) : Clé primaire.
* **`user_id`** (`INTEGER REFERENCES users(id) ON DELETE CASCADE`) : Clé étrangère pointant vers `users.id` avec suppression automatique en cascade des codes si l'utilisateur est supprimé.
* **`code`** (`VARCHAR(100) NOT NULL`) : Code à 8 caractères en majuscules stocké chiffré symétriquement en Fernet.
* **`used`** (`BOOLEAN NOT NULL DEFAULT FALSE`) : Drapeau indiquant si le code a été consommé (`TRUE`) ou s'il est toujours valide (`FALSE`).

#### Table `login_attempts`
Historise l'ensemble des connexions pour la détection des attaques par force brute.
* **`id`** (`SERIAL PRIMARY KEY`) : Clé primaire.
* **`user_id`** (`INTEGER REFERENCES users(id) ON DELETE CASCADE`) : Clé étrangère pointant vers `users.id` avec suppression automatique en cascade.
* **`attempt_time`** (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`) : Horodatage automatique lors de l'insertion.
* **`success`** (`BOOLEAN NOT NULL`) : Indique si la tentative s'est soldée par un succès (`TRUE`) ou un échec (`FALSE`).

### 3.3. Mécanisme de Chiffrement Applicatif (Fernet)
Toutes les colonnes contenant des secrets (`users.password`, `users.mfa`, `backup_codes.code`) sont chiffrées avant l'insertion en base de données.
* **Algorithme** : **Fernet** (implémentation standardisée d'un chiffrement AES 128/256 bits en mode CBC avec authentification par HMAC-SHA256).
* **Gestion de la clé de chiffrement** : 
  La clé Fernet est lue depuis le fichier secret `/var/openfaas/secrets/encryption-key` fourni au runtime dans les pods OpenFaaS (monté depuis le cluster Kubernetes). En cas d'absence de ce secret, elle bascule sur la variable d'environnement par défaut `ENCRYPTION_KEY`.
* **Flux de chiffrement (Python)** :
  ```python
  from cryptography.fernet import Fernet
  cipher = Fernet(key)
  # Chiffrement avant insertion
  encrypted_data = cipher.encrypt(raw_text.encode()).decode()
  # Déchiffrement après lecture
  decrypted_data = cipher.decrypt(encrypted_data.encode()).decode()
  ```

---

## 4. DOCUMENTATION DÉTAILLÉE DU BACKEND (OPENFAAS) & FONCTIONS

Le backend de COFRAP est composé de **4 fonctions serverless** Python. Toutes ces fonctions partagent une configuration CORS standard permettant d'accepter les requêtes asynchrones en provenance du navigateur client.

### 4.1. generate-password
* **Fichier source** : [handler.py (generate-password)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/generate-password/handler.py)
* **Objectif** : Validation du nom d'utilisateur, création du compte et génération du mot de passe initial sous forme de QR Code.
* **Entrée (JSON POST)** :
  ```json
  {
    "username": "nom_utilisateur"
  }
  ```
* **Logique Métier et Algorithme** :
  1. Validation du format du nom d'utilisateur via expression régulière : `^[a-zA-Z0-9_.-]{8,20}$`. Si le nom d'utilisateur comporte moins de 8 caractères ou des caractères interdits, la fonction retourne immédiatement `{"error": "invalid_username_format"}` (HTTP 400).
  2. Connexion à la base de données PostgreSQL.
  3. Vérification de disponibilité de l'identifiant. Si un utilisateur possède déjà cet identifiant, retourne `{"error": "username_already_exists"}` (HTTP 400).
  4. Génération d'un mot de passe sécurisé et complexe de 24 caractères alphanumériques (comprenant majuscules, minuscules et chiffres) via l'utilisation de `random.choice`.
  5. Chiffrement du mot de passe via Fernet.
  6. Insertion d'une nouvelle ligne dans la table `users` contenant : `username`, `password` (chiffré), `mfa = ''` (vide), `gendate = DATE_DU_JOUR`, `expired = 0`.
  7. Génération d'un QR code contenant le mot de passe brut généré (en clair) à l'aide de la bibliothèque `qrcode`.
  8. Encodage en Base64 du flux binaire PNG du QR Code.
* **Sortie (HTTP 200)** :
  ```json
  {
    "qr_code": "iVBORw0KGgoAAAANSUhEUgAA..." // Image PNG encodée en Base64
  }
  ```
* **Exceptions et Erreurs** :
  * `400 Bad Request` : Corps JSON invalide, format d'identifiant invalide, ou utilisateur existant.
  * `500 Internal Server Error` : Erreur de connexion ou d'écriture en base de données.

### 4.2. generate-2fa
* **Fichier source** : [handler.py (generate-2fa)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/generate-2fa/handler.py)
* **Objectif** : Configurer le double facteur (TOTP) de l'utilisateur après confirmation de son mot de passe initial, et lui fournir ses codes de secours.
* **Entrée (JSON POST)** :
  ```json
  {
    "username": "nom_utilisateur",
    "password": "mot_de_passe_24_caracteres"
  }
  ```
* **Logique Métier et Algorithme** :
  1. Extraction de `username` et `password` du payload JSON.
  2. Recherche de l'utilisateur en base. Si introuvable, retourne `{"error": "User not found"}` (HTTP 404).
  3. Déchiffrement du mot de passe stocké en base de données via la clé Fernet. Comparaison logique avec le mot de passe fourni par l'utilisateur. S'ils diffèrent, retourne `{"error": "invalid_password"}` (HTTP 400).
  4. Génération d'une clé secrète TOTP aléatoire codée en Base32 (via `pyotp.random_base32()`).
  5. Construction de l'URI de provisionnement TOTP standardisée : `otpauth://totp/COFRAP:username?secret=SECRET&issuer=COFRAP`.
  6. Génération de 5 codes de secours uniques à 8 caractères composés uniquement de lettres majuscules et de chiffres.
  7. Chiffrement individuel des 5 codes de secours via Fernet.
  8. Suppression des anciens codes de secours de l'utilisateur (le cas échéant) pour éviter les doublons orphelins.
  9. Insertion des 5 nouveaux codes dans la table `backup_codes` avec le flag `used = FALSE`.
  10. Mise à jour de la table `users` en écrivant la clé secrète TOTP (Base32) dans la colonne `mfa`.
  11. Génération du QR Code de provisionnement TOTP (contenant l'URI) à l'aide de `qrcode`, et conversion en image PNG encodée en Base64.
* **Sortie (HTTP 200)** :
  ```json
  {
    "qr_code": "iVBORw0KGgoAAAANSUhEUgAA...", // QR Code de l'URI TOTP
    "backup_codes": ["X5Y9Z8W7", "A1B2C3D4", "E5F6G7H8", "I9J0K1L2", "M3N4O5P6"] // Codes en clair à sauvegarder
  }
  ```
* **Exceptions et Erreurs** :
  * `400 Bad Request` : Paramètres manquants ou mot de passe incorrect.
  * `404 Not Found` : Utilisateur non trouvé.
  * `500 Internal Server Error` : Problème technique base de données.

### 4.3. authenticate
* **Fichier source** : [handler.py (authenticate)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/authenticate/handler.py)
* **Objectif** : Validation de l'authentification globale (mot de passe + jeton TOTP) et gestion de l'expiration du compte.
* **Entrée (JSON POST)** :
  ```json
  {
    "username": "nom_utilisateur",
    "password": "mot_de_passe_24_caracteres",
    "totp_code": "123456"
  }
  ```
* **Logique Métier et Algorithme** :
  1. Recherche de l'utilisateur dans la table `users`. Si absent, retourne `{"error": "invalid_credentials"}` (HTTP 401).
  2. Déchiffrement et comparaison du mot de passe.
  3. Si le mot de passe est faux : insertion d'une ligne d'échec (`success = FALSE`) dans `login_attempts` pour historisation, validation de la transaction et retour immédiat de `{"error": "invalid_credentials"}` (HTTP 401).
  4. Calcul de l'âge du mot de passe :
     * Différence en jours entre la date courante et `users.gendate`.
     * Si la différence est supérieure à 90 jours ou si `users.expired = 1`, la fonction retourne immédiatement `{"error": "expired_password", "expired": true}` (HTTP 401). Le frontend interceptera ce code d'expiration pour rediriger l'utilisateur vers la page de renouvellement.
  5. Vérification de la clé secrète TOTP. Si `users.mfa` est vide, retourne `{"error": "mfa_not_configured"}` (HTTP 401).
  6. Vérification du jeton TOTP fourni :
     * Instanciation de l'objet TOTP de `pyotp` avec la clé secrète TOTP récupérée de la base et déchiffrée.
     * Appel à `totp.verify(totp_code)`.
     * Si le code TOTP est invalide ou expiré : insertion d'une ligne d'échec dans `login_attempts` et retour de `{"error": "invalid_totp"}` (HTTP 401).
  7. Si l'identifiant, le mot de passe, l'âge du mot de passe et le jeton TOTP sont valides :
     * Insertion d'une ligne de succès (`success = TRUE`) dans la table `login_attempts`.
     * Validation définitive et retour de réussite.
* **Sortie (HTTP 200)** :
  ```json
  {
    "status": "success",
    "message": "Authentification reussie"
  }
  ```
* **Exceptions et Erreurs** :
  * `400 Bad Request` : Paramètres JSON manquants.
  * `401 Unauthorized` : Erreurs d'identification, de mot de passe expiré, de TOTP invalide ou de double facteur non activé.
  * `500 Internal Server Error` : Problème technique base de données.

### 4.4. recover-with-backup-code
* **Fichier source** : [handler.py (recover-with-backup-code)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/recover-with-backup-code/handler.py)
* **Objectif** : Valider un code de secours inutilisé et réinitialiser le compte avec un mot de passe temporaire s'affichant en QR Code.
* **Entrée (JSON POST)** :
  ```json
  {
    "username": "nom_utilisateur",
    "backup_code": "X5Y9Z8W7"
  }
  ```
* **Logique Métier et Algorithme** :
  1. Recherche de l'utilisateur par son nom d'utilisateur. Si absent, retourne `{"error": "invalid_credentials"}` (HTTP 401).
  2. Extraction de l'ensemble des codes de secours associés à l'utilisateur où le flag `used` vaut `FALSE` (non consommés).
  3. Déchiffrement de chaque code extrait à l'aide de la clé Fernet.
  4. Comparaison insensible à la casse et sans espaces avec le code saisi par l'utilisateur (`backup_code`).
  5. Si aucun code ne correspond : retourne `{"error": "invalid_backup_code"}` (HTTP 401).
  6. Si un code de secours correspond :
     * Mise à jour de ce code de secours en base en passant le flag `used = TRUE` pour le rendre inutilisable à l'avenir.
     * Génération d'un nouveau mot de passe temporaire aléatoire de 12 caractères alphanumériques.
     * Chiffrement du mot de passe généré.
     * Mise à jour de l'enregistrement de l'utilisateur dans `users` : le mot de passe est mis à jour, `expired` est remis à `0`, et `gendate` est mis à jour à la date du jour.
     * Génération d'un QR Code contenant le nouveau mot de passe brut sous forme de texte, encodé en image PNG Base64.
* **Sortie (HTTP 200)** :
  ```json
  {
    "qr_code": "iVBORw0KGgoAAAANSUhEUgAA..." // QR code du nouveau mot de passe temporaire
  }
  ```
* **Exceptions et Erreurs** :
  * `400 Bad Request` : Paramètres manquants.
  * `401 Unauthorized` : Utilisateur non trouvé ou code de secours invalide/déjà consommé.
  * `500 Internal Server Error` : Problème technique base de données.

---

## 5. DOCUMENTATION DÉTAILLÉE DU FRONTEND (REACT 18 + NGINX)

L'interface utilisateur de COFRAP est développée sous forme de Single Page Application (SPA). Elle s'exécute directement dans le navigateur et dialogue de manière asynchrone avec la Gateway OpenFaaS.

### 5.1. Structure Générale
Le répertoire `/frontend` est composé des éléments essentiels suivants :
* [App.jsx](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/src/App.jsx) : Le composant principal de l'application. Il contient tous les styles globaux (orbes décoratives, fonds sombres), la configuration de routage et l'ensemble des écrans métiers.
* [nginx.conf](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/nginx.conf) : Fichier de configuration du serveur web Nginx qui distribue l'application compilée. Il intègre la directive indispensable `try_files` pour forcer le routage côté client.
* [Dockerfile](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/Dockerfile) : Fichier de build Docker multi-étapes compilant l'application via NodeJS et exportant les fichiers générés vers une image finale Nginx alpine ultra-légère.

### 5.2. Analyse Détaillée des Écrans et du State

#### A. Écran d'Inscription (`Register`)
Gère l'inscription séquentielle au moyen d'un formulaire composé de **4 étapes** contrôlées par la variable d'état locale `step` (de 1 à 4) :
1. **Étape 1 (Création du compte)** : L'utilisateur saisit son identifiant. L'application valide qu'il respecte les contraintes et appelle la fonction `/function/generate-password`. Si le compte est libre, le backend retourne le mot de passe sous forme de QR Code et la vue passe à la valeur `step = 2`.
2. **Étape 2 (Récupération du mot de passe)** : Affiche le code QR du mot de passe brut. L'utilisateur doit scanner le QR Code pour le décrypter et le coller dans la zone de texte pour valider sa sauvegarde. Après validation, l'application appelle la fonction `/function/generate-2fa` et passe à la valeur `step = 3`.
3. **Étape 3 (Configuration du double facteur)** : Affiche le QR Code de provisionnement TOTP généré par le serveur. L'utilisateur le scanne avec son application d'authentification (Google Authenticator, etc.) et sauvegarde ses codes de secours affichés. La vue passe à `step = 4`.
4. **Étape 4 (Validation TOTP)** : Saisie du code à 6 chiffres généré par l'application TOTP. Le frontend appelle la fonction d'authentification `/function/authenticate`. Si le jeton est validé, l'inscription est marquée réussie.

#### B. Écran de Connexion (`Login`)
L'utilisateur saisit son identifiant, son mot de passe brut de 24 caractères et son jeton TOTP à 6 chiffres.
* L'application appelle `/function/authenticate`.
* En cas de succès : Accès accordé.
* En cas d'erreur de mot de passe ou TOTP périmés : Affiche un message d'erreur rouge.
* En cas de retour d'erreur d'expiration du mot de passe (`expired_password` avec `expired: true`) : L'application redirige automatiquement l'utilisateur vers `/renew?username=nom_utilisateur` via `react-router-dom`.

#### C. Écran de Renouvellement (`Renew`)
Cet écran permet de régénérer de nouveaux identifiants après expiration (ou sur demande de modification).
* L'utilisateur saisit ou confirme son nom d'utilisateur.
* Lors de la validation, l'application effectue deux requêtes consécutives :
  1. Appel à `/function/generate-password` pour créer le nouveau mot de passe.
  2. Appel à `/function/generate-2fa` pour réinitialiser la clé de sécurité TOTP et les codes de secours.
* Affiche côte à côte le QR code du nouveau mot de passe et le QR code de la nouvelle configuration TOTP, ainsi que les nouveaux codes de secours.

#### D. Écran de Récupération (`Recover`)
Permet de regagner l'accès au compte en cas de perte de l'appareil 2FA.
* L'utilisateur saisit son nom d'utilisateur et l'un de ses 5 codes de secours à 8 caractères.
* Le frontend appelle la fonction backend `/function/recover-with-backup-code`.
* En cas de succès, le backend fournit le code QR d'un nouveau mot de passe temporaire à 12 caractères que l'utilisateur peut utiliser immédiatement pour se reconnecter.

### 5.3. Routage Nginx & Single Page Application (SPA)
Le routage de l'application s'effectue dans le navigateur client via `react-router-dom`. Si l'utilisateur actualise la page sur `/register` ou `/renew`, le navigateur effectue une requête HTTP directe vers le serveur Nginx.
Sans configuration spéciale, Nginx retournerait une erreur HTTP 404 car le fichier `/register` n'existe pas physiquement sur le disque. Le fichier [nginx.conf](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/nginx.conf) corrige cela en redirigeant toutes les requêtes introuvables vers le point d'entrée unique :
```nginx
location / {
    root /usr/share/nginx/html;
    index index.html index.htm;
    try_files $uri $uri/ /index.html;
}
```

---

## 6. ÉTAPES DE DÉPLOIEMENT PAS-À-PAS

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

### Étape 5 : Build, Push et Déploiement des 4 fonctions OpenFaaS
**Responsable : P2 — Responsable Backend Fonctions** | **Durée estimée : ~45 min**

#### 5.1 — Préparer Docker Hub et le template python3-http
```bash
docker login
faas-cli template pull https://github.com/openfaas/python-flask-template
```

#### 5.2 — Mettre à jour `stack.yaml` avec votre identifiant Docker Hub
Modifiez le fichier [stack.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/stack.yaml) pour l'adapter à votre registre et vos paramètres d'URL comme défini à la [section 5.2 du guide précédent](#52-mettre-a-jour-stackyml-avec-votre-identifiant-docker-hub).

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

* **Checkpoint 5** : `faas-cli list` retourne les 4 fonctions avec 1 réplique active chacune.

---

### Étape 6 : Déploiement de la frontend React
**Responsable : P4 — Responsable Frontend** | **Durée estimée : ~20 min**

#### 6.1 — Builder l'image frontend avec la bonne URL gateway
```bash
docker build \
  --build-arg VITE_GATEWAY_URL=http://IP_VM:NODE_PORT \
  -t TON_USERNAME/cofrap-frontend:latest \
  ./frontend

docker push TON_USERNAME/cofrap-frontend:latest
```

#### 6.2 — Appliquer les manifests frontend
Mettez à jour le manifest [07-frontend-deployment.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/07-frontend-deployment.yaml) avec votre identifiant d'image, puis déployez :
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

### Étape 7 : Tests end-to-end et validation
**Responsable : Toute l'équipe** | **Durée estimée : ~30 min**

Effectuez les scénarios de test complets détaillés ci-dessous :
1. **Inscription (`/register`)** $\rightarrow$ Génération réussie du mot de passe fort (QR) + configuration TOTP + codes de secours.
2. **Double Facteur (TOTP)** $\rightarrow$ Jeton valide généré par l'application mobile.
3. **Connexion (`/login`)** $\rightarrow$ Authentification réussie et redirection.
4. **Erreurs de sécurité** $\rightarrow$ Rejet des mauvais identifiants ou mauvais TOTP.
5. **Expiration** $\rightarrow$ Blocage au bout de 90 jours et redirection sur la page `/renew` pour forcer la reconfiguration.
6. **Récupération (`/recover`)** $\rightarrow$ Consommation d'un code de secours pour regénérer un mot de passe temporaire en QR Code.

---

## 7. COMMANDES UTILES POUR LE DEBUG

### 7.1. Diagnostics Généraux
```bash
# Vérifier l'état de l'ensemble des pods du cluster
kubectl get pods -A

# Inspecter la description d'un pod en erreur
kubectl describe pod NOM_DU_POD -n NOM_NAMESPACE
```

### 7.2. Logs en direct
```bash
# Logs des fonctions
kubectl logs -n openfaas-fn -l faas_function=authenticate

# Logs frontend et BDD
kubectl logs -n cofrap deployment/frontend -f
kubectl logs -n cofrap statefulset/postgres -f
```

---

## 8. CHECKLIST FINALE AVANT LA SOUTENANCE

* [ ] **Infrastructure** : K3S installé et node `Ready`. Helm v3 installé. `faas-cli` opérationnel.
* [ ] **OpenFaaS** : Gateway accessible en externe. `faas-cli login` réussi. `curl /healthz` répond OK.
* [ ] **Base de données** : `postgres-0` en statut Running 1/1. Tables SQL initialisées. Connexions acceptées.
* [ ] **Secrets** : Secret `encryption-key` créé dans OpenFaaS. Fichier [02-secrets.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/02-secrets.yaml) mis à jour dans le cluster.
* [ ] **Fonctions** : Les 4 images publiées sur Docker Hub. `faas-cli list` affiche les 4 fonctions comme actives.
* [ ] **Tests API** : `generate-password` retourne un QR code. `generate-2fa` fournit codes et QR. `authenticate` répond success.
* [ ] **Frontend** : Image construite avec `VITE_GATEWAY_URL` correct. Pods en statut Running. Accessible sur `http://IP_VM:8080`.
* [ ] **Tests E2E** : Validation des 4 scénarios d'inscriptions, connexion, expiration et récupération.

---

## 9. VARIABLES DE RÉFÉRENCE

Complétez ce tableau avec les valeurs réelles de votre déploiement pour la soutenance :

| Variable | Valeur de Déploiement |
| :--- | :--- |
| **IP du serveur (VM)** | *À compléter* : \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |
| **GATEWAY_URL** | `http://IP_VM:NODE_PORT` |
| **NODE_PORT OpenFaaS** | *À compléter* (via `kubectl -n openfaas get svc gateway-external`) |
| **Mot de passe OpenFaaS admin** | *À noter et conserver précieusement* |
| **Clé Fernet (ENCRYPTION_KEY)** | `Rt9LIv0sl8hVk_UjrxDB2QoACvrPoJmVVxuM5OdM5_o=` (Exemple) |
| **Identifiant Docker Hub** | *À compléter* : \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ |
| **URL Frontend de Production** | `http://IP_VM:8080` |
| **DATABASE_URL Interne** | `postgresql://cofrap:cofrap@postgres.cofrap.svc.cluster.local:5432/cofrap` |

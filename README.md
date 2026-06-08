# MSPR BLOC 2 — RNCP35584 | EPSI 2025/2026
## COFRAP — Plateforme d'Authentification Sécurisée

### Guide de Déploiement Complet
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
3. [Architecture de la Base de Données (PostgreSQL)](#3-architecture-de-la-base-de-donnees-postgresql)
4. [Spécifications Détaillées des Fonctions Backend (OpenFaaS)](#4-specifications-detaillees-des-fonctions-backend-openfaas)
5. [Logique et Constitution du Frontend (React)](#5-logique-et-constitution-du-frontend-react)
6. [Étapes de déploiement pas-à-pas](#6-etapes-de-deploiement-pas-a-pas)
   - [Étape 1 : Installation K3S (single-node)](#etape-1--installation-k3s-single-node)
   - [Étape 2 : Déploiement OpenFaaS via Helm](#etape-2--deploiement-openfaas-via-helm)
   - [Étape 3 : Déploiement PostgreSQL sur Kubernetes](#etape-3--deploiement-postgresql-sur-kubernetes)
   - [Étape 4 : Création des secrets OpenFaaS pour les fonctions](#etape-4--creation-des-secrets-openfaas-pour-les-fonctions)
   - [Étape 5 : Build, Push et Déploiement des 4 fonctions OpenFaaS](#etape-5--build-push-et-deploiement-des-4-fonctions-openfaas)
   - [Étape 6 : Déploiement de la frontend React](#etape-6--deploiement-de-la-frontend-react)
   - [Étape 7 : Tests end-to-end et validation](#etape-7--tests-end-to-end-et-validation)
7. [Commandes utiles pour le debug](#7-commandes-utiles-pour-le-debug)
8. [Checklist finale avant la soutenance](#8-checklist-finale-avant-la-soutenance)
9. [Variables de référence](#9-variables-de-reference)

---

## 1. ARCHITECTURE GLOBALE DE LA SOLUTION

Le projet COFRAP est déployé en architecture serverless sur Kubernetes K3S. Chaque fonction métier est encapsulée dans une image Docker indépendante et déployée via OpenFaaS Community. 

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

## 3. ARCHITECTURE DE LA BASE DE DONNÉES (POSTGRESQL)

La persistance des données utilise un serveur PostgreSQL 16 déployé de manière isolée au sein du cluster Kubernetes. Le schéma d'initialisation SQL est déclaré dans [03-postgres-configmap.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/03-postgres-configmap.yaml).

```mermaid
erDiagram
    USERS ||--o{ BACKUP_CODES : "possede"
    USERS ||--o{ LOGIN_ATTEMPTS : "historise"

    USERS {
        int id PK
        varchar username UK
        varchar password "Chiffré par Fernet"
        varchar mfa "Secret TOTP Chiffré"
        date gendate "Date de génération/renouvellement"
        int expired "0 = actif, 1 = expiré"
    }

    BACKUP_CODES {
        int id PK
        int user_id FK
        varchar code "Chiffré par Fernet"
        boolean used "Par défaut FALSE"
    }

    LOGIN_ATTEMPTS {
        int id PK
        int user_id FK
        timestamp attempt_time "DATE-HEURE courante"
        boolean success "Résultat de la tentative"
    }
```

### 3.1. Dictionnaire des Tables

#### Table `users`
* **`id`** (`SERIAL PRIMARY KEY`) : Clé primaire unique.
* **`username`** (`VARCHAR(100) NOT NULL UNIQUE`) : Nom de l'utilisateur (valide de 8 à 20 caractères alphanumériques).
* **`password`** (`VARCHAR(255) NOT NULL`) : Mot de passe de 24 caractères généré par le système, stocké chiffré symétriquement en AES (Fernet).
* **`mfa`** (`VARCHAR(100) DEFAULT ''`) : Clé secrète de configuration TOTP stockée chiffrée symétriquement.
* **`gendate`** (`DATE NOT NULL`) : Date de création/renouvellement du mot de passe.
* **`expired`** (`INTEGER NOT NULL DEFAULT 0`) : Indicateur d'expiration (0 = Actif, 1 = Expire).

#### Table `backup_codes`
* **`id`** (`SERIAL PRIMARY KEY`) : Clé primaire.
* **`user_id`** (`INTEGER REFERENCES users(id) ON DELETE CASCADE`) : Clé étrangère pointant vers l'utilisateur associé.
* **`code`** (`VARCHAR(100) NOT NULL`) : Code de secours à 8 caractères stocké chiffré symétriquement.
* **`used`** (`BOOLEAN NOT NULL DEFAULT FALSE`) : Drapeau d'utilisation (devient `TRUE` dès que le code est consommé).

#### Table `login_attempts`
* **`id`** (`SERIAL PRIMARY KEY`) : Identifiant unique de la tentative.
* **`user_id`** (`INTEGER REFERENCES users(id) ON DELETE CASCADE`) : Utilisateur concerné.
* **`attempt_time`** (`TIMESTAMP DEFAULT CURRENT_TIMESTAMP`) : Horodatage exact de l'authentification.
* **`success`** (`BOOLEAN NOT NULL`) : Indique si la tentative a réussi (`TRUE`) ou échoué (`FALSE`).

### 3.2. Mécanisme de Cryptographie (Fernet)
Toutes les données sensibles stockées en base de données (`password`, `mfa`, `code`) sont chiffrées au niveau applicatif.
* **Format** : Algorithme **Fernet** (chiffrement symétrique AES-128/256 en mode CBC authentifié par un HMAC SHA-256).
* **Gestion de la clé** : Les fonctions lisent la clé de chiffrement partagée depuis le fichier secret `/var/openfaas/secrets/encryption-key` fourni par OpenFaaS au runtime.

---

## 4. SPÉCIFICATIONS DÉTAILLÉES DES FONCTIONS BACKEND (OPENFAAS)

Toutes les fonctions sont configurées dans [stack.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/stack.yaml) et utilisent la signature d'événement standard de la passerelle `python3-http` d'OpenFaaS. Les requêtes s'exécutent en méthode `POST`.

### 4.1. generate-password
* **Fichier source** : [handler.py (generate-password)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/generate-password/handler.py)
* **Description** : Inscription d'un utilisateur et génération d'un mot de passe fort de 24 caractères.
* **Entrée (JSON)** :
  ```json
  { "username": "utilisateur_test" }
  ```
* **Traitement** :
  1. Validation regex du nom d'utilisateur (`^[a-zA-Z0-9_.-]{8,20}$`).
  2. Vérification de disponibilité en base de données.
  3. Génération d'une chaîne aléatoire de 24 caractères (lettres + chiffres).
  4. Chiffrement symétrique de la chaîne via Fernet.
  5. Insertion de l'utilisateur avec `expired = 0` et `gendate` à la date du jour.
  6. Génération du QR Code contenant le mot de passe brut, encodé en PNG Base64.
* **Sortie (HTTP 200)** :
  ```json
  { "qr_code": "iVBORw0KGgoAAAANSU..." }
  ```
* **Erreurs possibles** : `username_already_exists` (400), `invalid_username_format` (400), `Database error` (500).

### 4.2. generate-2fa
* **Fichier source** : [handler.py (generate-2fa)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/generate-2fa/handler.py)
* **Description** : Initialisation du module double facteur (MFA) pour un utilisateur existant.
* **Entrée (JSON)** :
  ```json
  {
    "username": "utilisateur_test",
    "password": "mot_de_passe_24_caracteres"
  }
  ```
* **Traitement** :
  1. Vérification du mot de passe fourni en le comparant avec le mot de passe stocké déchiffré.
  2. Génération d'un secret TOTP de provisionnement (Base32).
  3. Génération de 5 codes de secours uniques de 8 caractères alphanumériques.
  4. Chiffrement symétrique des codes de secours et stockage dans `backup_codes`.
  5. Stockage chiffré de la clé secrète TOTP dans `users.mfa`.
  6. Création du QR Code contenant l'URI de configuration TOTP (PNG Base64).
* **Sortie (HTTP 200)** :
  ```json
  {
    "qr_code": "iVBORw0KGgoAAAAN...",
    "backup_codes": ["X8Y7Z6W5", "A1B2C3D4", "E5F6G7H8", "I9J0K1L2", "M3N4O5P6"]
  }
  ```
* **Erreurs possibles** : `invalid_password` (400), `User not found` (404), `Database error` (500).

### 4.3. authenticate
* **Fichier source** : [handler.py (authenticate)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/authenticate/handler.py)
* **Description** : Authentification complète (Identifiants + TOTP) et gestion de l'expiration du compte.
* **Entrée (JSON)** :
  ```json
  {
    "username": "utilisateur_test",
    "password": "mot_de_passe_24_caracteres",
    "totp_code": "123456"
  }
  ```
* **Traitement** :
  1. Comparaison du mot de passe avec la version stockée déchiffrée. En cas d'échec, journalisation d'échec dans `login_attempts` et retour d'erreur.
  2. Calcul de l'âge du mot de passe via `users.gendate`. Si l'âge dépasse 90 jours ou `users.expired = 1`, retour de l'erreur `expired_password` avec redirection forcée du frontend.
  3. Récupération et déchiffrement du secret TOTP de l'utilisateur.
  4. Validation du code à 6 chiffres via la bibliothèque `pyotp`. En cas d'échec, journalisation d'échec et retour d'erreur.
  5. En cas de succès global, journalisation de succès dans `login_attempts`.
* **Sortie (HTTP 200)** :
  ```json
  { "status": "success", "message": "Authentification reussie" }
  ```
* **Erreurs possibles** : `invalid_credentials` (401), `expired_password` (401, avec indicateur `expired: true`), `mfa_not_configured` (401), `invalid_totp` (401), `Database error` (500).

### 4.4. recover-with-backup-code
* **Fichier source** : [handler.py (recover-with-backup-code)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/recover-with-backup-code/handler.py)
* **Description** : Récupération d'accès temporaire via code de secours à usage unique.
* **Entrée (JSON)** :
  ```json
  {
    "username": "utilisateur_test",
    "backup_code": "X8Y7Z6W5"
  }
  ```
* **Traitement** :
  1. Récupération de l'ensemble des codes de secours non consommés (`used = FALSE`) pour cet utilisateur.
  2. Déchiffrement et comparaison avec le code de secours saisi par l'utilisateur.
  3. Si correspondance, marquage du code de secours comme consommé (`used = TRUE`).
  4. Génération d'un nouveau mot de passe temporaire fort de 12 caractères alphanumériques.
  5. Chiffrement et mise à jour en base de données. Réinitialisation de `expired` à 0 et mise à jour de `gendate`.
  6. Génération et encodage du QR Code du nouveau mot de passe (PNG Base64).
* **Sortie (HTTP 200)** :
  ```json
  { "qr_code": "iVBORw0KGgoAAAANSU..." }
  ```
* **Erreurs possibles** : `invalid_credentials` (401), `invalid_backup_code` (401), `Database error` (500).

---

## 5. LOGIQUE ET CONSTITUTION DU FRONTEND (REACT)

L'interface utilisateur est développée en React (SPA) et gère l'état local du formulaire de manière réactive.

### 5.1. Fichiers sources clés
* [App.jsx](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/src/App.jsx) : Contient l'ensemble de la logique applicative (State, Helpers, Pages, Routes).
* [nginx.conf](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/nginx.conf) : Serveur web de production configuré pour rediriger toutes les routes inconnues vers `/index.html` via `try_files` afin de préserver le routage de la Single Page Application (SPA).
* [Dockerfile](file:///home/ubuntu/mspr-auth-serverless-dev-fin/frontend/Dockerfile) : Construction multi-étapes. Le build npm génère les assets statiques qui sont ensuite copiés et servis par l'image finale Nginx alpine.

### 5.2. Gestion du Routage et de l'URL Gateway
L'application utilise le routeur `react-router-dom` pour naviguer entre les écrans.
Pour effectuer les appels API vers OpenFaaS, le frontend utilise une fonction helper nommée `apiCall` qui concatène la variable d'environnement `VITE_GATEWAY_URL` lue au build avec l'endpoint souhaité (ex: `/function/authenticate`). Elle applique systématiquement les en-têtes JSON et transmet le corps de requête sérialisé.

---

## 6. ÉTAPES DE DÉPLOIEMENT PAS-À-PAS

### Étape 1 : Installation K3S (single-node)
**Responsable : P1 — Responsable Infrastructure** | **Durée estimée : ~30 min**

K3S est la distribution Kubernetes légère retenue. En mode single-node, la VM joue à la fois le rôle de control-plane et de worker — parfaitement adapté au PoC COFRAP.

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
# Attendu : 1 node Ready avec role control-plane,master
```

#### 1.3 — Installer Helm v3
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
# Attendu : version.BuildInfo{Version:"v3.x.x"...}
```

#### 1.4 — Installer faas-cli
```bash
curl -sL https://cli.openfaas.com | sudo sh
faas-cli version
# Attendu : CLI version: 0.x.x
```

* **Checkpoint 1** : `kubectl get nodes` → 1 node Ready. `helm version` OK. `faas-cli version` OK.

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
# Générer et noter le mot de passe (nécessaire pour faas-cli login)
PASSWORD=$(head -c 12 /dev/urandom | shasum | cut -d' ' -f1)
echo "Mot de passe OpenFaaS : $PASSWORD"

kubectl -n openfaas create secret generic basic-auth \
  --from-literal=basic-auth-user=admin \
  --from-literal=basic-auth-password=$PASSWORD
```
> [!IMPORTANT]
> Notez ce mot de passe maintenant. Il sera nécessaire à chaque connexion via `faas-cli login`.

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
# Ctrl+C quand gateway, nats, queue-worker, alertmanager, prometheus sont Running
```
> [!NOTE]
> Les pods autoscaler et dashboard peuvent rester en ContainerCreating — ils sont optionnels (OpenFaaS Enterprise). Le fonctionnement des fonctions n'en dépend pas.

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
# Attendu : OK
```

* **Checkpoint 2** : `curl $GATEWAY_URL/healthz` répond OK. `faas-cli login` réussi.

---

### Étape 3 : Déploiement PostgreSQL sur Kubernetes
**Responsable : P3 — Responsable Backend** | **Durée estimée : ~20 min**

PostgreSQL est déployé en StatefulSet Kubernetes dans le namespace `cofrap`, avec un volume persistant de 10 Go. Les manifests sont déjà dans le dossier `k8s/` du repo.

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
> [!NOTE]
> Avec `stringData` (et non `data`), Kubernetes encode automatiquement les valeurs en base64 au chargement. La clé Fernet doit donc être collée telle quelle en texte brut dans le manifest YAML.

#### 3.2 — Déployer PostgreSQL
```bash
# Déployer dans l'ordre
kubectl apply -f k8s/01-namespace.yaml
kubectl apply -f k8s/02-secrets.yaml
kubectl apply -f k8s/03-postgres-configmap.yaml
kubectl apply -f k8s/04-postgres-pvc.yaml
kubectl apply -f k8s/05-postgres-service.yaml
kubectl apply -f k8s/06-postgres-statefulset.yaml

# Attendre que PostgreSQL soit prêt
kubectl wait --for=condition=ready pod \
  -n cofrap -l app=postgres --timeout=300s

# Vérifier l'état du Pod
kubectl get pods -n cofrap
# Attendu : postgres-0   1/1   Running
```

#### 3.3 — Vérifier la connexion à la BDD et la création des tables
```bash
# Se connecter à PostgreSQL et vérifier la présence des tables
kubectl exec -it -n cofrap postgres-0 -- psql -U cofrap -d cofrap -c "\dt"
# Les tables (users, backup_codes, login_attempts) doivent être créées via le script SQL d'initialisation.
```

* **Checkpoint 3** : `postgres-0` en `Running 1/1`. Tables SQL créées et visibles via `psql`.

---

### Étape 4 : Création des secrets OpenFaaS pour les fonctions
**Responsable : P1 — Responsable Infrastructure** | **Durée estimée : ~15 min**

Les informations de sécurité et d'accès à la BDD sont transmises aux fonctions OpenFaaS de manière sécurisée en tant que secrets montés dans `/var/openfaas/secrets/`.

#### 4.1 — Créer le secret encryption-key
```bash
# Utiliser la clé Fernet générée à l'étape 3
faas-cli secret create encryption-key \
  --from-literal="$FERNET_KEY" \
  --gateway $GATEWAY_URL
```

#### 4.2 — Vérifier les secrets
```bash
faas-cli secret list --gateway $GATEWAY_URL
# Doit afficher : encryption-key
```

* **Checkpoint 4** : `faas-cli secret list` affiche `encryption-key`.

---

### Étape 5 : Build, Push et Déploiement des 4 fonctions OpenFaaS
**Responsable : P2 — Responsable Backend Fonctions** | **Durée estimée : ~45 min**

Chaque fonction est construite à partir du sous-dossier `functions/` et poussée sur Docker Hub. Le fichier `stack.yaml` orchestre tout le processus.

#### 5.1 — Préparer Docker Hub et le template python3-http
```bash
# Se connecter à votre compte Docker Hub
docker login

# Télécharger le template python3-http
faas-cli template pull https://github.com/openfaas/python-flask-template

# Vérifier que le template est disponible
ls template/
# Doit afficher le dossier : python3-http
```

#### 5.2 — Mettre à jour `stack.yaml` avec votre identifiant Docker Hub
Ouvrez le fichier [stack.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/stack.yaml) pour configurer les fonctions :
1. Utilisez le langage `python3-http`.
2. Remplacez le préfixe d'image par votre nom d'utilisateur Docker Hub (`TON_USERNAME/cofrap-`).
3. Supprimez les dépendances à des fichiers d'environnement secrets locaux non existants.

Vérifiez le contenu corrigé de [stack.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/stack.yaml) :
```yaml
version: 1.0
provider:
  name: openfaas
  gateway: http://51.210.104.236 # Ou l'adresse de votre gateway
  network: openfaas-fn

functions:
  generate-password:
    lang: python3-http
    handler: ./functions/generate-password
    image: TON_USERNAME/cofrap-generate-password:latest
    environment:
      DATABASE_URL: "postgresql://cofrap:cofrap@postgres.cofrap.svc.cluster.local:5432/cofrap"
    secrets:
      - encryption-key

  generate-2fa:
    lang: python3-http
    handler: ./functions/generate-2fa
    image: TON_USERNAME/cofrap-generate-2fa:latest
    environment:
      DATABASE_URL: "postgresql://cofrap:cofrap@postgres.cofrap.svc.cluster.local:5432/cofrap"
    secrets:
      - encryption-key

  authenticate:
    lang: python3-http
    handler: ./functions/authenticate
    image: TON_USERNAME/cofrap-authenticate:latest
    environment:
      DATABASE_URL: "postgresql://cofrap:cofrap@postgres.cofrap.svc.cluster.local:5432/cofrap"
    secrets:
      - encryption-key

  recover-with-backup-code:
    lang: python3-http
    handler: ./functions/recover-with-backup-code
    image: TON_USERNAME/cofrap-recover-with-backup-code:latest
    environment:
      DATABASE_URL: "postgresql://cofrap:cofrap@postgres.cofrap.svc.cluster.local:5432/cofrap"
    secrets:
      - encryption-key
```

#### 5.3 — Vérifier la structure des répertoires des fonctions
Chaque répertoire de fonction doit contenir le code du script `handler.py` et le fichier `requirements.txt`.
* [handler.py (generate-password)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/generate-password/handler.py)
* [handler.py (generate-2fa)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/generate-2fa/handler.py)
* [handler.py (authenticate)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/authenticate/handler.py)
* [handler.py (recover-with-backup-code)](file:///home/ubuntu/mspr-auth-serverless-dev-fin/functions/recover-with-backup-code/handler.py)

Chaque script implémente la signature d'appel suivante :
```python
def handle(event, context):
    # event.body   -> Contenu JSON désérialisé de la requête
    # event.method -> Méthode HTTP (POST, GET, OPTIONS)
    return {
        "statusCode": 200,
        "body": json.dumps({"result": "ok"})
    }
```

#### 5.4 — Vérifier les dépendances dans `requirements.txt`
Le fichier de dépendances de chaque fonction doit inclure les bibliothèques indispensables :
```
pyotp
qrcode[pil]
cryptography
psycopg2-binary
Pillow
```

#### 5.5 — Construire les images Docker des fonctions
```bash
faas-cli build -f stack.yaml

# Vérifier la création locale
docker images | grep cofrap
# Doit lister les 4 images associées aux fonctions
```

#### 5.6 — Pousser les images vers Docker Hub
```bash
faas-cli push -f stack.yaml
```

#### 5.7 — Déployer les fonctions sur OpenFaaS
```bash
faas-cli deploy -f stack.yaml --gateway $GATEWAY_URL

# Vérifier le statut d'activation
faas-cli list --gateway $GATEWAY_URL
# Attendu :
# Function                    Invocations  Replicas
# generate-password           0            1
# generate-2fa                0            1
# authenticate                0            1
# recover-with-backup-code    0            1

# Vérifier l'état des Pods dans le namespace OpenFaaS-fn
kubectl -n openfaas-fn get pods
```

#### 5.8 — Tester l'API avec des commandes curl
```bash
# Tester generate-password
curl -X POST $GATEWAY_URL/function/generate-password \
  -H 'Content-Type: application/json' \
  -d '{"username": "test.user.test"}'
# Attendu : {"qr_code": "iVBORw0KGgo..."}
```

* **Checkpoint 5** : Les 4 fonctions sont en statut Ready. Les tests API retournent des QR Codes en Base64.

---

### Étape 6 : Déploiement de la frontend React
**Responsable : P4 — Responsable Frontend** | **Durée estimée : ~20 min**

L'application frontend React doit être compilée avec la bonne URL de Gateway OpenFaaS et publiée dans le cluster.

#### 6.1 — Construire l'image Docker frontend
```bash
# Lancer le build avec la Gateway OpenFaaS en argument
docker build \
  --build-arg VITE_GATEWAY_URL=http://IP_VM:NODE_PORT \
  -t TON_USERNAME/cofrap-frontend:latest \
  ./frontend

# Pousser l'image compilée sur Docker Hub
docker push TON_USERNAME/cofrap-frontend:latest
```
> [!IMPORTANT]
> `VITE_GATEWAY_URL` doit correspondre à l'adresse externe accessible de la passerelle OpenFaaS.

#### 6.2 — Importer l'image dans le runtime K3s
Si vous effectuez le build en local sur le serveur sans passer par le Docker Hub public, chargez directement le conteneur dans le runtime Containerd de K3s :
```bash
docker save TON_USERNAME/cofrap-frontend:latest | sudo k3s ctr images import -
```

#### 6.3 — Mettre à jour l'image et appliquer les manifests
Mettez à jour le manifest [07-frontend-deployment.yaml](file:///home/ubuntu/mspr-auth-serverless-dev-fin/k8s/07-frontend-deployment.yaml) avec votre identifiant d'image, puis déployez :
```bash
kubectl apply -f k8s/07-frontend-deployment.yaml
kubectl apply -f k8s/08-frontend-service.yaml
kubectl apply -f k8s/09-frontend-ingress.yaml

# Forcer la mise à jour des Pods du déploiement frontend
kubectl rollout restart deployment frontend -n cofrap

# Vérifier
kubectl get pods -n cofrap
# Attendu : frontend-xxx 1/1 Running (2 répliques actives)
```

#### 6.4 — Accéder à l'application
Exposez le frontend publiquement sur le port 8080 :
```bash
kubectl port-forward -n cofrap svc/frontend 8080:80 --address 0.0.0.0 &
```
Vous pouvez maintenant ouvrir votre navigateur sur `http://IP_VM:8080`.

* **Checkpoint 6** : Le portail est accessible. Les requêtes partent bien vers les fonctions OpenFaaS.

---

### Étape 7 : Tests end-to-end et validation
**Responsable : Toute l'équipe** | **Durée estimée : ~30 min**

Valider les 4 scénarios complets avant la soutenance. Prendre des captures d'écran de chaque étape (obligatoires pour le dossier final).

| Scénario | Actions | Résultat attendu |
| :--- | :--- | :--- |
| **Création de compte** | Aller sur `/register` $\rightarrow$ Entrer l'identifiant (min 8 car.) $\rightarrow$ Soumettre. | Affiche le QR code du mot de passe initial, puis le QR de configuration TOTP et les 5 codes de secours. |
| **Configuration 2FA** | Scanner le QR TOTP avec Google Authenticator ou Authy. | L'application génère un jeton à 6 chiffres renouvelé toutes les 30 secondes. |
| **Connexion réussie** | Aller sur `/login` $\rightarrow$ Saisir l'identifiant, le mot de passe décrypté et le jeton TOTP valide. | Authentification validée avec succès. Accès accordé. |
| **Erreurs de mot de passe** | Entrer un mot de passe incorrect lors de la connexion. | Affiche l'erreur `invalid_credentials` (statut HTTP 401). |
| **Erreurs de TOTP** | Entrer un code TOTP invalide lors de la connexion. | Affiche l'erreur `invalid_totp` (statut HTTP 401). |
| **Expiration de mot de passe**| Tenter de se connecter avec un compte dont l'âge dépasse 90 jours (ou flag `expired = 1`). | Redirection automatique vers `/renew` (statut `expired_password`). |
| **Renouvellement** | Sur `/renew`, entrer l'identifiant et valider. | Les identifiants sont régénérés : nouveaux codes QR de mot de passe et de 2FA affichés. |
| **Code de secours** | Aller sur `/recover` $\rightarrow$ Entrer l'identifiant et un code de secours valide. | Le code est consommé, un nouveau mot de passe s'affiche sous forme de QR Code. |

#### Captures d'écran obligatoires pour le dossier final :
1. `kubectl get nodes` $\rightarrow$ Node principal en état `Ready`.
2. `kubectl -n openfaas get pods` $\rightarrow$ Tous les pods de la passerelle en état `Running`.
3. `faas-cli list` $\rightarrow$ Les 4 fonctions backend enregistrées et prêtes.
4. [hub.docker.com](https://hub.docker.com) $\rightarrow$ Les images chargées sur votre dépôt d'images public.
5. Page `/register` avec l'affichage des codes QR d'inscription.
6. Page `/login` avec la validation de réussite de connexion.
7. Page `/renew` lors d'une réinitialisation de mot de passe.
8. `kubectl get pods -n cofrap` $\rightarrow$ État d'exécution de la base et du frontend.

---

## 7. COMMANDES UTILES POUR LE DEBUG

### 7.1. Diagnostics Généraux du Cluster
```bash
# Vérifier l'état de l'ensemble des pods du cluster
kubectl get pods -A

# Inspecter la description détaillée d'un Pod en erreur
kubectl describe pod NOM_DU_POD -n NOM_NAMESPACE

# Visualiser les derniers événements système du cluster
kubectl get events --sort-by='.lastTimestamp' -A | tail -20
```

### 7.2. Logs en direct des Fonctions OpenFaaS
```bash
kubectl logs -n openfaas-fn -l faas_function=generate-password
kubectl logs -n openfaas-fn -l faas_function=generate-2fa
kubectl logs -n openfaas-fn -l faas_function=authenticate
kubectl logs -n openfaas-fn -l faas_function=recover-with-backup-code
```

### 7.3. Logs des Composants Applicatifs
```bash
# Consulter les requêtes reçues par les serveurs Nginx Frontend
kubectl logs -n cofrap deployment/frontend -f

# Diagnostiquer les transactions et accès sur PostgreSQL
kubectl logs -n cofrap statefulset/postgres -f
```

### 7.4. Déploiement Rapide après Modification de Code
```bash
# Compiler, pousser et déployer uniquement la fonction modifiée (ex: authenticate)
faas-cli up -f stack.yaml --filter authenticate --gateway $GATEWAY_URL
```

### 7.5. Problèmes Fréquents et Solutions

| Erreur / Comportement | Cause Probable | Solution |
| :--- | :--- | :--- |
| **Open .env.secrets: no such file** | Ligne `environment_file` restée présente dans `stack.yaml`. | Retirer les lignes `environment_file` et `- .env.secrets` du fichier `stack.yaml`. |
| **Template python3 not found** | Mauvaise désignation du template de base dans `stack.yaml`. | Utiliser `python3-http` après avoir lancé `faas-cli template pull`. |
| **localhost:8000 depuis le navigateur**| L'URL de passerelle n'a pas été injectée lors du build du frontend. | Recompiler le frontend avec l'argument `--build-arg VITE_GATEWAY_URL=http://IP_VM:NODE_PORT`. |
| **Pod frontend bloqué en 0/1** | Erreur de tirage d'image ou format d'image local incompatible. | Lancer `kubectl describe pod frontend-xxx -n cofrap` et inspecter les événements. |
| **Fonction HTTP 500** | Problème de connexion BDD ou secret d'encryption absent. | Vérifier la présence du secret : `faas-cli secret list`. Valider `DATABASE_URL` dans `stack.yaml`. |

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
* [ ] **Captures d'écran** : Les 8 captures d'écran obligatoires ont été stockées pour le dossier final Mission 8.
* [ ] **Dossier final** : Rapports des missions 1 à 8 complétés, annexes de code incluses.

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

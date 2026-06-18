# Guide des Commandes COFRAP

Ce fichier liste l'ensemble des commandes système, Docker, Kubernetes (K3s), OpenFaaS et PostgreSQL utilisées pour le développement, le déploiement et la maintenance de la plateforme COFRAP.

---

## 1. Kubernetes & K3s (Gestion de l'Infrastructure)

### Obtenir l'état général du cluster
```bash
# Lister tous les nœuds du cluster K3s
kubectl get nodes

# Lister tous les namespaces du cluster
kubectl get namespaces

# Lister tous les Ingress (routes d'accès externes) de tous les namespaces
kubectl get ingress -A
```

### Gestion des Pods et Services du projet (Namespace `cofrap`)
```bash
# Lister tous les pods du projet COFRAP
kubectl get pods -n cofrap

# Lister tous les services (DNS internes et ports) du projet COFRAP
kubectl get svc -n cofrap

# Consulter les logs en direct du frontend
kubectl logs -n cofrap deployment/frontend -f

# Consulter les logs en direct de PostgreSQL
kubectl logs -n cofrap statefulset/postgres -f
```

### Gestion des fonctions OpenFaaS (Namespace `openfaas-fn`)
```bash
# Lister les pods de fonctions OpenFaaS actives
kubectl get pods -n openfaas-fn

# Consulter les logs d'une fonction spécifique (ex: authenticate)
kubectl logs -n openfaas-fn -l faas_function=authenticate -f

# Consulter les logs de la fonction generate-password
kubectl logs -n openfaas-fn -l faas_function=generate-password -f

# Consulter les logs de la fonction generate-2fa
kubectl logs -n openfaas-fn -l faas_function=generate-2fa -f
```

### Déploiement et Redémarrage
```bash
# Appliquer tous les manifests Kubernetes de configuration
kubectl apply -f k8s/01-namespace.yaml
kubectl apply -f k8s/02-secrets.yaml
kubectl apply -f k8s/03-postgres-configmap.yaml
kubectl apply -f k8s/04-postgres-pvc.yaml
kubectl apply -f k8s/05-postgres-service.yaml
kubectl apply -f k8s/06-postgres-statefulset.yaml
kubectl apply -f k8s/07-frontend-deployment.yaml
kubectl apply -f k8s/08-frontend-service.yaml
kubectl apply -f k8s/09-frontend-ingress.yaml

# Redémarrer proprement le frontend suite à une mise à jour d'image
kubectl rollout restart deployment frontend -n cofrap

# Surveiller le statut du redémarrage
kubectl rollout status deployment frontend -n cofrap
```

---

## 2. Docker & Compilation Frontend

### Compilation locale et build d'image
```bash
# Compiler et builder l'image Docker du frontend (port 80 de production)
sudo docker build --build-arg VITE_GATEWAY_URL=http://51.210.104.236 -t lyndaalga/cofrap-frontend:v3 ./frontend

# Lister les images Docker disponibles en local
sudo docker images
```

### Importation d'une image Docker locale vers K3s (containerd)
*Note : K3s n'utilisant pas directement le démon Docker local, les images construites doivent être poussées sur Docker Hub OU importées directement dans le namespace d'exécution de Kubernetes (`k8s.io`).*
```bash
# Exporter l'image locale et l'importer dans le moteur de conteneur de K3s (containerd)
sudo docker save lyndaalga/cofrap-frontend:v3 | sudo k3s ctr -n k8s.io images import -

# Vérifier que l'image est bien présente dans containerd
sudo k3s ctr -n k8s.io images list | grep cofrap-frontend
```

---

## 3. OpenFaaS CLI (`faas-cli`)

### Connexion et initialisation
```bash
# Définir la variable de l'URL de la gateway OpenFaaS (Port NodePort 31112)
export GATEWAY_URL="http://51.210.104.236:31112"

# Se connecter à OpenFaaS en CLI (remplacer par votre mot de passe administrateur)
faas-cli login --username admin --password VOTRE_MOT_DE_PASSE --gateway $GATEWAY_URL

# Télécharger les templates de base de fonctions Python
faas-cli template pull https://github.com/openfaas/python-flask-template
```

### Gestion des Fonctions
```bash
# Builder les conteneurs des fonctions définies dans stack.yml
faas-cli build -f stack.yml

# Pousser les images des fonctions sur Docker Hub
faas-cli push -f stack.yml

# Déployer les fonctions sur le cluster OpenFaaS
faas-cli deploy -f stack.yml --gateway $GATEWAY_URL

# Lister les fonctions déployées et voir leur nombre d'appels / répliques
faas-cli list --gateway $GATEWAY_URL
```

### Secrets OpenFaaS
```bash
# Créer le secret de clé de chiffrement Fernet pour le backend
faas-cli secret create encryption-key --from-literal="VOTRE_CLE_FERNET" --gateway $GATEWAY_URL

# Lister les secrets OpenFaaS existants
faas-cli secret list --gateway $GATEWAY_URL
```

---

## 4. PostgreSQL (Base de données)

### Accéder au terminal SQL de la base de données
```bash
# Se connecter directement en psql interactif dans le pod Postgresql
kubectl exec -it -n cofrap postgres-0 -- psql -U cofrap -d cofrap
```

### Requêtes utiles d'administration (à exécuter dans psql)
```sql
-- Lister toutes les tables existantes
\dt

-- Consulter la liste complète des utilisateurs enregistrés
SELECT id, username, gendate, expired FROM users;

-- Forcer l'expiration du mot de passe d'un utilisateur de test (pour valider le parcours /renew)
UPDATE users SET expired = 1 WHERE username = 'demotest';

-- Changer manuellement la date de génération d'un mot de passe à plus de 6 mois
UPDATE users SET gendate = '2025-01-01' WHERE username = 'demotest';

-- Supprimer un utilisateur pour réinitialiser son inscription
DELETE FROM users WHERE username = 'demotest';

-- Quitter le terminal psql
\q
```

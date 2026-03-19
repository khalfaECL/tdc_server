# 🔐 Sovrizon V2 — Serveur Tiers de Confiance

Ce dépôt contient le code source du **serveur tiers de confiance** pour le projet **Sovrizon V2**, un système décentralisé de gestion et de partage sécurisé des données personnelles.

---

## 🎯 Objectif

Le tiers de confiance est un composant essentiel du système Sovrizon. Il est responsable de :

- 🔑 **Génération de clés de chiffrement** pour les images (AES-256-GCM)
- 💾 **Stockage sécurisé des clés** dans une base de données MongoDB
- 👤 **Gestion des utilisateurs** : inscription, connexion, authentification via tokens
- 🛡️ **Contrôle d'accès granulaire** : autorisation et révocation d'accès par utilisateur
- 🔄 **Chiffrement/Déchiffrement automatique** des images stockées
- 🎨 **Filigrane DCT** pour la traçabilité des images
- 📝 **Publication sécurisée de posts** avec autorisations conditionnelles

---

## 🧱 Technologies

| Catégorie | Technologies |
|---|---|
| **Backend** | Python, FastAPI |
| **Base de données** | MongoDB |
| **Sécurité** | AES-256-GCM (AEAD), JWT (24h), bcrypt, Filigrane DCT |
| **Traitement d'images** | OpenCV, NumPy |

---

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Marwanagr/Serveur-TDC.git
cd Serveur-TDC
```

### 2. Configuration de MongoDB

**Option A : MongoDB Atlas (Cloud) — Recommandé**

1. Créez un compte sur [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Créez un cluster gratuit
3. Copiez votre URI de connexion

**Option B : MongoDB Local**

Installation :

```bash
# Sur Windows
choco install mongodb

# Sur macOS
brew install mongodb-community

# Sur Linux (Ubuntu/Debian)
sudo apt-get install -y mongodb
```

Démarrer le service :

```bash
# Windows
mongod --dbpath "C:\data\db"

# macOS/Linux
mongod --dbpath /usr/local/var/mongodb
```

Créer un utilisateur (local) :

```bash
mongosh
use admin
db.createUser({ user: "admin", pwd: "password", roles: ["root"] })
```

### 3. Configuration du fichier `.env`

Créez un fichier `.env` à la racine du projet :

```env
# MongoDB Atlas (Cloud)
MONGO_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/tiers-de-confiance?retryWrites=true&w=majority"

# Ou MongoDB Local
# MONGO_URI="mongodb://admin:password@localhost:27017"

PORT=8300
```

### 4. Créer un environnement virtuel et lancer l'application

```bash
# Créer l'environnement virtuel
python -m venv venv

# Activer l'environnement
# Sur Windows :
.\venv\Scripts\activate
# Sur macOS/Linux :
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
uvicorn main:app --reload --port 8300
```

L'application sera accessible sur : **http://localhost:8300**  
Interface interactive : **http://localhost:8300/docs** (Swagger UI)

---

## 📁 Structure du projet

```
Serveur-TDC/
│
├── main.py                        # Point d'entrée FastAPI — enregistrement des routers
│
├── core/
│   ├── security.py                # Hash mdp, vérification token, récupération utilisateur
│   └── __init__.py
│
├── db/
│   ├── client.py                  # Connexion MongoDB
│   ├── collections.py             # Références aux collections (users, tokens, keys, posts)
│   └── __init__.py
│
├── routers/
│   ├── auth.py                    # Inscription, connexion, déconnexion
│   ├── posts.py                   # Ajout et lecture de posts chiffrés
│   ├── access.py                  # Autorisation et révocation d'accès par image
│   ├── watermark.py               # Application et extraction de filigrane DCT
│   └── __init__.py
│
├── services/
│   ├── crypto.py                  # Chiffrement / déchiffrement AES-256-GCM
│   ├── watermark_svc.py           # Logique de filigrane (DCT)
│   └── __init__.py
│
├── WatermarkingModule/
│   ├── engine.py                  # Moteur DCT d'encodage / décodage du filigrane
│   ├── utils.py                   # Utilitaires image pour le watermarking
│   └── __init__.py
│
├── .env                           # Variables d'environnement (non versionné)
├── requirements.txt               # Dépendances Python
└── venv/                          # Environnement virtuel (non versionné)
```

---
## 🔌 API — Endpoints
 
### 🔐 Authentification — `/auth`
 
| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Créer un compte utilisateur |
| `POST` | `/auth/login` | Se connecter et obtenir un token (24h) |
| `POST` | `/auth/logout` | Invalider un token |

---
### 📸 Posts — `/add_post`, `/posts/{image_id}`
 
| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/add_post` | Publier une image chiffrée |
| `POST` | `/posts/{image_id}` | Lire un post (déchiffré si autorisé) |

---

### 🛡️ Contrôle d'accès — `/authorize`, `/revoke`
 
| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/authorize/{image_id}` | Accorder l'accès à des utilisateurs |
| `DELETE` | `/revoke/{image_id}/{target_username}` | Révoquer l'accès d'un utilisateur |


---



### 🎨 Filigrane DCT — `/trust`
 
| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/trust/watermark` | Appliquer un filigrane DCT à une image |
| `POST` | `/trust/extract` | Extraire le filigrane d'une image |
 

## 👤 Auteur

**Marwan** — [@Marwanagr](https://github.com/Marwanagr)

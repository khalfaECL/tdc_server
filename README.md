# Secugram — Serveur Tiers de Confiance

Serveur backend de l'application **Secugram**, un système de partage d'images sécurisé de bout en bout. Ce composant est le **Tiers de Confiance (TDC)** : il gère le chiffrement AES-256-GCM des images, les clés par image, les autorisations d'accès granulaires, le filigrane DCT et l'historique des consultations.

---

## Fonctionnalités

- Inscription / connexion avec tokens d'authentification (24h)
- Chiffrement AES-256-GCM de chaque image à l'upload — la clé est stockée côté serveur, jamais exposée
- Contrôle d'accès par image : le propriétaire choisit qui peut déchiffrer
- Limite de vues par utilisateur + intervalle minimum entre deux consultations
- Filigrane DCT invisible : encode le username du viewer dans l'image déchiffrée
- Historique des accès (qui a vu quoi et quand)
- Système de demandes d'accès (un utilisateur peut demander l'autorisation au propriétaire)

---

## Stack

| Composant | Technologie |
|---|---|
| Framework | Python · FastAPI |
| Base de données | MongoDB Atlas |
| Chiffrement | AES-256-GCM (`cryptography`) |
| Authentification | Token hex 64 chars · bcrypt |
| Traitement image | OpenCV · NumPy · SciPy |
| Filigrane | DCT (Reed-Solomon) |
| Déploiement | Render (Web Service) |

---

## Structure du projet

```
Serveur-TDC/
├── main.py                  # Point d'entrée FastAPI — CORS + routers
│
├── core/
│   └── security.py          # Hash bcrypt, vérification token, get_user
│
├── db/
│   ├── client.py            # Connexion MongoDB (TLS + certifi)
│   └── collections.py       # Init des 6 collections + exports
│
├── routers/
│   ├── auth.py              # POST /auth/register, /auth/login, /auth/logout
│   ├── posts.py             # Upload, lecture, feed, mes photos, suppression
│   ├── access.py            # Autorisation, révocation, demandes d'accès
│   └── watermark.py         # POST /trust/watermark, /trust/extract
│
├── services/
│   ├── crypto.py            # encrypt_image / decrypt_image AES-256-GCM
│   └── watermark_svc.py     # Application du filigrane DCT
│
├── WatermarkingModule/
│   ├── engine.py            # Encodage / décodage DCT
│   └── utils.py             # Utilitaires image
│
├── requirements.txt
└── .env                     # Non versionné — voir section Configuration
```

### Collections MongoDB

| Collection | Contenu |
|---|---|
| `users` | Comptes (username, password bcrypt, user_id) |
| `tokens` | Tokens de session actifs |
| `posts` | Images chiffrées (blob AES) |
| `keys` | Clés AES par image + autorisations + paramètres |
| `requests` | Demandes d'accès en attente |
| `history` | Historique des consultations |

---

## API — Endpoints

### Authentification `/auth`

| Méthode | Endpoint | Corps | Description |
|---|---|---|---|
| `POST` | `/auth/register` | `{ username, password }` | Créer un compte |
| `POST` | `/auth/login` | `{ username, password }` | Connexion → retourne token 24h |
| `POST` | `/auth/logout` | `{ token }` | Invalider le token |

### Images `/posts`

| Méthode | Endpoint | Type | Description |
|---|---|---|---|
| `POST` | `/add_post` | `multipart/form-data` | Upload + chiffrement d'une image |
| `POST` | `/posts/{image_id}` | JSON | Lire une image (déchiffrée si autorisé) |
| `POST` | `/my_posts` | JSON | Lister ses propres images |
| `POST` | `/feed` | JSON | Feed global (toutes les images) |
| `DELETE` | `/delete_post/{image_id}` | JSON | Supprimer une image |

Champs `multipart` pour `/add_post` :

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `user_id` | string | oui | ID de l'utilisateur |
| `owner_username` | string | oui | Username du propriétaire |
| `token` | string | oui | Token de session |
| `image` | file | oui | Fichier image |
| `caption` | string | non | Description (défaut vide) |
| `authorized_users` | string | non | Usernames séparés par virgule |
| `ephemeral_duration` | int | non | Durée d'affichage en secondes (défaut 5) |
| `max_views` | int | non | Vues max par utilisateur (défaut 3) |
| `view_cooldown` | int | non | Intervalle min entre vues en minutes (défaut 10) |

### Accès `/access`

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/authorize/{image_id}` | Accorder l'accès à des utilisateurs |
| `DELETE` | `/revoke/{image_id}/{username}` | Révoquer l'accès |
| `POST` | `/add_request` | Envoyer une demande d'accès |
| `POST` | `/get_requests` | Lister les demandes reçues |
| `POST` | `/grant_request` | Accepter une demande |

### Filigrane `/trust`

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/trust/watermark` | Appliquer un filigrane DCT à une image |
| `POST` | `/trust/extract` | Extraire le filigrane d'une image |

---

## Déploiement sur Render (guide complet)

Ce guide permet à n'importe qui de déployer sa propre instance du serveur en ~15 minutes.

### Étape 1 — Créer un cluster MongoDB Atlas

1. Aller sur [mongodb.com/atlas](https://www.mongodb.com/atlas) et créer un compte gratuit
2. Créer un **nouveau projet**, puis un cluster **M0 (gratuit)**
3. Dans **Database Access** : créer un utilisateur avec un nom et un mot de passe — noter les deux
4. Dans **Network Access** : cliquer "Add IP Address" → choisir **Allow Access from Anywhere** (`0.0.0.0/0`) pour que Render puisse se connecter
5. Dans l'onglet **Clusters**, cliquer "Connect" → "Connect your application" → copier l'URI de connexion

L'URI ressemble à :
```
mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
```

Remplacer `<username>` et `<password>` par les identifiants créés à l'étape 3, et ajouter le nom de la base de données `tiers-de-confiance` :
```
mongodb+srv://monuser:monpassword@cluster0.xxxxx.mongodb.net/tiers-de-confiance?retryWrites=true&w=majority
```

### Étape 2 — Forker le dépôt

Forker ce dépôt sur votre compte GitHub :

```
https://github.com/khalfaECL/tdc_server
```

### Étape 3 — Créer le Web Service sur Render

1. Aller sur [render.com](https://render.com) et créer un compte gratuit
2. Tableau de bord → **New** → **Web Service**
3. Connecter votre compte GitHub et sélectionner le fork du dépôt
4. Configurer le service :

| Paramètre | Valeur |
|---|---|
| **Name** | `secugram-tdc` (ou ce que vous voulez) |
| **Region** | Frankfurt (EU) ou la plus proche |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free |

### Étape 4 — Ajouter les variables d'environnement

Dans l'onglet **Environment** du service Render, ajouter :

| Clé | Valeur |
|---|---|
| `MONGO_URI` | L'URI Atlas complète copiée à l'étape 1 |

Cliquer **Save Changes**.

### Étape 5 — Déployer

Cliquer **Create Web Service**. Render va :
1. Cloner le dépôt
2. Installer les dépendances (`pip install -r requirements.txt`)
3. Démarrer le serveur avec uvicorn

Au premier démarrage, les 6 collections MongoDB sont créées automatiquement.

L'URL du service sera de la forme :
```
https://secugram-tdc.onrender.com
```

Vérifier que le serveur fonctionne en ouvrant `https://<votre-service>.onrender.com/docs` — vous devez voir la documentation Swagger interactive.

> **Note Render Free Tier** : les instances gratuites se mettent en veille après 15 min d'inactivité. Le premier appel après une mise en veille peut prendre ~30 secondes. Pour un test sérieux, passer au plan Starter ($7/mois).

### Étape 6 — Configurer le client Secugram

Dans le repo frontend (`secugram-rn`), ouvrir `src/api/index.js` et mettre à jour l'URL de base :

```js
const API_BASE_URL = 'https://<votre-service>.onrender.com';
```

---

## Développement local

### Prérequis

- Python 3.11+
- Un cluster MongoDB Atlas (voir Étape 1) ou MongoDB installé localement

### Installation

```bash
git clone https://github.com/khalfaECL/tdc_server.git
cd tdc_server

python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Configuration

Créer un fichier `.env` à la racine :

```env
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/tiers-de-confiance?retryWrites=true&w=majority
```

Pour MongoDB local (sans Atlas) :

```env
MONGO_URI=mongodb://localhost:27017
```

### Lancer le serveur

```bash
uvicorn main:app --reload --port 8300
```

Serveur disponible sur `http://localhost:8300`
Documentation Swagger : `http://localhost:8300/docs`

---

## Auteurs

**Marwane Agrebi** — [@Marwanagr](https://github.com/Marwanagr)
**Malek Chammakhi**
**Amani Krid**
**Youssef Khalfa** — [@khalfaECL](https://github.com/khalfaECL)

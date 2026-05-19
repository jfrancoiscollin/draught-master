# PvP entre amis — Cadrage & implémentation

> **Statut** : J1+J2+J3+J4+J5 livrés sur `develop`. Backend complet
> (schema + REST défis + WebSocket avec auth, présence, push, state
> machine, grace period). Frontend live : lobby + écran de jeu actif +
> hook WS singleton. J6 à venir (toast global cross-écran, polish edge
> cases, tests E2E).

Permettre à deux utilisateurs Draught Master de jouer une partie en
temps réel sans passer par lidraughts, dans une logique "défi entre
amis" : pas de matchmaking public, pas de classement Elo, pas
d'horloge. L'asset distinctif reste l'analyse pédagogique post-partie
(dilf + heatmap + Gantt), qui s'enchaîne naturellement sur une partie
live finie via le flow `/api/pedagogy/analyze-game` existant.

---

## Scope v1 (≈ 6 jours)

✅ Défier un utilisateur par username
✅ Accepter / refuser / annuler un défi
✅ Jouer en temps réel via WebSocket (J2+)
✅ Abandon manuel
✅ Détection de fin de partie (mat / blocage) via le `game_engine` existant
✅ Persistance de la partie dans la table `games` → analysable comme une PDN importée

❌ **Pas d'horloge** — correspondance, pas de pression temporelle
❌ **Pas de matchmaking** ("partie au hasard")
❌ **Pas de spectateurs**, pas de chat
❌ **Pas d'offres de nulle** (le joueur peut abandonner ou la partie finit naturellement)
❌ **Pas de reconnexion sophistiquée** — coupure > 2 min = abandon
❌ **Pas de classement Elo**

Ces lignes ❌ sont des choix v1, pas des renoncements définitifs. Le
backlog post-v1 vit dans [ROADMAP.md](../ROADMAP.md) Tier "Live PvP".

---

## User flows

### 1. Défier un joueur

1. Alice ouvre l'onglet "Jouer en ligne"
2. Tape `bob` dans le champ "Défier un joueur"
3. Frontend appelle `POST /api/live/challenge { opponent_username: "bob", preferred_color: "random" }`
4. Backend valide (existence opposant, pas soi-même, pas de doublon en attente) et insère dans `live_challenges`
5. Bob (s'il est connecté au WS) reçoit un push `challenge_received`. Sinon, il le verra à sa prochaine connexion via `GET /api/live/challenges/pending`

### 2. Répondre à un défi

1. Bob voit "Alice te défie ⚔️ Accepter / Refuser"
2. `POST /api/live/challenge/{id}/respond { accept: true }`
3. Si accepté : le défi passe à `status='accepted'`, **un Game est créé** (J3), les deux clients sont redirigés vers l'écran de jeu live
4. Si refusé : `status='declined'`, fin

### 3. Annuler son propre défi

Alice peut retirer un défi tant qu'il est `pending` :
`POST /api/live/challenge/{id}/cancel` → `status='cancelled'`.

### 4. Jouer

(J3+) Plateau standard en mode "live" :
- Tour à tour, le client n'envoie un coup que si c'est son tour
- Validation serveur via `game_engine.apply_move`
- Broadcast WebSocket aux deux clients
- Fin détectée (plus de coups légaux) → `status='finished'` → bouton "Analyser cette partie" apparaît

---

## Data model

### Migrations sur `games` (J1)

```sql
ALTER TABLE games ADD COLUMN kind TEXT DEFAULT 'imported';   -- 'imported' | 'live'
ALTER TABLE games ADD COLUMN white_user_id INTEGER;
ALTER TABLE games ADD COLUMN black_user_id INTEGER;
ALTER TABLE games ADD COLUMN turn TEXT DEFAULT 'white';      -- side to move
```

Une partie live s'enregistre dans la table `games` existante avec
`kind='live'`. Le `pdn` s'incrémente coup après coup. `status` suit le
state machine décrit plus bas.

### Nouvelle table `live_challenges` (J1)

```sql
CREATE TABLE live_challenges (
  id TEXT PRIMARY KEY,                              -- token URL-safe ~96 bits
  challenger_id INTEGER NOT NULL,
  opponent_id   INTEGER NOT NULL,
  preferred_color TEXT NOT NULL DEFAULT 'random',   -- 'white' | 'black' | 'random'
  status TEXT NOT NULL DEFAULT 'pending',           -- voir cycle de vie ci-dessous
  created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at TEXT,                                 -- stamp à toute transition non-pending
  game_id TEXT,                                     -- set quand accepted, lie au Game
  FOREIGN KEY (challenger_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (opponent_id)   REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (game_id)       REFERENCES games(id) ON DELETE SET NULL
);
CREATE INDEX idx_live_challenges_opponent_status   ON live_challenges(opponent_id, status);
CREATE INDEX idx_live_challenges_challenger_status ON live_challenges(challenger_id, status);
```

#### Cycle de vie d'un challenge

```
                    ┌→ accepted   (opponent /respond accept=true → game créé)
pending ────────────┼→ declined   (opponent /respond accept=false)
                    ├→ cancelled  (challenger /cancel)
                    └→ expired    (TTL, job batch — pas en v1)
```

---

## API surface

### REST (J1, livré)

| Méthode | Route | Auth | Body | Réponse |
|---|---|---|---|---|
| `POST` | `/api/live/challenge` | required | `{opponent_username, preferred_color?}` | `ChallengeOut` |
| `GET`  | `/api/live/challenges/pending` | required | — | `{received: [...], sent: [...]}` |
| `POST` | `/api/live/challenge/{id}/respond` | required (opponent only) | `{accept: bool}` | `ChallengeOut` |
| `POST` | `/api/live/challenge/{id}/cancel`  | required (challenger only) | — | `ChallengeOut` |

#### Codes d'erreur

| Code | Cas |
|---|---|
| 404 | Opposant introuvable, ou défi inexistant, ou utilisateur non autorisé à voir ce défi (on renvoie 404 plutôt que 403 pour ne pas leak l'existence) |
| 409 | Défi déjà résolu ; ou doublon "pending" entre les deux mêmes joueurs |
| 422 | Tentative de se défier soi-même |

### WebSocket (J2, livré ; J3+ enrichit)

**Endpoint unique** : `WS /api/live/ws`

Cycle de vie :

1. Client se connecte → serveur accepte
2. Client envoie `{type: 'auth', token}` dans les 10s (sinon socket fermé)
3. Serveur valide via `_decode_token` (même JWT que le REST) → enregistre dans `presence.manager`
4. **Single-connection-per-user** : si une autre socket existait pour ce `user_id`, elle reçoit `{type: 'kicked_by_other_session'}` puis est fermée
5. Serveur envoie `{type: 'auth_ok', user_id}`
6. Boucle de messages

**Messages client → serveur** (J2) :
| Type | Effet |
|---|---|
| `ping` | Serveur répond `pong` |
| *(tout autre)* | Serveur répond `{type:'error', reason:'unknown type ...'}` — la connexion reste ouverte (forward-compat) |

**Messages client → serveur** (J3, livré) :
| Type | Body | Effet |
|---|---|---|
| `move` | `{move: "32-28"}` | Validation côté serveur via `game_engine.get_legal_moves`. Erreurs taxonomiques : `not_in_game`, `game_over`, `not_your_turn`, `unknown_move`. Sur succès, broadcast `move_played` aux deux joueurs + auto-détection mat/blocage qui chaîne un `game_ended` |
| `resign` | `{}` | Marque le côté envoyeur `abandoned_<color>`, l'adversaire gagne. Broadcast `game_ended` aux deux |

**Messages serveur → client** :
| Type | Émis quand |
|---|---|
| `auth_ok` | Auth réussie |
| `auth_error` | Auth échouée (token invalide / expiré / absent / frame malformée). Socket fermé après |
| `pong` | Réponse au `ping` |
| `kicked_by_other_session` | Une autre socket vient de prendre la place |
| `error` | Frame inconnu / non-objet / coup invalide — log only, connexion préservée. ``reason`` est un slug stable (`not_in_game` / `not_your_turn` / `game_over` / `unknown_move`) |
| `challenge_received` | Quelqu'un t'a défié (push REST → WS) |
| `challenge_resolved` | Ton défi vient d'être accepté ou refusé |
| `challenge_cancelled` | Le challenger a retiré son défi |
| `game_started` | Une partie live vient d'être créée pour toi (acceptation d'un défi) |
| `move_played` | L'un des deux joueurs vient de jouer un coup (côté + notation + nouvelle session) |
| `game_ended` | Partie terminée (mat / blocage / abandon / forfait grace expirée — voir `by_forfeit:bool`). Le client peut maintenant proposer "Analyser la partie" |
| `opponent_disconnected` | (J4) L'adversaire vient de couper sa WS. `grace_seconds` indique le temps restant avant forfait auto |
| `opponent_reconnected` | (J4) L'adversaire est revenu avant la fin du grace, partie continue |
| `game_state` | (J4) Bootstrap envoyé au joueur juste après `auth_ok` quand il a une partie active — laisse le frontend reprendre sans polling |

Toutes les pushs (`challenge_received` / `_resolved` / `_cancelled`) sont **best-effort** : si l'utilisateur cible n'est pas connecté, le push est silencieusement abandonné. La récupération se fait par `GET /api/live/challenges/pending` à la reconnexion.

#### Présence in-memory

Le singleton `presence.manager` (à `backend/live/presence.py`) tient `Dict[user_id, WebSocket]` derrière un `asyncio.Lock`. Cohérent avec le scope v1 "process unique sur Railway" — un redéploiement vide la map et toutes les connexions sont coupées (les clients se reconnectent automatiquement). Pas de Redis en v1.

---

## State machine d'une partie live (J3+)

```
created  (challenge accepted, Game inséré avec status='pending')
   └─→ in_progress           (premier coup joué OU les 2 clients connectés au WS de la partie)
         ├─→ finished            (mat ou blocage détecté par game_engine)
         ├─→ abandoned_white     (white resigned, OR white disconnected > 2 min)
         ├─→ abandoned_black     (black resigned, OR black disconnected > 2 min)
         └─→ abandoned_server    (serveur redémarré pendant la partie — voir Risques)
```

---

## Edge cases v1

| Scénario | Comportement |
|---|---|
| Opposant coupe sa connexion | 2 min grace period, puis `abandoned_<color>` (gain pour l'autre) |
| Serveur redémarre | Toutes parties en cours → `abandoned_server`. Message clair côté client. |
| Joueur tente de bouger hors-tour | Coup rejeté avec message "Pas ton tour" |
| Coup illégal envoyé | Rejeté (le `game_engine` retourne déjà la raison) |
| 2 clients du même user (mobile + desktop) | Le second remplace le premier — un seul WS par user_id à la fois |
| Username inexistant à la création | 404 immédiat, pas de bruit DB |
| Spam de défis | Bloqué côté API : 1 seul "pending" par paire (challenger, opponent). 409 sur doublon |

---

## UI à venir (J5)

| Composant | Rôle |
|---|---|
| `<LivePlayPanel>` | Onglet principal — champ "Défier un joueur" (autocomplete sur username), liste "Défis reçus" (badge rouge si non-lu), liste "Parties en cours" |
| `<LiveGameScreen>` | Adaptation de `ImportGamePanel` : plateau actif, bandeau "À toi de jouer" / "Tour de l'adversaire", bouton "Abandonner", une fois finie bouton "Analyser la partie" qui réutilise le flow pédagogique existant |
| `<ChallengeToast>` | Toast/badge global "Alice te défie", écouté sur le WS depuis n'importe quel écran de l'app |

---

## Coût opérationnel

- **RAM serveur** : ~1-2 KB par connexion WS active. Négligeable < 1000 simultanées
- **Railway** : pas de coût additionnel (free tier tient)
- **Maintenance** : surveiller les fuites de WS (déconnexions mal nettoyées), logs ciblés à prévoir

---

## Risques

1. **State in-memory** — chaque redéploiement Railway tue les parties en cours. V1 : message clair à l'utilisateur. V2 : Redis pour la session live
2. **Triche par moteur** — un joueur peut faire tourner Scan en parallèle dans un autre onglet. Pas adressé en v1 (entre amis, on suppose la confiance). Si problème : rate-limit coups + timing analysis
3. **Charge réseau mobile** — WS persistante consomme la batterie. Ping/pong toutes les 30s, pas plus

---

## Plan d'implémentation

| Jour | Livrable | Statut |
|---|---|---|
| **J1** | Schema migrations + endpoints REST de défis + tests | ✅ livré |
| **J2** | WebSocket endpoint, présence (dict in-mem), auth via token, ping/pong + push REST→WS sur les 3 transitions de challenge | ✅ livré |
| **J3** | State machine de partie (LiveGameManager singleton), move/resign WS frames, broadcast move_played + game_ended, persistance incrémentale dans games.pdn | ✅ livré |
| **J4** | 2-min grace period sur déconnexion, reconnect-cancels-forfeit, push opponent_disconnected / opponent_reconnected, game_state bootstrap au auth_ok, startup-hook abandoned_server | ✅ livré |
| **J5** | UI lobby (`<LivePlayPanel>`) + écran de jeu actif (`<LiveGameScreen>`) + hook WS singleton (`useLiveWS`) + nouvel onglet 'live' dans App.tsx | ✅ livré |
| **J4** | Détection fin de partie (mat/blocage), grace period déconnexion, abandon explicite | ⏳ à venir |
| **J5** | UI : `<LivePlayPanel>` (lobby/défis) + `<LiveGameScreen>` (jeu live) | ⏳ à venir |
| **J6** | `<ChallengeToast>` global, edge cases, intégration avec le flow pédagogique pour analyser une partie finie. Tests E2E | ⏳ à venir |

---

## Liens

- [ROADMAP.md](../ROADMAP.md) — vue d'ensemble des tiers
- [CHANGELOG.md](../CHANGELOG.md) — entries datés J1+
- [PEDAGOGY_WEAKNESSES.md](./PEDAGOGY_WEAKNESSES.md) — flow d'analyse post-partie qu'on enchaîne

import markdown, re, json, urllib.request, urllib.error
from models import db, Message, Chat, SiteSetting

class AIEngine:
    def __init__(self, app):
        self.app = app

    def get_setting(self, key, default=''):
        setting = SiteSetting.query.filter_by(key=key).first()
        return setting.value if setting else default

    def get_provider(self):
        return self.get_setting('ai_provider', 'offline')

    def get_system_prompt(self):
        default = (
            "Tu es un assistant IA généraliste qui répond à toutes les questions. "
            "Tu aides sur tous les sujets : programmation, sciences, culture, conseils, rédaction, mathématiques, etc. "
            "Tu réponds en français de façon claire, précise et utile. "
            "Pour les questions de code, tu utilises des blocs markdown avec le langage spécifié."
        )
        return self.get_setting('system_prompt', default)

    def build_context(self, chat_id):
        messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at).all()
        context = [{"role": "system", "content": self.get_system_prompt()}]
        for m in messages:
            context.append({"role": m.role, "content": m.content})
        return context

    def generate_response(self, chat_id, user_message):
        msg = Message(chat_id=chat_id, role='user', content=user_message)
        db.session.add(msg)
        db.session.commit()

        provider = self.get_provider()
        ai_content = None

        if provider == 'openai':
            ai_content = self._call_openai(chat_id, user_message)
        elif provider == 'gemini':
            ai_content = self._call_gemini(chat_id, user_message)

        if not ai_content:
            ai_content = self._offline_response(user_message)

        ai_msg = Message(chat_id=chat_id, role='assistant', content=ai_content)
        db.session.add(ai_msg)
        db.session.commit()

        chat = Chat.query.get(chat_id)
        if chat and chat.messages.count() <= 2:
            chat.title = self._generate_title(user_message)
            db.session.commit()

        return ai_content

    def _generate_title(self, message):
        words = message.split()[:8]
        title = ' '.join(words)
        return (title[:80] + '...') if len(title) > 80 else title

    def _call_openai(self, chat_id, user_message):
        try:
            from openai import OpenAI
            key = self.get_setting('openai_api_key', '')
            if not key:
                return None
            client = OpenAI(api_key=key)
            model = self.get_setting('openai_model', 'gpt-4o-mini')
            context = self.build_context(chat_id)
            resp = client.chat.completions.create(
                model=model, messages=context,
                temperature=0.7, max_tokens=4096
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"OpenAI error: {e}")
            return None

    def _call_gemini(self, chat_id, user_message):
        key = self.get_setting('gemini_api_key', '')
        if not key:
            return None
        model = self.get_setting('gemini_model', 'gemini-2.0-flash')

        context = self.build_context(chat_id)
        system_prompt = self.get_system_prompt()

        history = []
        for c in context[1:]:
            role = "user" if c["role"] == "user" else "model"
            history.append({"role": role, "parts": [{"text": c["content"]}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = {
            "contents": history,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
            }
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                texts = [p.get("text", "") for p in parts]
                return "\n".join(texts)
        except Exception:
            return None
        return None

    def _offline_response(self, message):
        msg = message.lower().strip()

        greetings = r'^(bonjour|salut|hey|coucou|hello|hi|yo|bjr|slt|cc)'
        if re.match(greetings, msg):
            return "Salut ! Comment tu vas ? Je peux t'aider avec quelque chose ?"

        if re.search(r'(qui.*(toi|tu)|présente.*toi|c\'est qui)', msg):
            return "Je suis un assistant IA. Dis-moi ce dont tu as besoin, je suis là pour t'aider !"

        if re.search(r'(merci|thanks|thx|merci beaucoup)', msg):
            return "De rien ! N'hésite pas si tu as d'autres questions, je suis là pour t'aider. 😊"

        if re.search(r'(explique|c\'est quoi|qu\'est-ce que|défini|definition|signifie)', msg):
            return self._handle_explain(msg)

        if re.search(r'(exemple|montre|donne.*exemple|illustre)', msg):
            return self._handle_example(msg)

        if re.search(r'(python|flask|django|pandas|numpy)', msg):
            return self._handle_python(msg)
        elif re.search(r'(javascript|js|typescript|ts|react|node|vue|angular)', msg):
            return self._handle_javascript(msg)
        elif re.search(r'(html|css|site|page web|frontend)', msg):
            return self._handle_html_css(msg)
        elif re.search(r'(sql|base de donn|database|mysql|postgres|mongo)', msg):
            return self._handle_sql(msg)
        elif re.search(r'(git|github|versioning|commit|push|pull)', msg):
            return self._handle_git(msg)
        elif re.search(r'(api|rest|endpoint|route)', msg):
            return self._handle_api(msg)
        elif re.search(r'(erreur|bug|debug|ne marche|probleme|pas fonctionne)', msg):
            return self._handle_debug(msg)
        elif re.search(r'(algorithme|complexité|tri|recherche|structure)', msg):
            return self._handle_algo(msg)
        elif re.search(r'(docker|conteneur|container|deploy|déploiement)', msg):
            return self._handle_docker(msg)
        elif re.search(r'(linux|bash|terminal|commande|shell)', msg):
            return self._handle_linux(msg)
        elif re.search(r'(math|calcul|équation|equation|probabilité|statistique|algèbre|géom.)', msg):
            return self._handle_math(msg)
        elif re.search(r'(français|anglais|langue|traduit|grammaire|orthographe)', msg):
            return self._handle_language(msg)
        elif re.search(r'(histoire|historique|guerre|roi|révolution|époque|siècle)', msg):
            return self._handle_history(msg)
        elif re.search(r'(santé|maladie|symptôme|traitement|médicament|virus|bactérie)', msg):
            return self._handle_health(msg)
        elif re.search(r'(conseil|astuce|comment|pourquoi|meilleur|solution)', msg):
            return self._handle_advice(msg)
        elif re.search(r'(jeu|jeux|jouer|gaming|video|console)', msg):
            return self._handle_gaming(msg)
        elif re.search(r'(musique|music|chanson|chant|instrument|guitare|piano)', msg):
            return self._handle_music(msg)
        elif re.search(r'(voyage|voyager|visiter|pays|ville|tourisme)', msg):
            return self._handle_travel(msg)
        elif re.search(r'(nourriture|cuisine|recette|manger|plat|ingrédient)', msg):
            return self._handle_food(msg)
        elif re.search(r'(sport|entraînement|fitness|musculation|courir|velo)', msg):
            return self._handle_sport(msg)
        elif re.search(r'(économie|finance|argent|investir|bourse|crypto|budget)', msg):
            return self._handle_finance(msg)
        elif re.search(r'(philosophie|philo|sens|vie|existence|réflexion)', msg):
            return self._handle_philosophy(msg)
        elif re.search(r'(ia|intelligence artificielle|machine learning|deep learning|ai)', msg):
            return self._handle_ai(msg)
        elif re.search(r'(réseau|reseau|wifi|internet|tcp|ip|protocol|sécurité)', msg):
            return self._handle_networking(msg)

        return self._handle_general(message)

    def _handle_explain(self, msg):
        if 'variable' in msg:
            return (("**Variable en programmation**\n\n"
                "Une variable est un conteneur qui stocke une valeur en mémoire.\n\n"
                "```python\nnom = \"Alice\"\nage = 25\nprix = 19.99\n```\n\n"
                "```javascript\nlet nom = 'Alice';\nconst AGE = 25;\n```\n\n"
                "**Conseil :** Utilise des noms explicites."))
        if 'fonction' in msg:
            return (("**Fonction en programmation**\n\n"
                "Une fonction est un bloc de code réutilisable.\n\n"
                "```python\ndef calculer_moyenne(nombres):\n    if not nombres:\n        return 0\n    return sum(nombres) / len(nombres)\n```\n\n"
                "**Règle :** Une fonction = une responsabilité"))
        if ('classe' in msg or 'objet' in msg or 'poo' in msg or 'orienté' in msg):
            return (("**POO - Programmation Orientée Objet**\n\n"
                "Organise le code autour d'objets (données + méthodes).\n\n"
                "```python\nclass Utilisateur:\n    def __init__(self, nom):\n        self.nom = nom\n    def saluer(self):\n        return f\"Bonjour {self.nom}\"\n```\n\n"
                "**Principes :** Encapsulation, Héritage, Polymorphisme"))
        if 'api' in msg or 'rest' in msg:
            return (("**API REST**\n\n"
                "Expose des ressources via HTTP :\n\n"
                "| Méthode | Action |\n| GET | Lire |\n| POST | Créer |\n| PUT | Mettre à jour |\n| DELETE | Supprimer |\n\n"
                "```python\n@app.route('/api/users')\ndef get_users():\n    return jsonify(users)\n```"))
        if 'atome' in msg or 'molécule' in msg or 'chimie' in msg or 'proton' in msg:
            return (("**Notions de chimie**\n\n"
                "Un **atome** est la plus petite unité de la matière.\n"
                "- **Proton** : charge positive (dans le noyau)\n"
                "- **Neutron** : charge neutre (dans le noyau)\n"
                "- **Électron** : charge négative (autour du noyau)\n\n"
                "Une **molécule** est un ensemble d'atomes liés entre eux.\n"
                "Exemple : H₂O (eau) = 2 hydrogènes + 1 oxygène"))
        if 'photosynthèse' in msg or 'chlorophylle' in msg:
            return (("**Photosynthèse**\n\n"
                "Processus par lequel les plantes convertissent la lumière en énergie.\n\n"
                "**Équation :**\n"
                "6 CO₂ + 6 H₂O → C₆H₁₂O₆ + 6 O₂\n\n"
                "**Étapes :**\n"
                "1. Capture de la lumière par la chlorophylle\n"
                "2. Conversion en énergie chimique (ATP)\n"
                "3. Fabrication de glucose\n"
                "4. Libération d'oxygène"))
        if 'capital' in msg or 'pays' in msg:
            return (("Je peux te parler de la géographie des pays. "
                "Précise le nom du pays qui t'intéresse et je te dirai sa capitale, sa population, et d'autres informations."))
        return (
            "Je peux t'expliquer des concepts dans **tous les domaines** :\n\n"
            "- **Programmation** : variables, fonctions, classes, API...\n"
            "- **Sciences** : physique, chimie, biologie, mathématiques...\n"
            "- **Culture** : histoire, géographie, langues...\n"
            "- **Technologie** : IA, réseaux, sécurité...\n\n"
            "De quoi veux-tu une explication ?"
        )

    def _handle_example(self, msg):
        if 'python' in msg:
            return ("**Exemples Python**\n\n"
                "```python\n# Lire un fichier CSV\nimport csv\nwith open('data.csv', 'r') as f:\n    for row in csv.DictReader(f):\n        print(row)\n\n# Requête HTTP\nimport requests\nresp = requests.get('https://api.example.com/data')\ndata = resp.json()\n```")
        if 'javascript' in msg or 'js' in msg:
            return ("**Exemples JavaScript**\n\n"
                "```javascript\n// Fetch API\nfetch('https://api.example.com/users')\n  .then(res => res.json())\n  .then(data => console.log(data));\n\n// Async/Await\nasync function getData() {\n  const res = await fetch('/api/data');\n  return await res.json();\n}\n```")
        if 'lettre' in msg or 'motivation' in msg or 'cv' in msg:
            return ("**Modèle de lettre de motivation**\n\n"
                "```\nObjet : Candidature au poste de [Poste]\n\nMadame, Monsieur,\n\nActuellement [situation actuelle], je suis vivement intéressé(e) "
                "par le poste de [Poste] au sein de votre entreprise.\n\n"
                "Fort(e) de [X] années d'expérience dans le domaine de [domaine], "
                "j'ai développé des compétences solides en [compétence 1], [compétence 2] et [compétence 3].\n\n"
                "Je suis convaincu(e) que mon profil correspond à vos attentes "
                "et je serais ravi(e) de vous rencontrer pour en discuter.\n\n"
                "Dans l'attente de votre retour, je vous prie d'agréer, "
                "Madame, Monsieur, l'expression de mes salutations distinguées.\n\n[Prénom Nom]\n```")
        return (
            "**Exemples variés**\n\n"
            "```python\n# Python\nprint(\"Hello World\")\n```\n\n"
            "```javascript\n// JavaScript\nconsole.log(\"Hello World\");\n```\n\n"
            "```html\n<!-- HTML -->\n<h1>Hello World</h1>\n```\n\n"
            "```sql\n-- SQL\nSELECT 'Hello World';\n```\n\n"
            "Précise ce dont tu veux un exemple ! (code, lettre, calcul...)"
        )

    def _handle_python(self, msg):
        if 'flask' in msg:
            return ("**Flask - Application web**\n\n"
                "```python\nfrom flask import Flask, jsonify, request\napp = Flask(__name__)\n\n@app.route('/api/hello')\ndef hello():\n    return jsonify({\"message\": \"Hello World\"})\n\nif __name__ == '__main__':\n    app.run(debug=True)\n```")
        if 'django' in msg:
            return ("**Django - Structure**\n\n"
                "```bash\ndjango-admin startproject monsite\ncd monsite\npython manage.py startapp blog\n```\n\n"
                "```python\n# blog/models.py\nfrom django.db import models\n\nclass Article(models.Model):\n    titre = models.CharField(max_length=200)\n    contenu = models.TextField()\n    date = models.DateTimeField(auto_now_add=True)\n```")
        return ("**Python - Essentiel**\n\n"
            "```python\n# Liste en compréhension\ncarres = [x**2 for x in range(10) if x % 2 == 0]\n\n# Gestion d'erreurs\ntry:\n    with open('fichier.txt') as f:\n        contenu = f.read()\nexcept FileNotFoundError:\n    print('Fichier introuvable')\n\n# Décorateur\ndef timer(func):\n    import time\n    def wrapper(*args, **kwargs):\n        debut = time.time()\n        r = func(*args, **kwargs)\n        print(f\"Temps: {time.time()-debut:.2f}s\")\n        return r\n    return wrapper\n```")

    def _handle_javascript(self, msg):
        if 'react' in msg:
            return ("**React - Composant**\n\n"
                "```jsx\nfunction App() {\n  const [users, setUsers] = useState([]);\n  \n  useEffect(() => {\n    fetch('/api/users')\n      .then(r => r.json())\n      .then(setUsers);\n  }, []);\n\n  return (\n    <ul>\n      {users.map(u => <li key={u.id}>{u.name}</li>)}\n    </ul>\n  );\n}\n```")
        if 'node' in msg or 'express' in msg:
            return ("**Node.js Express**\n\n"
                "```javascript\nconst express = require('express');\nconst app = express();\n\napp.get('/api/users', (req, res) => {\n  res.json([{ id: 1, name: 'Alice' }]);\n});\n\napp.listen(3000);\n```")
        return ("**JavaScript - Essentiel**\n\n"
            "```javascript\n// Arrow functions\nconst add = (a, b) => a + b;\n\n// Destructuration\nconst { name, age } = user;\n\n// Spread\nconst arr2 = [...arr1, 4, 5];\n\n// Template\nconsole.log(`Bonjour ${name}`);\n\n// Map/Filter\nnombres.map(n => n * 2).filter(n => n > 5);\n```")

    def _handle_html_css(self, msg):
        if 'flexbox' in msg or 'flex' in msg:
            return ("**CSS Flexbox**\n\n```css\n.container {\n  display: flex;\n  justify-content: center;\n  align-items: center;\n  gap: 16px;\n}\n```")
        if ('grid' in msg) and 'flex' not in msg:
            return ("**CSS Grid**\n\n```css\n.grid {\n  display: grid;\n  grid-template-columns: repeat(3, 1fr);\n  gap: 16px;\n}\n@media (max-width: 768px) {\n  .grid { grid-template-columns: 1fr; }\n}\n```")
        return ("**HTML/CSS - Template**\n\n"
            "```html\n<!DOCTYPE html>\n<html lang=\"fr\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n  <title>Site</title>\n  <style>\n    * { margin: 0; padding: 0; box-sizing: border-box; }\n    body { font-family: system-ui, sans-serif; }\n    .card {\n      background: #fff;\n      border-radius: 12px;\n      padding: 24px;\n      box-shadow: 0 2px 8px rgba(0,0,0,0.1);\n    }\n  </style>\n</head>\n<body>\n  <div class=\"card\">\n    <h1>Bienvenue</h1>\n  </div>\n</body>\n</html>\n```")

    def _handle_sql(self, msg):
        if 'join' in msg:
            return ("**SQL JOIN**\n\n```sql\nSELECT u.nom, c.titre\nFROM utilisateurs u\nINNER JOIN commandes c ON u.id = c.utilisateur_id;\n\nSELECT u.nom, c.titre\nFROM utilisateurs u\nLEFT JOIN commandes c ON u.id = c.utilisateur_id;\n```")
        return ("**SQL - Requêtes**\n\n"
            "```sql\nSELECT * FROM users WHERE age > 18 ORDER BY nom;\n\nSELECT statut, COUNT(*) as total\nFROM commandes\nGROUP BY statut\nHAVING total > 5;\n\nCREATE INDEX idx_email ON users(email);\n```")

    def _handle_git(self, msg):
        return ("**Git - Commandes**\n\n```bash\ngit init\ngit add .\ngit commit -m \"Message\"\ngit checkout -b nouvelle-branche\ngit push origin main\ngit pull\ngit log --oneline --graph\ngit stash\ngit stash pop\n```")

    def _handle_api(self, msg):
        return ("**API REST**\n\n```python\nfrom flask import Flask, jsonify, request\napp = Flask(__name__)\n\n@app.route('/api/produits', methods=['GET'])\ndef lister():\n    return jsonify(produits)\n\n@app.route('/api/produits', methods=['POST'])\ndef creer():\n    data = request.get_json()\n    return jsonify(data), 201\n\n@app.route('/api/produits/<int:id>', methods=['DELETE'])\ndef supprimer(id):\n    return jsonify({}), 204\n```")

    def _handle_debug(self, msg):
        return ("**Débogage**\n\n"
            "1. **Lis l'erreur** : le message et la stack trace\n"
            "2. **Strategies** :\n"
            "   ```python\n   print(f\"DEBUG: {var}\")\n   import logging; logging.debug(f\"{var}\")\n   ```\n"
            "   ```javascript\n   console.log(var); debugger;\n   ```\n"
            "3. **Outils** : pdb (Python), DevTools (JS), Flask debug mode\n\n"
            "Quelle est l'erreur exacte ?")

    def _handle_algo(self, msg):
        return ("**Algorithmes**\n\n"
            "```python\ndef tri_bulles(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr\n\ndef recherche_binaire(arr, cible):\n    g, d = 0, len(arr)-1\n    while g <= d:\n        m = (g+d)//2\n        if arr[m] == cible: return m\n        if arr[m] < cible: g = m+1\n        else: d = m-1\n    return -1\n```\n\n"
            "| Structure | Accès | Recherche |\n|-----------|-------|-----------|\n| Liste | O(1) | O(n) |\n| Dict | O(1) | O(1) |\n| Arbre | O(log n) | O(log n) |")

    def _handle_docker(self, msg):
        return ("**Docker**\n\n```dockerfile\nFROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"python\", \"app.py\"]\n```\n\n```bash\ndocker build -t mon-app .\ndocker run -p 5000:5000 mon-app\ndocker-compose up -d\n```")

    def _handle_linux(self, msg):
        return ("**Commandes Linux**\n\n```bash\npwd           # répertoire courant\nls -la        # liste\ncd dossier    # navigation\nmkdir dossier  # créer dossier\ncp a.txt b.txt # copier\nmv a.txt b.txt # renommer\ncat fichier   # afficher\nchmod +x script.sh  # rendre exécutable\nps aux        # processus\nkill -9 PID   # tuer\ncurl localhost:5000\nssh user@host\n```")

    def _handle_math(self, msg):
        if 'équation' in msg or 'equation' in msg or 'second' in msg:
            return ("**Équation du second degré**\n\n"
                "Forme : ax² + bx + c = 0\n\n"
                "Discriminant : Δ = b² - 4ac\n\n"
                "Si Δ > 0 : x = (-b ± √Δ) / 2a  (2 solutions)\n"
                "Si Δ = 0 : x = -b / 2a  (1 solution)\n"
                "Si Δ < 0 : pas de solution réelle\n\n"
                "```python\ndef resoudre(a, b, c):\n    delta = b**2 - 4*a*c\n    if delta > 0:\n        x1 = (-b + delta**0.5) / (2*a)\n        x2 = (-b - delta**0.5) / (2*a)\n        return x1, x2\n    elif delta == 0:\n        return -b / (2*a)\n    else:\n        return None\n```")
        if 'probabilité' in msg or 'probabilite' in msg:
            return ("**Probabilités**\n\n"
                "P(A) = nombre de cas favorables / nombre de cas possibles\n\n"
                "Propriétés :\n"
                "- P(Ω) = 1 (événement certain)\n"
                "- P(∅) = 0 (événement impossible)\n"
                "- 0 ≤ P(A) ≤ 1\n"
                "- P(A̅) = 1 - P(A)\n"
                "- P(A ∪ B) = P(A) + P(B) - P(A ∩ B)")
        if 'dériv' in msg or 'primitive' in msg or 'intégrale' in msg:
            return ("**Calcul différentiel**\n\n"
                "Dérivée de x^n → n·x^(n-1)\n"
                "Dérivée de sin(x) → cos(x)\n"
                "Dérivée de cos(x) → -sin(x)\n"
                "Dérivée de e^x → e^x\n"
                "Dérivée de ln(x) → 1/x\n\n"
                "**Règles :**\n"
                "(u+v)' = u' + v'\n"
                "(uv)' = u'v + uv'\n"
                "(u/v)' = (u'v - uv')/v²")
        return ("**Mathématiques**\n\n"
            "Je peux t'aider avec :\n"
            "- **Algèbre** : équations, systèmes, matrices\n"
            "- **Analyse** : dérivées, intégrales, limites\n"
            "- **Géométrie** : aires, volumes, trigonométrie\n"
            "- **Statistiques** : moyenne, médiane, écart-type\n"
            "- **Probabilités** : calculs, lois, combinatoire\n\n"
            "Quel sujet mathématique t'intéresse ?")

    def _handle_language(self, msg):
        if ('français' in msg or 'francais' in msg) and 'tradu' not in msg:
            return ("**Conseils en français**\n\n"
                "- **Accord du participe passé** : avec être, le PP s'accorde avec le sujet. Avec avoir, il s'accorde avec le COD si placé avant.\n"
                "- **Subjonctif** : après \"il faut que\", \"bien que\", \"pour que\"\n"
                "- **Orthographe** : \"quelque soit\" → \"quel que soit\"\n\n"
                "Envoie-moi un texte à corriger si tu veux !")
        if 'anglais' in msg or 'english' in msg:
            return ("**English Tips**\n\n"
                "- **Present Perfect** : have/has + past participle (action with present relevance)\n"
                "- **Conditionals** : If + present → will (type 1), If + past → would (type 2)\n"
                "- **Prepositions** : in (months/years), at (times), on (days/dates)\n\n"
                "Send me a text to translate or correct!")
        if 'tradu' in msg:
            return ("Bien sûr ! Envoie-moi le texte à traduire avec les langues source et cible "
                    "(ex: \"traduis 'Hello' en français\").")
        return ("**Langues**\n\n"
            "Je peux t'aider avec :\n"
            "- **Français** : grammaire, orthographe, conjugaison, rédaction\n"
            "- **Anglais** : grammar, vocabulary, translation\n"
            "- **Traduction** : français ↔ anglais et autres langues\n\n"
            "De quoi as-tu besoin ?")

    def _handle_history(self, msg):
        return ("**Histoire**\n\n"
            "Je peux te parler de nombreuses périodes historiques :\n\n"
            "- **Préhistoire** : premiers humains, outils, art rupestre\n"
            "- **Antiquité** : Égypte, Grèce, Rome\n"
            "- **Moyen Âge** : féodalité, croisades, cathédrales\n"
            "- **Renaissance** : arts, sciences, grandes découvertes\n"
            "- **Époque moderne** : révolutions, guerres mondiales\n\n"
            "Quelle période ou événement t'intéresse ?")

    def _handle_health(self, msg):
        return ("**Santé et bien-être**\n\n"
            "⚠️ Je suis un assistant IA, pas un médecin. Consulte un professionnel de santé pour un diagnostic.\n\n"
            "Je peux donner des informations générales sur :\n"
            "- **Alimentation** : équilibre nutritionnel, régimes\n"
            "- **Sommeil** : cycles, hygiène du sommeil\n"
            "- **Exercice** : types d'activité physique\n"
            "- **Prévention** : gestes barrières, vaccination\n\n"
            "Quel sujet veux-tu aborder ?")

    def _handle_advice(self, msg):
        return ("**Conseils pratiques**\n\n"
            "Je peux te donner des conseils sur :\n\n"
            "- **Productivité** : gestion du temps, organisation, priorités\n"
            "- **Apprentissage** : méthodes d'étude, mémorisation\n"
            "- **Écriture** : rédaction de mails, rapports, CV\n"
            "- **Code** : bonnes pratiques, architecture, design patterns\n"
            "- **Carrière** : orientation, entretiens, développement pro\n\n"
            "De quel sujet veux-tu des conseils ?")

    def _handle_gaming(self, msg):
        if 'minecraft' in msg:
            return ("**Minecraft**\n\n"
                "Un jeu de construction et survie en monde ouvert.\n"
                "- **Survie** : récolte des ressources, construis un abri, affronte les monstres\n"
                "- **Créatif** : construis librement avec tous les blocs\n"
                "- **Astuce** : toujours avoir un lit pour passer la nuit !")
        if 'fortnite' in msg:
            return ("**Fortnite**\n\n"
                "Battle Royale avec construction et événements live.\n"
                "Construis des murs et rampes pour te protéger et gagner en hauteur.")
        if 'zelda' in msg:
            return ("**The Legend of Zelda**\n\n"
                "Une saga d'aventure et d'exploration. Le dernier opus **Tears of the Kingdom** "
                "reprend la map de Breath of the Wild avec de nouvelles capacités.")
        return ("**Jeux vidéo**\n\n"
            "Je peux parler de : Minecraft, Fortnite, Zelda, Elden Ring, GTA, FIFA, Call of Duty... "
            "Quel jeu t'intéresse ?")

    def _handle_music(self, msg):
        if 'guitare' in msg:
            return ("**Guitare - Bases**\n\n"
                "- **Accords ouverts** : Do (C), Ré (D), Mi (E), Sol (G), La (A)\n"
                "- **Gammes** : pentatonique mineure pour le blues/rock\n"
                "- **Conseil** : apprends d'abord les accords de base, puis le rythme")
        if 'piano' in msg:
            return ("**Piano - Bases**\n\n"
                "- **Doigté** : 1=pouce, 2=index, 3=majeur, 4=annulaire, 5=auriculaire\n"
                "- **Gamme de Do majeur** : Do Ré Mi Fa Sol La Si Do\n"
                "- **Conseil** : pratique les gammes 10 min/jour")
        return ("**Musique**\n\n"
            "Je peux t'aider avec : instruments (guitare, piano), solfège, composition, "
            "ou te parler de mes connaissances musicales !")

    def _handle_travel(self, msg):
        if 'japon' in msg:
            return ("**Voyage au Japon**\n\n"
                "- **Tokyo** : Shibuya, Akihabara, temples\n"
                "- **Kyoto** : temples historiques, geishas, bambouseraie\n"
                "- **Osaka** : street food, château, aquarium\n"
                "- **Conseil** : le Japan Rail Pass est économique pour voyager")
        if 'france' in msg or 'paris' in msg:
            return ("**Voyage en France**\n\n"
                "- **Paris** : Tour Eiffel, Louvre, Montmartre\n"
                "- **Sud** : Nice, Marseille, Calanques\n"
                "- **Montagne** : Alpes, Chamonix, ski\n"
                "- **Conseil** : le TGV relie Paris à Lyon en 2h")
        return ("**Voyage**\n\n"
            "Je peux te parler de destinations : Japon, France, Italie, USA, Thaïlande... "
            "Quel pays ou ville veux-tu explorer ?")

    def _handle_food(self, msg):
        if 'italien' in msg or 'pizza' in msg or 'pasta' in msg:
            return ("**Cuisine italienne**\n\n"
                "- **Pizza Margherita** : tomate, mozzarella, basilic\n"
                "- **Pasta carbonara** : œufs, pecorino, guanciale (pas de crème !)\n"
                "- **Tiramisu** : café, mascarpone, cacao")
        if 'indien' in msg or 'curry' in msg:
            return ("**Cuisine indienne**\n\n"
                "- **Curry** : base d'oignons, gingembre, épices\n"
                "- **Naan** : pain traditionnel cuit au four tandoor\n"
                "- **Biryani** : riz parfumé aux épices et viande")
        return ("**Cuisine**\n\n"
            "Je peux te parler de : cuisine italienne, indienne, japonaise, française, "
            "ou te donner des recettes et conseils culinaires !")

    def _handle_sport(self, msg):
        return ("**Sport et fitness**\n\n"
            "Quel sport t'intéresse ?\n"
            "- **Musculation** : exercices de base (squat, développé, soulevé de terre)\n"
            "- **Course à pied** : plan d'entraînement, endurance, fractionné\n"
            "- **Football** : conseils, tactiques, exercices\n"
            "- **Yoga** : postures, respiration, relaxation")

    def _handle_finance(self, msg):
        return ("**Économie et finances**\n\n"
            "Je peux t'aider avec :\n"
            "- **Budget personnel** : gestion, épargne, économies\n"
            "- **Investissement** : bourse, immobilier, cryptomonnaies\n"
            "- **Concepts économiques** : inflation, PIB, offre/demande\n\n"
            "⚠️ Je donne des informations générales, pas des conseils financiers personnalisés.")

    def _handle_philosophy(self, msg):
        return ("**Philosophie**\n\n"
            "Quel sujet philosophique t'intéresse ?\n"
            "- **Existentialisme** : Sartre, Camus, liberté et responsabilité\n"
            "- **Stoïcisme** : Marc Aurèle, Sénèque, contrôle des émotions\n"
            "- **Éthique** : bien/mal, morale, utilitarisme\n"
            "- **Métaphysique** : réalité, conscience, libre arbitre")

    def _handle_ai(self, msg):
        return ("**Intelligence Artificielle**\n\n"
            "- **LLM** : modèles de langage comme GPT, Gemini, Claude\n"
            "- **Machine Learning** : algorithmes qui apprennent à partir de données\n"
            "- **Deep Learning** : réseaux de neurones profonds\n"
            "- **Applications** : chatbots, vision, traduction, génération d'images\n\n"
            "Moi-même je suis un assistant IA ! Pose-moi des questions sur ce sujet.")

    def _handle_networking(self, msg):
        return ("**Réseaux et sécurité**\n\n"
            "- **Modèle OSI** : 7 couches (physique → application)\n"
            "- **TCP/IP** : protocoles fondamentaux d'Internet\n"
            "- **Sécurité** : chiffrement, VPN, firewall, mots de passe\n"
            "- **WiFi** : normes (ac, ax/6e), sécurité WPA3, ports\n\n"
            "Des questions sur un sujet précis ?")

    def _handle_general(self, message):
        msg = message.lower().strip()

        if len(msg) < 3:
            return "Je t'écoute ! Pose-moi une question, je suis là pour t'aider."

        sujet = msg[:100].strip().rstrip('?!.')

        if re.search(r'(quoi|comment|pourquoi|quand|où|qui|quel|quelle)', msg):
            return (
                f"Pour répondre à ta question sur \"{sujet}\", j'ai besoin d'un peu plus de contexte. "
                f"Explique-moi ce que tu veux savoir exactement et je te donnerai une réponse complète !"
            )

        if re.match(r'(dis|parle|raconte|explique)', msg):
            return (
                "Je peux te parler de programmation, sciences, histoire, culture, technologie... "
                "De quoi veux-tu discuter ?"
            )

        if len(msg.split()) <= 3:
            return (
                f"Parle-moi de \"{sujet}\" ! Dis-m'en un peu plus pour que je puisse t'aider "
                f"ou te donner des informations précises."
            )

        return (
            f"Tu mentionnes \"{sujet}\". "
            f"C'est un sujet intéressant ! Pour que je puisse t'aider au mieux, "
            f"dis-moi ce que tu veux savoir précisément."
        )

    def format_response(self, content):
        return markdown.markdown(content, extensions=['fenced_code', 'codehilite', 'tables'])

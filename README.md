# Class Notes — System Design & Backend Engineering

Static HTML site of detailed, interview-ready notes, published after each class so students always have a link instead of asking for notes individually.

**Live structure:**
```
notes-site/
├── index.html                     # homepage
├── assets/style.css                # shared styling
└── system-design/
    ├── index.html                  # course overview (all weeks)
    ├── week-1/
    │   ├── 01-hld-approach.html
    │   ├── 02-cap-theorem.html
    │   ├── 03-sql-vs-nosql.html
    │   ├── 04-estimation.html
    │   └── 05-api-data-model.html
    └── week-2/
        ├── 01-networking-load-balancers.html
        ├── 02-cdn-dns-reverse-proxy.html
        ├── 03-caching-strategies.html
        └── 04-redis-deep-dive.html
```

## Publish to GitHub (one-time setup)

1. Create a new **empty** repo on GitHub (no README/license) — e.g. `class-notes`.
2. From inside this `notes-site` folder, run:

```bash
git init
git add .
git commit -m "Week 1 & 2: System design foundations + core infra"
git branch -M main
git remote add origin https://github.com/<your-username>/class-notes.git
git push -u origin main
```

## Turn it into a live website (GitHub Pages) — free, no server needed

1. On GitHub, go to your repo → **Settings → Pages**.
2. Under "Build and deployment", set **Source: Deploy from a branch**.
3. Branch: `main`, folder: `/ (root)` → **Save**.
4. Wait ~1 minute, then your notes are live at:
   `https://<your-username>.github.io/class-notes/`

Share that single link with your class instead of sending files after every session.

## Adding notes after each future class

For each new week/topic:

```bash
# 1. Add new HTML file(s), e.g. system-design/week-3/01-topic.html
# 2. Update the sidebar nav (copy-paste block) in every existing page
#    AND update system-design/index.html + index.html to link the new page
git add .
git commit -m "Week 3: <topics>"
git push
```

GitHub Pages auto-redeploys within ~1 minute of every push — no extra step needed.

## Design notes

- Single shared stylesheet (`assets/style.css`) — dark theme, sidebar navigation, code blocks, callout boxes for "interview tips" vs "warnings".
- Every page is self-contained HTML (no build step, no dependencies) so it's easy to keep extending class after class.
- Sidebar is duplicated per page (no JS framework) — intentional, keeps it a plain static site that works instantly on GitHub Pages with zero configuration.

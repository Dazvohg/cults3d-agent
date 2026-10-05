"""Publish the next design in queue/ to Cults3D through the official GraphQL API.

Flow: build STL + renders -> upload them to a public "CDN" GitHub repo ->
createCreation with those raw URLs -> wait until Cults has pulled the files ->
delete the temporary copies -> move the queue item to published/.

Environment variables (set as GitHub Actions secrets / variables):
  CULTS_USERNAME   your Cults3D nickname
  CULTS_API_KEY    API key from https://cults3d.com/en/api/keys
  CDN_REPO         public repo used as temporary file host, e.g. "user/cults-cdn"
  CDN_TOKEN        fine-grained token with Contents: read & write on CDN_REPO only
  DRY_RUN          "1" = build and print the payload, touch nothing (default "0")
  MADE_WITH_AI     "1" (default) flags the design as AI-assisted, as Cults requires
  LICENSE_CODE     optional; otherwise a Cults commercial-use-for-buyer license is picked
"""
import base64
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.parse

import requests
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build import build  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = "https://cults3d.com/graphql"
DRY = os.getenv("DRY_RUN", "0") == "1"
WAIT_MAX_S = 15 * 60


def log(msg):
    print(f"[{dt.datetime.utcnow():%H:%M:%S}] {msg}", flush=True)


# ---------------------------------------------------------- listing extras
COMMERCIAL_PRICE = 9.99
COMMERCIAL_SUFFIX = " | Commercial License"
COMMERCIAL_TERMS = """**COMMERCIAL LICENSE EDITION**
Same files as the personal edition, plus the right to **sell physical prints** of this design
(shops, markets, Etsy, print farms). Reselling or sharing the digital files is not allowed.
Crediting the design in your listings is appreciated.

"""
LANG_TITLES = {"fr": "Français", "de": "Deutsch", "es": "Español", "it": "Italiano"}


def with_translations(item):
    """English description + short translated summaries, so FR/DE buyers understand the listing."""
    d = item["description"].rstrip()
    for lang, tr in (item.get("i18n") or {}).items():
        d += f"\n\n**{LANG_TITLES.get(lang, lang.upper())} – {tr['name']}**\n{tr['summary']}"
    return d


# ---------------------------------------------------------------- Cults API
class CreateTimeout(Exception):
    """Cults did not answer createCreation in time: the design may or may not have been created."""


class Cults:
    def __init__(self, user, key):
        tok = base64.b64encode(f"{user}:{key}".encode()).decode()
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Basic {tok}", "Content-Type": "application/json"})

    def q(self, query, variables=None, tries=5, timeout=60):
        for i in range(tries):
            r = self.s.post(API, json={"query": query, "variables": variables or {}}, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i * 5)
                continue
            if r.status_code == 401:
                sys.exit("Cults3D rejected the credentials (check CULTS_USERNAME / CULTS_API_KEY).")
            r.raise_for_status()
            data = r.json()
            if data.get("errors"):
                sys.exit(f"GraphQL error: {json.dumps(data['errors'])}")
            return data["data"]
        sys.exit("Cults3D API kept failing (rate limit or server error).")

    def resolve_category(self, name, sub):
        cats = self.q("{ categories { id name(locale: EN) children { id name(locale: EN) } } }")["categories"]
        norm = lambda s: (s or "").strip().lower()
        cat = next((c for c in cats if norm(c["name"]) == norm(name)), None)
        if not cat:
            names = [c["name"] for c in cats]
            cat = next((c for c in cats if norm(c["name"]) in ("various", "other", "divers")), cats[0])
            log(f"Category '{name}' not found in {names}; using '{cat['name']}'")
        subs = [c["id"] for c in (cat.get("children") or []) if sub and norm(c["name"]) == norm(sub)]
        return cat["id"], subs

    def resolve_license(self, priced, commercial=False):
        """Personal-use license for the normal listing, commercial-use license for the commercial one."""
        forced = os.getenv("LICENSE_CODE_COMMERCIAL" if commercial else "LICENSE_CODE")
        if forced:
            return forced
        lic = self.q("{ licenses { code name(locale: EN) availableOnFreeDesigns availableOnPricedDesigns } }")["licenses"]
        ok = [l for l in lic if (l["availableOnPricedDesigns"] if priced else l["availableOnFreeDesigns"])]
        low = lambda l: (l.get("name") or "").lower()
        if commercial:
            pref = next((l for l in ok if "commercial" in low(l) and "non" not in low(l)), None)
        else:
            pref = next((l for l in ok if any(k in low(l) for k in ("private", "personal", "non-commercial",
                                                                        "non commercial"))), None)
        if not pref:
            log(f"No {'commercial' if commercial else 'personal'} license found in {[l['name'] for l in ok]}; "
                f"using {ok[0]['name']}")
        return (pref or ok[0])["code"]

    def localize(self, creation_id, lang, name, description, price=0.0):
        """Best effort: add a translated title/description. Never stops the publication if the API refuses."""
        lit = json.dumps
        # Cults validates the whole creation on update: a paid design must send its price again (min 0.5)
        price_arg = f", price: {price}" if price and price > 0 else ""
        m = f"""mutation {{ updateCreation(id: {lit(creation_id)}, locale: {lang.upper()}, name: {lit(name)},
                description: {lit(description)}{price_arg}) {{ creation {{ id }} errors }} }}"""
        try:
            r = self.s.post(API, json={"query": m}, timeout=60).json()
            errs = r.get("errors") or (r.get("data") or {}).get("updateCreation", {}).get("errors")
            log(f"  {lang.upper()} translation: {'OK' if not errs else f'not accepted ({errs})'}")
        except Exception as e:  # noqa: BLE001
            log(f"  {lang.upper()} translation skipped: {e}")

    def create(self, **kw):
        # Arguments are inlined as literals (JSON strings are valid GraphQL strings), so we
        # don't depend on the exact names of Cults' input types.
        lit = json.dumps
        cur = kw["currency"].upper()
        if cur not in ("USD", "EUR"):
            sys.exit(f"Unsupported currency {cur}")
        m = f"""mutation {{ createCreation(
            name: {lit(kw['name'])}, description: {lit(kw['description'])},
            imageUrls: {lit(kw['imageUrls'])}, fileUrls: {lit(kw['fileUrls'])},
            locale: EN, categoryId: {lit(kw['categoryId'])}, subCategoryIds: {lit(kw['subCategoryIds'])},
            downloadPrice: {float(kw['price'])}, currency: {cur}, licenseCode: {lit(kw['license'])},
            tagNames: {lit(kw['tags'])}, madeWithAi: {lit(bool(kw['ai']))}
          ) {{ creation {{ id url(locale: EN) }} errors }} }}"""
        try:   # Cults downloads every file while it answers: it can take minutes
            res = self.q(m, tries=1, timeout=300)["createCreation"]
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            raise CreateTimeout(str(e)) from e
        if res.get("errors"):
            sys.exit(f"Cults3D refused the design: {res['errors']}")
        return res["creation"]

    def find_by_name(self, name):
        """Latest own creation with exactly this name (used to avoid duplicates after a timeout)."""
        res = self.q("""{ myself { creationsBatch(limit: 40, offset: 0) { results { id name(locale: EN) url(locale: EN) } } } }""")
        for c in res["myself"]["creationsBatch"]["results"]:
            if (c.get("name") or "").strip() == name.strip():
                return {"id": c["id"], "url": c["url"]}
        return None

    def assets(self, slug):
        d = self.q("""query($slug:String!){ creation(slug:$slug){ blueprints{ id } illustrations{ id } } }""",
                   {"slug": slug})["creation"]
        return (len(d["blueprints"]), len(d["illustrations"])) if d else (0, 0)


# ------------------------------------------------------ temporary file host
class Cdn:
    def __init__(self, repo, token):
        self.repo = repo
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        info = self.s.get(f"https://api.github.com/repos/{repo}").json()
        self.branch = info.get("default_branch", "main")
        self.private = bool(info.get("private", False))

    def put(self, path, local):
        url = f"https://api.github.com/repos/{self.repo}/contents/{path}"
        body = {"message": f"tmp upload {path}", "content": base64.b64encode(local.read_bytes()).decode(),
                "branch": self.branch}
        r = self.s.put(url, json=body, timeout=120)
        r.raise_for_status()
        return r.json()["content"]["sha"], (
            f"https://raw.githubusercontent.com/{self.repo}/{self.branch}/{urllib.parse.quote(path)}")

    def delete(self, path, sha):
        url = f"https://api.github.com/repos/{self.repo}/contents/{path}"
        self.s.delete(url, json={"message": f"cleanup {path}", "sha": sha, "branch": self.branch}, timeout=60)


# ------------------------------------------------------- resilient create
def mirror(raw_url):
    """Same file through the jsDelivr CDN (GitHub raw sometimes refuses Cults' downloader)."""
    rest = raw_url.split("raw.githubusercontent.com/", 1)[1].split("/", 3)   # user, repo, branch, path
    return f"https://cdn.jsdelivr.net/gh/{rest[0]}/{rest[1]}@{rest[2]}/{rest[3]}"


def raw_of(url):
    """Inverse of mirror(): the raw.githubusercontent URL of a file, whichever host the URL uses."""
    if "cdn.jsdelivr.net/gh/" in url:
        user, repo_branch, path = url.split("cdn.jsdelivr.net/gh/", 1)[1].split("/", 2)
        repo, branch = repo_branch.split("@", 1)
        return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
    return url


def make_creator(cults, cleanup, file_urls, image_urls, sleep=time.sleep, warm=True):
    """Returns (create_retry, dropped). Cults fetches the URLs itself and its downloader is flaky, so:
    - an image that cannot be downloaded is dropped (the listing still goes out with the others);
    - a design file that cannot be downloaded is retried, then served from the jsDelivr mirror;
    - after any timeout or 'Unexpected error' the design is looked up by name first: it may exist already."""
    import re
    dropped = set()   # raw URLs of images Cults could not download

    def create_retry(**kw):
        kw["imageUrls"] = [u for u in kw["imageUrls"] if raw_of(u) not in dropped]
        use_mirror = False
        for attempt in range(1, 9):
            try:
                return cults.create(**kw)
            except (CreateTimeout, SystemExit) as e:
                msg = str(e.code) if isinstance(e, SystemExit) else f"timeout {e}"
                transient = isinstance(e, CreateTimeout) or "Could not download" in msg or "Unexpected error" in msg
                if not transient or attempt == 8:
                    cleanup()
                    if isinstance(e, SystemExit):
                        raise
                    sys.exit("Cults did not answer and the design was not created. Run Publish again later.")
                log(f"Cults problem (attempt {attempt}/8): {msg[:300]}")
                found = cults.find_by_name(kw["name"])
                if found:
                    log(f"It was created anyway: {found['url']}")
                    return found
                m = re.search(r"Could not download URL (\S+?)['\"\]]", msg)
                failed = raw_of(m.group(1)) if m else None
                if failed and failed in [raw_of(u) for u in image_urls]:
                    if len(kw["imageUrls"]) > 1 and failed != raw_of(image_urls[0]):   # the cover is never dropped
                        dropped.add(failed)
                        kw["imageUrls"] = [u for u in kw["imageUrls"] if raw_of(u) != failed]
                        log(f"Dropping the image Cults cannot download; {len(kw['imageUrls'])} images left")
                        sleep(5)
                        continue
                elif failed and attempt >= 2 and not use_mirror:   # a design file keeps failing: use the mirror
                    use_mirror = True
                    kw["fileUrls"] = [mirror(raw_of(u)) for u in file_urls[:10]]
                    kw["imageUrls"] = [mirror(raw_of(u)) for u in kw["imageUrls"]]
                    if warm:
                        for u in kw["fileUrls"] + kw["imageUrls"]:
                            for _ in range(6):
                                try:
                                    if requests.get(u, headers={"Range": "bytes=0-0"}, timeout=30).status_code in (200, 206):
                                        break
                                except requests.RequestException:
                                    pass
                                sleep(5)
                sleep(20 if failed else 45)
        cleanup()
        sys.exit("Cults could not create the design after 8 attempts.")

    return create_retry, dropped


# ------------------------------------------------------------------- main
def main():
    if (ROOT / "PAUSED").exists():
        log("PAUSED file present - nothing published.")
        return
    queue = sorted((ROOT / "queue").glob("*.yaml"))
    # Never publish twice something that is already in the inventory (e.g. a seasonal template that re-entered the queue).
    inv_file = ROOT / "inventario_cults3d.csv"
    if inv_file.exists():
        import csv
        with open(inv_file, encoding="utf-8", newline="") as f:
            ya = {r.get("slug") for r in csv.DictReader(f)}
        for q in list(queue):
            it = yaml.safe_load(q.read_text(encoding="utf-8")) or {}
            if it.get("slug") in ya:
                log(f"{q.name} is already published (inventory) - moved to published/ without publishing again.")
                dest = ROOT / "published" / q.name
                dest.parent.mkdir(exist_ok=True)
                dest.write_text(q.read_text(encoding="utf-8"), encoding="utf-8")
                q.unlink()
                queue.remove(q)
    if not queue:
        log("Queue is empty - add designs to queue/.")
        return
    # Productos de temporada con la ventana abierta salen primero, aunque la cola no se haya reordenado.
    from calendario import en_ventana
    temp = {q: (yaml.safe_load(q.read_text(encoding="utf-8")) or {}).get("temporada") for q in queue}
    abiertos = [q for q in queue if temp[q] and en_ventana(temp[q])]
    normales = [q for q in queue if not temp[q]]  # fuera de ventana: esperan al año que viene
    if not (abiertos or normales):
        log("Solo quedan productos de temporada fuera de su ventana - nada para publicar hoy.")
        return
    item_path = (abiertos or normales)[0]
    b = build(item_path, ROOT / "build")
    item = b["item"]
    price = float(item.get("price", 0))
    log(f"Next: {item['name']} ({len(b['files'])} files, {len(b['images'])} images, {price} {item.get('currency', 'USD')})")

    commercial = price > 0 and item.get("commercial", True)
    com_price = float(item.get("commercial_price", COMMERCIAL_PRICE))
    description = with_translations(item)
    if DRY:
        log("DRY_RUN=1 -> payload preview only:")
        prev = {k: item[k] for k in ("name", "price", "category", "tags")}
        prev["commercial_listing"] = f"{item['name']}{COMMERCIAL_SUFFIX} @ {com_price}" if commercial else None
        prev["languages"] = ["en"] + sorted((item.get("i18n") or {}).keys())
        print(json.dumps(prev, indent=2, ensure_ascii=False))
        return

    cults = Cults(os.environ["CULTS_USERNAME"], os.environ["CULTS_API_KEY"])
    cdn = Cdn(os.environ["CDN_REPO"], os.environ["CDN_TOKEN"])
    cat_id, sub_ids = cults.resolve_category(item.get("category"), item.get("subcategory"))
    license_code = cults.resolve_license(price > 0)

    stamp = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    uploaded, file_urls, image_urls = [], [], []

    def small_image(p):
        """Renders are re-saved as JPEG (about 10x smaller than PNG): Cults downloads them faster and fails less."""
        if p.suffix.lower() != ".png":
            return p
        try:
            from PIL import Image
            out = p.with_suffix(".jpg")
            Image.open(p).convert("RGB").save(out, "JPEG", quality=88, optimize=True)
            return out
        except Exception as e:  # noqa: BLE001
            log(f"Could not convert {p.name} to JPEG ({e}); uploading the PNG")
            return p

    for p in b["files"] + [small_image(i) for i in b["images"]]:
        path = f"tmp/{item['slug']}-{stamp}/{p.name}"
        sha, url = cdn.put(path, p)
        uploaded.append((path, sha))
        (file_urls if p.suffix in (".stl", ".zip", ".3mf") else image_urls).append(url)
    log(f"Uploaded {len(uploaded)} files to {cdn.repo}")

    def cleanup():
        for path, sha in uploaded:
            cdn.delete(path, sha)
        log("Temporary copies deleted from the CDN repo.")

    # Cults3D downloads these URLs anonymously: check that they are really public before asking it to.
    if cdn.private:
        cleanup()
        sys.exit(f"The repo {cdn.repo} is PRIVATE. Cults3D cannot download from a private repo: "
                 f"make it public (Settings > General > Danger Zone > Change visibility) and run again.")
    pendientes = list(file_urls[:10] + image_urls[:10])
    t0 = time.time()
    while pendientes and time.time() - t0 < 120:
        pendientes = [u for u in pendientes
                      if requests.get(u, headers={"Range": "bytes=0-0"}, timeout=30).status_code not in (200, 206)]
        if pendientes:
            time.sleep(10)
    if pendientes:
        cleanup()
        sys.exit(f"{len(pendientes)} CDN files are not reachable anonymously after 2 minutes, e.g. {pendientes[0]}. "
                 f"Open that link in a private browser window: if it says 404, the repo is private or the branch/path is wrong.")

    common = dict(imageUrls=image_urls[:10], fileUrls=file_urls[:10], categoryId=cat_id, subCategoryIds=sub_ids,
                  currency=item.get("currency", "USD"), tags=[t.lower().strip() for t in item["tags"]][:20],
                  ai=os.getenv("MADE_WITH_AI", "1") == "1")
    create_retry, dropped = make_creator(cults, cleanup, file_urls, image_urls)

    creation = create_retry(name=item["name"], description=description, price=price, license=license_code, **common)
    log(f"Created: {creation['url']}")
    com = None
    if commercial:
        com = create_retry(name=(item["name"] + COMMERCIAL_SUFFIX)[:120], description=COMMERCIAL_TERMS + description,
                           price=com_price, license=cults.resolve_license(True, commercial=True), **common)
        log(f"Created commercial listing: {com['url']}")
    for lang, tr in (item.get("i18n") or {}).items():
        cults.localize(creation["id"], lang, tr["name"], tr["summary"] + "\n\n" + description, price)

    # Wait until Cults has fetched every file before deleting the temporary copies.
    slug = urllib.parse.urlparse(creation["url"]).path.rstrip("/").split("/")[-1]
    want = (len(file_urls[:10]), max(1, len(image_urls[:10]) - len(dropped)))
    t0, got = time.time(), (0, 0)
    while time.time() - t0 < WAIT_MAX_S:
        got = cults.assets(slug)
        if com:  # the commercial listing must also have pulled everything before we delete the copies
            got2 = cults.assets(urllib.parse.urlparse(com["url"]).path.rstrip("/").split("/")[-1])
            got = (min(got[0], got2[0]), min(got[1], got2[1]))
        if got[0] >= want[0] and got[1] >= want[1]:
            break
        time.sleep(30)
    if got[0] >= want[0] and got[1] >= want[1]:
        for path, sha in uploaded:
            cdn.delete(path, sha)
        log("Cults pulled all files; temporary copies deleted.")
    else:
        log(f"WARNING: Cults shows {got} of {want} files after 15 min - temporary copies kept for review.")

    item.update({"cults_id": creation["id"], "cults_url": creation["url"],
                 "published_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                 "license_code": license_code, "assets_confirmed": list(got),
                 "commercial_url": com["url"] if com else None})
    inv = ROOT / "inventario_cults3d.csv"
    nuevo = not inv.exists()
    with open(inv, "a", encoding="utf-8", newline="") as f:
        import csv
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha_utc", "slug", "nombre", "precio", "moneda", "archivos", "url", "estado",
                        "url_comercial", "precio_comercial"])
        w.writerow([item["published_at"], item["slug"], item["name"], price, item.get("currency", "USD"),
                    len(file_urls), creation["url"],
                    "PUBLICADO" if list(got) >= list(want) else "PUBLICADO_REVISAR_ARCHIVOS",
                    com["url"] if com else "", com_price if com else ""])
    dest = ROOT / "published" / item_path.name
    dest.parent.mkdir(exist_ok=True)   # the folder does not exist on a fresh checkout (git does not track empty folders)
    dest.write_text(yaml.safe_dump(item, allow_unicode=True, sort_keys=False))
    item_path.unlink()
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### Published: [{item['name']}]({creation['url']})\n")


if __name__ == "__main__":
    main()

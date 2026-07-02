# Implementar source `animesdigital.org` no anime-dl-br

## Objetivo

Adicionar `animesdigital.org` como terceira fonte de download no script `~/.local/bin/anime-dl-br`, seguindo o mesmo padrão dos sources existentes (`AnimeFire`, `AnimesOnlineCC`).

## Arquivo

`~/.local/bin/anime-dl-br` — script Python com shebang `#!/home/ismaeldev/.local/venv/anime/bin/python3`

## Estrutura do Site

```
animesdigital.org (WordPress)
├── Busca:     GET /?s={query}
├── Anime:     GET /anime/{slug}              → lista de episódios
├── Episódio:  GET /video/a/{id}/             → página com player
└── Player 1: iframe → api.anivideo.net/videohls.php?d={hls_url}
```

### Mapeamento de URLs

| O que | URL |
|-------|-----|
| Buscar "one piece" | `https://animesdigital.org/?s=one+piece` |
| Página do anime | `https://animesdigital.org/anime/one-piece` |
| Episódio 1165 | `https://animesdigital.org/video/a/136491/` |
| Player 1 (HLS) | iframe `src="https://api.anivideo.net/videohls.php?d=https://cdn-s01.mywallpaper-4k-image.net/stream/o/one-piece/1165.mp4/index.m3u8"` |

## O que implementar

Você precisa criar **3 funções** e **integrar no CLI**.

---

### 1. `search_animesdigital(query)`

**O que faz:** Busca animes no WordPress e retorna lista de slugs/títulos.

**URL:** `https://animesdigital.org/?s={quote(query)}`

**Como extrair os resultados:**

O HTML de resultados tem links no formato:
```html
<a href="https://animesdigital.org/anime/{slug}/">
  <img alt="Título do Anime" ...>
</a>
```

Use regex:
```python
r'<a\s+href=["\']https://animesdigital\.org/anime/([^"\']+)/?["\'][^>]*>.*?<img[^>]*alt=["\']([^"\']+)["\']'
```

**Retorno:** `list[dict]` — mesmos campos dos outros sources:
```python
[
    {"slug": "one-piece", "title": "One Piece", "url": "https://animesdigital.org/anime/one-piece/"},
    ...
]
```

**Dica:** A resposta pode vir em formato WordPress padrão. Se não achar resultados, retorne lista vazia.

---

### 2. `get_animesdigital_episodes(slug)`

**O que faz:** Pega a página do anime e extrai a lista de episódios com seus IDs numéricos.

**URL:** `https://animesdigital.org/anime/{slug}/`

**Como extrair:**

A página do anime tem uma sidebar de episódios com links no formato:
```html
<a href="https://animesdigital.org/video/a/{id}/" class="episode_list_episodes_item">
  <div class="episode_list_episodes_num">1165</div>
  ...
</a>
```

Use regex:
```python
r'href=["\']https://animesdigital\.org/video/a/([^"\']+)/?["\'].*?episode_list_episodes_num[^>]*>(\d+(?:\.\d+)?)<'
```

O `{id}` (ex: `136491`) é o identificador único do post do WordPress para aquele episódio.

**Retorno:** mesmo padrão dos outros:
```python
{
    "title": "One Piece",
    "episodes": [{"num": 1165, "url": "https://animesdigital.org/video/a/136491/"}, ...],
    "total_count": 30,
}
```

**Extraia o título** do `<h1>` ou `<title>` da página.

---

### 3. `get_animesdigital_video_url(episode_url)`

**O que faz:** Acessa a página do episódio, encontra o iframe do Player 1, extrai o parâmetro `d=` da URL do iframe (que é uma URL HLS direta).

**URL recebida:** `https://animesdigital.org/video/a/{id}/`

**Como extrair:**

A página tem dois players em `<div class="tab-video">`. O **Player 1** contém um iframe:
```html
<div id="player1" class="tab-video" data-id="136491" data-video="1">
  <iframe class="metaframe rptss no-lazy"
    src="https://api.anivideo.net/videohls.php?d=https://cdn-s01.mywallpaper-4k-image.net/stream/o/one-piece/1165.mp4/index.m3u8&nocache12345"
    frameborder="0" ...>
  </iframe>
</div>
```

**Passo a passo:**

1. Fazer GET na URL do episódio
2. Extrair o `src` do iframe dentro de `#player1` (ou do primeiro `.tab-video iframe`)
3. A URL tem o formato: `https://api.anivideo.net/videohls.php?d={HLS_URL}&nocache...`
4. Extrair o valor do parâmetro `d=` (URL encoded) — essa é a stream HLS direta
5. Retornar ela

**Regex sugerido:**
```python
# Pega o src do iframe dentro do player1
r'<div[^>]*id=["\']player1["\'][^>]*>.*?<iframe[^>]*src=["\']([^"\']+)["\']'
```

Depois de extrair o `src`, parseie a URL para pegar o parâmetro `d`:
```python
from urllib.parse import urlparse, parse_qs
parsed = urlparse(iframe_src)
params = parse_qs(parsed.query)
hls_url = params.get('d', [None])[0]
```

**Retorno:** string com a URL HLS direta (ex: `https://cdn-s01.mywallpaper-4k-image.net/stream/o/one-piece/1165.mp4/index.m3u8`) ou `None`.

**Nota:** URL HLS (`.m3u8`) é suportada pelo `yt-dlp` nativamente.

---

### 4. Integrar no CLI

**Constante:**
```python
ANIMESDIGITAL_BASE = "https://animesdigital.org"
```

**Adicionar `--source animesdigital`** nos argumentos. O argparse já tem:
```python
sp.add_argument("--source", choices=["animefire", "animesonline"],
                default="animefire", help="Source")
```

Mude para:
```python
sp.add_argument("--source", choices=["animefire", "animesonline", "animesdigital"],
                default="animefire", help="Source")
```

**Criar `download_animesdigital()`** seguindo o padrão de `download_animefire()` e `download_animesonline()`:

```python
def download_animesdigital(anime_title, slug, episode, quality="best", output_dir=None, embed_subs=False):
    out_dir = output_dir or DEFAULT_DOWNLOAD_DIR
    os.makedirs(out_dir, exist_ok=True)
    plex_name = f"{anime_title} - S01E{episode:02d}.mp4"
    out_path = os.path.join(out_dir, plex_name)

    if os.path.isfile(out_path):
        print(f"  ⏭️  Already exists: {out_path}")
        return out_path

    # 1. Pega a lista de episódios para achar a URL do ep
    info = get_animesdigital_episodes(slug)
    ep_url = None
    for e in info["episodes"]:
        if e["num"] == episode:
            ep_url = e["url"]
            break

    if not ep_url:
        print(f"  ❌ Episode {episode} not found for '{slug}'")
        return None

    # 2. Extrai a URL do vídeo
    print(f"  🔍 Extracting video from AnimesDigital...")
    video_url = get_animesdigital_video_url(ep_url)

    if not video_url:
        print(f"  ❌ Could not find video URL")
        return None

    # 3. Baixa com yt-dlp (reusa _download_video)
    print(f"  📥 Downloading HLS stream...")
    return _download_video(video_url, out_path, out_dir, plex_name, embed_subs, ANIMESDIGITAL_BASE)
```

**Adicionar no `main()`** dentro do bloco `download`:

```python
elif args.source == "animesdigital":
    filepath = download_animesdigital(
        title, slug, ep, quality=args.quality,
        output_dir=output_dir, embed_subs=args.embed_subs
    )
```

Junte isso com a lógica existente de `if args.source == "animefire"` e `else` (que é animesonline).

---

## Fluxo Completo

```
Usuário: anime-dl-br search "one piece" --source animesdigital
  → search_animesdigital("one piece")
  → mostra slugs encontrados

Usuário: anime-dl-br episodes one-piece --source animesdigital
  → get_animesdigital_episodes("one-piece")
  → mostra lista de eps

Usuário: anime-dl-br download "One Piece" 1165 --source animesdigital
  → resolve_anime("animesdigital", "One Piece")  → slug
  → download_animesdigital("One Piece", slug, 1165)
     → get_animesdigital_episodes(slug) → acha URL do ep 1165
     → get_animesdigital_video_url(ep_url) → extrai HLS
     → yt-dlp baixa o .m3u8
```

## Teste Manual

```bash
# 1. Testar busca
~/.local/bin/anime-dl-br search "one piece" --source animesdigital

# 2. Testar episódios (use o slug retornado)
~/.local/bin/anime-dl-br episodes one-piece --source animesdigital --json

# 3. Testar download (dry-run com --max 1 se quiser testar o fluxo)
~/.local/bin/anime-dl-br download "One Piece" 1165 --source animesdigital --dir /tmp/teste-anime
```

## Observações

- O site é WordPress, então a estrutura HTML pode mudar com atualizações do tema
- A URL HLS do Player 1 é direta (`...mp4/index.m3u8`) e funciona com yt-dlp
- O Player 2 usa Blogger (mesmo esquema do AnimesOnlineCC) — não precisa implementar agora
- As funções seguem o **mesmo contrato** dos sources existentes para reuso do CLI
- O `--embed-subs` funciona via yt-dlp, igual nos outros sources

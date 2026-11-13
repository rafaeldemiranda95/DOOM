# DOOM (Linux source) + Docker

Código-fonte original do DOOM (id Software, release de 1997, GPL-2.0), com build e execução via Docker no Linux moderno.

A nota histórica de John Carmack continua em [`README.TXT`](README.TXT).

## Estrutura

| Pasta | Conteúdo |
| --- | --- |
| `linuxdoom-1.10/` | Cliente Linux + X11 (`linuxxdoom`) |
| `sndserv/` | Servidor de som separado (`sndserver`) |
| `ipx/`, `sersrc/` | Drivers DOS de rede (fora do build Linux) |
| `wad/` | IWAD local (não versionado) |
| `scripts/` | Download do shareware `doom1.wad` |

O repositório **não inclui** dados do jogo. É necessário um IWAD (`doom1.wad`, `doom.wad`, `doom2.wad`, etc.).

## O que foi feito neste fork

- `Dockerfile` multi-stage (Debian Bookworm)
- Build **32-bit** (`-m32`) — o código original assume ponteiros de 32 bits
- Patches aplicados só na imagem: `errno.h`, remoção de `values.h`, libs X11 modernas
- Runtime headless com **Xvfb 8 bpp** (o `i_video.c` original exige PseudoColor 256 cores)
- Entrypoint que liga o IWAD montado em `/wad` e sobe o jogo
- Script para baixar o shareware legal `doom1.wad` (ibiblio, v1.8)

## Requisitos

- Docker Desktop (Windows/macOS) ou Docker Engine (Linux)
- IWAD em `wad/` (use o script abaixo se não tiver um)

## Uso

```powershell
# 1) Baixar shareware (opcional, se ainda não tiver IWAD)
powershell -ExecutionPolicy Bypass -File .\scripts\fetch-shareware-wad.ps1

# 2) Build
docker build -t linuxdoom:local .

# 3) Run (smoke test headless com Xvfb)
docker run --rm -v "${PWD}/wad:/wad:ro" linuxdoom:local
```

Sem argumentos extras, o container inicia em **E1M1** (`-skill 3 -warp 1 1`). Isso evita as demos do IWAD 1.8, incompatíveis com o engine 1.10.

Exemplos:

```powershell
# Mesmo smoke test, explícito
docker run --rm -v "${PWD}/wad:/wad:ro" linuxdoom:local -skill 3 -warp 1 1

# Menu título (demos do WAD 1.8 vão falhar com "different game version")
docker run --rm -v "${PWD}/wad:/wad:ro" linuxdoom:local -warp 1 1
```

No Linux, o script equivalente é `scripts/fetch-shareware-wad.sh`.

## Limitações conhecidas

- **Som**: sem `/dev/dsp` no container; o `sndserver` sobe, mas o áudio falha (esperado)
- **Janela no host Windows**: PseudoColor 8-bit é frágil com VcXsrv; o fluxo suportado aqui é headless via Xvfb
- **Demos**: IWAD shareware 1.8 ≠ engine 1.10 → demos embutidas não tocam

## Licença

- Código: GPL-2.0 — ver [`LICENSE.TXT`](LICENSE.TXT)
- IWAD comercial: propriedade da Bethesda/id; o script baixa apenas o **shareware** redistribuível

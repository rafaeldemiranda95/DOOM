# Mapas (PWAD)

## E1M1 expandido

- **Saída:** [`e1m1_expandido.wad`](e1m1_expandido.wad) — sobrescreve o lump `E1M1` do IWAD em runtime (`-file`).
- **Builder:** [`build_e1m1_expandido.py`](build_e1m1_expandido.py)
- **Stats:** [`e1m1_stats.json`](e1m1_stats.json)
- **Level design:** [`../docs/e1m1-level-design.md`](../docs/e1m1-level-design.md)

### Regenerar

```powershell
# Requer: Python 3 + omgifol (`py -m pip install omgifol`)
# AJBSP em maps/tools/ajbsp/ajbsp.exe
# IWAD em wad/doom1.wad
py maps\build_e1m1_expandido.py
```

O `Dockerfile` copia `maps/e1m1_expandido.wad` para `/doom/pwad/`; o entrypoint passa `-file` automaticamente.

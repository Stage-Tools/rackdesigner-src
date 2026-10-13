import csv
import io
import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.models import DeviceDefinition, Project, Rack, RackSlot, DEFAULT_CATEGORIES, RACK_INNER_WIDTH

APP_NAME = "RackDesigner"


def get_app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_library_path() -> Path:
    return get_app_data_dir() / "library.json"


def get_projects_dir() -> Path:
    p = get_app_data_dir() / "projects"
    p.mkdir(exist_ok=True)
    return p


def get_custom_categories_path() -> Path:
    return get_app_data_dir() / "custom_categories.json"


# ── Internal helpers: atomic writes, corrupt-file quarantine, warning log ──────

def _atomic_write_json(path, data) -> None:
    """Write JSON to `path` without ever leaving a truncated/corrupt file behind:
    write to a sibling `<path>.tmp`, flush + fsync, then os.replace() it onto the
    real target. A crash or kill mid-write leaves either the old file intact or
    the new one complete — never a half-written one."""
    path = str(path)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _log_warning(message: str) -> None:
    """Appends a timestamped warning to the same crash.log used by main.py's
    global exception handler — reuses that convention rather than inventing a
    second log file. Never raises: logging must not itself take the app down."""
    try:
        log_path = get_app_data_dir() / "crash.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] WARNING: {message}\n")
    except Exception:
        pass


def _quarantine_corrupt_file(path: Path) -> Optional[Path]:
    """Renames an unparseable file aside (never deletes it) so the original
    bytes remain recoverable. Returns the backup path, or None if the rename
    itself failed."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.stem}.corrupt-{timestamp}{path.suffix}")
    counter = 2
    while backup_path.exists():
        backup_path = path.with_name(f"{path.stem}.corrupt-{timestamp}-{counter}{path.suffix}")
        counter += 1
    try:
        os.replace(path, backup_path)
        return backup_path
    except Exception:
        return None


@dataclass
class LoadResult:
    """Return type for load_library()/load_custom_categories(). `items` is the
    usable (possibly empty) data. `was_corrupt` distinguishes "file legitimately
    doesn't exist / is empty" (False) from "file existed but failed to parse,
    and was quarantined" (True) — callers that care (currently only
    preloaded_library.seed_library_if_empty()) can react differently; callers
    that just want the data use `.items` and ignore the rest."""
    items: list = field(default_factory=list)
    was_corrupt: bool = False
    backup_path: Optional[str] = None


# ── Library ───────────────────────────────────────────────────────────────────

def load_library() -> LoadResult:
    path = get_library_path()
    if not path.exists():
        return LoadResult([])
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return LoadResult([DeviceDefinition.from_dict(d) for d in data])
    except Exception as e:
        backup = _quarantine_corrupt_file(path)
        _log_warning(f"library.json failed to parse ({e!r}) — quarantined to {backup}")
        return LoadResult([], was_corrupt=True, backup_path=str(backup) if backup else None)


def save_library(devices: list[DeviceDefinition]) -> None:
    _atomic_write_json(get_library_path(), [d.to_dict() for d in devices])


# ── Custom categories ─────────────────────────────────────────────────────────

def load_custom_categories() -> LoadResult:
    path = get_custom_categories_path()
    if not path.exists():
        return LoadResult([])
    try:
        with open(path, "r", encoding="utf-8") as f:
            return LoadResult(json.load(f))
    except Exception as e:
        backup = _quarantine_corrupt_file(path)
        _log_warning(f"custom_categories.json failed to parse ({e!r}) — quarantined to {backup}")
        return LoadResult([], was_corrupt=True, backup_path=str(backup) if backup else None)


def save_custom_categories(cats: list[str]) -> None:
    _atomic_write_json(get_custom_categories_path(), cats)


def add_custom_category(name: str) -> None:
    cats = load_custom_categories().items
    if name not in cats:
        cats.append(name)
        save_custom_categories(cats)


def register_category_if_unknown(category: str) -> str:
    """If `category` isn't part of the known default+custom category set,
    registers it as a new custom category (via add_custom_category()) so it
    becomes recognized going forward. Returns `category` unchanged either
    way. Shared by CSV import, JSON library import, and DeviceForm.load()
    (see design.md) so "an unrecognized category becomes a permanent
    custom one" is decided in exactly one place."""
    from app.models import get_categories
    if category not in get_categories():
        add_custom_category(category)
    return category


# ── Projects ──────────────────────────────────────────────────────────────────

def save_project(project: Project, filepath: Optional[str] = None) -> tuple[str, str]:
    """
    Salva il progetto su disco. Ritorna (filepath, resolved_name).

    resolved_name è il nome effettivamente scritto nel file: identico a
    project.name se filepath era già noto o non c'è collisione; altrimenti un
    nome deduplicato con suffisso progressivo " (N)". Questa funzione NON
    modifica project.name in-place — è il chiamante a decidere se e come
    riflettere il nome risolto sull'oggetto in memoria (vedi MainWindow._save()).
    """
    resolved_name = project.name
    if filepath is None:
        # Controlla se esiste già un progetto con lo stesso nome (nel contenuto JSON)
        existing_names = set()
        for f in get_projects_dir().glob("*.rackproj"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                existing_names.add(data.get("name", ""))
            except Exception:
                pass

        # Se il nome esiste già, aggiunge suffisso progressivo al nome del progetto
        base_name = project.name
        if base_name in existing_names:
            counter = 2
            while f"{base_name} ({counter})" in existing_names:
                counter += 1
            resolved_name = f"{base_name} ({counter})"

        safe = "".join(c for c in resolved_name if c.isalnum() or c in " _-").strip()
        safe = safe.replace(" ", "_") or "project"
        base = get_projects_dir() / f"{safe}.rackproj"
        # Fallback sul filename se anche quello esiste
        if base.exists():
            counter = 2
            while True:
                candidate = get_projects_dir() / f"{safe} ({counter}).rackproj"
                if not candidate.exists():
                    break
                counter += 1
            filepath = str(candidate)
        else:
            filepath = str(base)

    data = project.to_dict()
    data["name"] = resolved_name
    _atomic_write_json(filepath, data)
    return filepath, resolved_name


def load_project(filepath: str) -> tuple[Project, list[str]]:
    """
    Carica un progetto da .rackproj. Ritorna (project, skip_warnings).

    Se il file non è JSON valido, l'eccezione si propaga al chiamante senza
    che il file venga toccato/rinominato — è un file dell'utente, non gestito
    dall'app (a differenza di library.json/custom_categories.json, che sono
    quarantenati su corruzione, vedi load_library()/load_custom_categories()).

    Se invece il JSON top-level è valido ma uno o più slot al suo interno non
    lo sono (es. una voce null in "slots", da una scrittura parziale), quello
    specifico slot viene saltato e il resto del progetto viene caricato
    normalmente. skip_warnings contiene un messaggio per rack con almeno uno
    slot saltato, così il chiamante può mostrare un riepilogo.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    project = Project.from_dict({**data, "racks": []})

    skip_warnings = []
    for rd in data.get("racks", []):
        try:
            slot_dicts = rd.get("slots", [])
        except AttributeError:
            skip_warnings.append("A rack entry could not be loaded and was skipped.")
            continue

        slots = []
        skipped_here = 0
        for sd in slot_dicts:
            try:
                slots.append(RackSlot.from_dict(sd))
            except Exception:
                skipped_here += 1

        rack = Rack.from_dict({**rd, "slots": []})
        rack.slots = slots
        project.racks.append(rack)
        if skipped_here:
            skip_warnings.append(
                f"{skipped_here} slot(s) in '{rack.name}' could not be loaded and were skipped.")

    return project, skip_warnings


def list_recent_projects() -> list[str]:
    files = sorted(get_projects_dir().glob("*.rackproj"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(f) for f in files]


# ── CSV import ────────────────────────────────────────────────────────────────

def _parse_float(value: str) -> Optional[float]:
    """Stringa numerica con virgola o punto → float. None se vuota/invalida."""
    if not value or not value.strip():
        return None
    try:
        return float(value.strip().replace(",", "."))
    except ValueError:
        return None


def _parse_int(value: str) -> Optional[int]:
    """Used only for the CSV 'Height (U)' column (confirmed via grep — the
    sole call site in the live tree) — rounds UP (ceiling), not Python's
    round()/round-half-to-even, since a device needing e.g. 2.5U of rack
    space genuinely needs 3U of physical space, matching mm_to_u()'s
    ceiling behavior elsewhere in this module (task.md #37)."""
    f = _parse_float(value)
    if f is None:
        return None
    return max(1, math.ceil(f))


def _read_text_with_encoding_fallback(filepath: str) -> str:
    """Try utf-8-sig first, then cp1252 (Excel's default 'CSV (Comma delimited)'
    export encoding on many Windows locales) if that fails. Raises a clear,
    user-facing ValueError if neither works, instead of letting a raw
    UnicodeDecodeError propagate from deep inside csv.DictReader iteration."""
    raw = Path(filepath).read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(
        f"Couldn't read '{Path(filepath).name}' as UTF-8 or Windows-1252. "
        "Re-save the CSV with one of those encodings and try again."
    )


def import_library_csv(filepath: str) -> tuple[list[DeviceDefinition], list[str], list[str]]:
    """
    Legge un CSV con separatore ; (o , rilevato automaticamente).
    Intestazioni attese:
      Name;Manufacturer;Model;Description;Category;Power (W);Height (U);W;H;D;Weight (kg);Notes

    'Height (U)' vuota  → rack_native=False  (ingombro da dimensioni fisiche)
    'Height (U)' valida → rack_native=True

    Ritorna:
        devices   — lista DeviceDefinition
        new_cats  — categorie nuove registrate automaticamente
        warnings  — righe saltate con motivazione
    """
    devices: list[DeviceDefinition] = []
    new_cats: list[str] = []
    warnings: list[str] = []

    known_cats = set(DEFAULT_CATEGORIES)
    existing_custom = set(load_custom_categories().items)
    known_cats |= existing_custom

    text = _read_text_with_encoding_fallback(filepath)
    sample = text[:4096]
    sep = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=sep)
    # strip spazi dai nomi colonna
    if reader.fieldnames:
        reader.fieldnames = [h.strip() if h else h for h in reader.fieldnames]

    for lineno, row in enumerate(reader, start=2):
        def col(*keys):
            for k in keys:
                v = row.get(k)
                if v is not None:
                    return v.strip()
            return ""

        name = col("Name")
        if not name:
            mfr = col("Manufacturer")
            mdl = col("Model")
            if mfr or mdl:
                name = " ".join(filter(None, [mfr, mdl]))
            else:
                warnings.append(f"Riga {lineno}: nome vuoto, nessun manufacturer/model — saltata.")
                continue

        manufacturer = col("Manufacturer")
        model        = col("Model")
        description  = col("Description")
        category     = (col("Category") or "Other").strip()

        # Case-insensitive match against the known set first — "AUDIO"
        # should map onto the existing "Audio", not register a
        # near-duplicate custom category differing only in case
        # (task.md #36). Only a genuinely new category (no
        # case-insensitive match) gets normalized to Title Case and
        # registered.
        existing_match = next((c for c in known_cats if c.lower() == category.lower()), None)
        if existing_match is not None:
            category = existing_match
        elif category:
            category = category[0].upper() + category[1:].lower()
            known_cats.add(category)
            new_cats.append(category)
            register_category_if_unknown(category)

        watts     = _parse_float(col("Power (W)", "Power"))
        u_val     = _parse_int(col("Height (U)", "Height U", "U"))
        w_mm      = _parse_float(col("W", "W (mm)", "Width"))
        h_mm      = _parse_float(col("H", "H (mm)", "H(mm)", "Height"))
        d_mm      = _parse_float(col("D", "D (mm)", "Depth"))
        weight_kg = _parse_float(col("Weight (kg)", "Weight"))
        notes     = col("Notes")

        rack_native = u_val is not None

        if rack_native:
            effective_u = u_val
        else:
            if h_mm:
                from app.models import mm_to_u
                effective_u = mm_to_u(h_mm)
            else:
                effective_u = 1

        # width_mm: solo se inferiore alla larghezza rack standard (oggetto parziale)
        width_mm_val = None
        if w_mm is not None and w_mm < RACK_INNER_WIDTH - 1:
            width_mm_val = w_mm

        dev = DeviceDefinition(
            name=name,
            manufacturer=manufacturer,
            model=model,
            description=description,
            category=category,
            u_height=effective_u,
            rack_native=rack_native,
            width_mm=width_mm_val,
            height_mm=h_mm if not rack_native else None,
            depth_mm=d_mm,
            watts=watts,
            weight_kg=weight_kg,
            notes=notes,
        )
        devices.append(dev)

    return devices, new_cats, warnings

import csv
import json
import os
from pathlib import Path
from typing import Optional
from app.models import DeviceDefinition, Project, DEFAULT_CATEGORIES, RACK_INNER_WIDTH

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


# ── Library ───────────────────────────────────────────────────────────────────

def load_library() -> list[DeviceDefinition]:
    path = get_library_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [DeviceDefinition.from_dict(d) for d in data]
    except Exception:
        return []


def save_library(devices: list[DeviceDefinition]) -> None:
    with open(get_library_path(), "w", encoding="utf-8") as f:
        json.dump([d.to_dict() for d in devices], f, indent=2, ensure_ascii=False)


# ── Custom categories ─────────────────────────────────────────────────────────

def load_custom_categories() -> list[str]:
    path = get_custom_categories_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_custom_categories(cats: list[str]) -> None:
    with open(get_custom_categories_path(), "w", encoding="utf-8") as f:
        json.dump(cats, f, indent=2, ensure_ascii=False)


def add_custom_category(name: str) -> None:
    cats = load_custom_categories()
    if name not in cats:
        cats.append(name)
        save_custom_categories(cats)


# ── Projects ──────────────────────────────────────────────────────────────────

def save_project(project: Project, filepath: Optional[str] = None) -> str:
    if filepath is None:
        # Controlla se esiste già un progetto con lo stesso nome (nel contenuto JSON)
        existing_names = set()
        for f in get_projects_dir().glob("*.rackproj"):
            try:
                import json as _json
                data = _json.loads(f.read_text(encoding="utf-8"))
                existing_names.add(data.get("name", ""))
            except Exception:
                pass

        # Se il nome esiste già, aggiunge suffisso progressivo al nome del progetto
        base_name = project.name
        if base_name in existing_names:
            counter = 2
            while f"{base_name} ({counter})" in existing_names:
                counter += 1
            project.name = f"{base_name} ({counter})"

        safe = "".join(c for c in project.name if c.isalnum() or c in " _-").strip()
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
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)
    return filepath


def load_project(filepath: str) -> Project:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Project.from_dict(data)


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
    f = _parse_float(value)
    if f is None:
        return None
    return max(1, int(round(f)))


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
    existing_custom = set(load_custom_categories())
    known_cats |= existing_custom

    with open(filepath, "r", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        sep = ";" if sample.count(";") >= sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=sep)
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
            category     = col("Category") or "Other"

            # Normalizza: prima lettera maiuscola
            category = category.strip()
            if category:
                category = category[0].upper() + category[1:]

            if category not in known_cats:
                known_cats.add(category)
                new_cats.append(category)
                add_custom_category(category)

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

from dataclasses import dataclass, field, asdict
from typing import Optional
import math
import uuid

# Built-in categories — user can add custom ones via library settings
DEFAULT_CATEGORIES = ["Video", "Audio", "Lighting", "Network", "Power", "Other"]

CATEGORY_COLORS = {
    "Video":    "#2563EB",
    "Audio":    "#D97706",
    "Lighting": "#7C3AED",
    "Network":  "#059669",
    "Power":    "#DC2626",
    "Other":    "#6B7280",
}

DEFAULT_CUSTOM_COLOR = "#6B7280"
IMAGE_WIDTH_PX    = 1200
IMAGE_U_HEIGHT_PX = 44

RACK_U_MM        = 44.45   # 1U in millimetres (EIA standard)
RACK_INNER_WIDTH = 482.0   # 19" rack usable inner width in mm


def get_categories() -> list[str]:
    """Returns default + any user-defined custom categories."""
    from app import storage
    custom = storage.load_custom_categories().items
    seen = set(DEFAULT_CATEGORIES)
    result = list(DEFAULT_CATEGORIES)
    for c in custom:
        if c not in seen:
            result.append(c)
            seen.add(c)
    return result


def category_color(cat: str) -> str:
    return CATEGORY_COLORS.get(cat, DEFAULT_CUSTOM_COLOR)


def mm_to_u(mm: float) -> int:
    """Convert a physical height in mm to the minimum number of rack units needed."""
    # Subtract a tiny epsilon before ceiling — the standard fix for the
    # classic float-division-then-ceil over-allocation: an exact multiple of
    # RACK_U_MM (e.g. 3 * 44.45) can land a hair above the true integer due
    # to floating-point division error, rounding up one extra U (task.md
    # #32). Non-exact heights are unaffected — 1e-9 is far smaller than any
    # real-world measurement precision.
    return max(1, math.ceil(mm / RACK_U_MM - 1e-9))


@dataclass
class DeviceDefinition:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: str = "Other"
    u_height: int = 1
    color: str = ""
    manufacturer: str = ""
    model: str = ""
    watts: Optional[float] = None
    weight_kg: Optional[float] = None
    depth_mm: Optional[float] = None
    width_mm: Optional[float] = None   # physical width; None = full rack width (482mm)
    height_mm: Optional[float] = None  # physical height in mm; used when rack_native=False
    rack_native: bool = True            # False = device is not 19" rack-mount (e.g. desktop/half-rack)
    description: str = ""
    notes: str = ""
    image_front: str = ""
    image_rear: str = ""

    def effective_color(self) -> str:
        return self.color if self.color else category_color(self.category)

    def effective_u_height(self) -> int:
        """
        Authoritative U height.
        - rack_native=True  → use u_height as declared
        - rack_native=False → derive from height_mm (ceiling to nearest U)
        """
        if not self.rack_native and self.height_mm:
            return mm_to_u(self.height_mm)
        return self.u_height

    def effective_width_mm(self) -> float:
        """Physical width. Full rack width when not specified."""
        return self.width_mm if self.width_mm is not None else RACK_INNER_WIDTH

    def expected_image_size(self) -> tuple:
        return IMAGE_WIDTH_PX, self.effective_u_height() * IMAGE_U_HEIGHT_PX

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DeviceDefinition":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RackSlot:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = ""
    device_snapshot: dict = field(default_factory=dict)
    position_u: int = 1
    bay: int = 0           # 0-indexed bay within the rack
    notes: str = ""
    # Tray support: when non-empty this slot is a tray containing multiple
    # non-rack-native devices placed side by side.  Each entry is a
    # device snapshot dict (same structure as device_snapshot).
    tray_devices: list = field(default_factory=list)

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "device_id":       self.device_id,
            "device_snapshot": self.device_snapshot,
            "position_u":      self.position_u,
            "bay":             self.bay,
            "notes":           self.notes,
            "tray_devices":    self.tray_devices,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RackSlot":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            device_id=d.get("device_id", ""),
            device_snapshot=d.get("device_snapshot", {}),
            position_u=d.get("position_u", 1),
            bay=d.get("bay", 0),
            notes=d.get("notes", ""),
            tray_devices=d.get("tray_devices", []),
        )

    # ── tray helpers ──────────────────────────────────────────────────────────

    @property
    def is_tray(self) -> bool:
        return len(self.tray_devices) > 0

    def tray_used_width_mm(self) -> float:
        return sum(d.get("width_mm") or RACK_INNER_WIDTH for d in self.tray_devices)

    def tray_remaining_width_mm(self) -> float:
        return RACK_INNER_WIDTH - self.tray_used_width_mm()

    def tray_can_fit(self, device_width_mm: float) -> bool:
        return self.tray_remaining_width_mm() >= device_width_mm

    def tray_u_height(self) -> int:
        """Height of the tray = ceiling U of the tallest contained device."""
        if not self.tray_devices:
            return 1
        return max(
            mm_to_u(d["height_mm"]) if d.get("height_mm") else d.get("u_height", 1)
            for d in self.tray_devices
        )

    # ── primary-device properties (works for both normal and tray slots) ──────

    @property
    def u_height(self) -> int:
        if self.is_tray:
            return self.tray_u_height()
        return self.device_snapshot.get("u_height", 1)

    @property
    def name(self) -> str:
        if self.is_tray:
            names = [d.get("name", "?") for d in self.tray_devices]
            return "Tray: " + " · ".join(names)
        return self.device_snapshot.get("name", "Unknown")

    # Colours that were used as "no colour" placeholders in older versions
    _NEUTRAL_COLORS = {"#555555", "#6b7280", ""}

    @property
    def effective_color(self) -> str:
        if self.is_tray:
            return "#2a2a2a"   # neutral tray colour
        color = self.device_snapshot.get("color", "").lower()
        if color and color not in self._NEUTRAL_COLORS:
            return color
        return category_color(self.device_snapshot.get("category", "Other"))

    @property
    def category(self) -> str:
        if self.is_tray:
            cats = list({d.get("category", "Other") for d in self.tray_devices})
            return cats[0] if len(cats) == 1 else "Mixed"
        return self.device_snapshot.get("category", "Other")

    @property
    def watts(self) -> Optional[float]:
        if self.is_tray:
            vals = [d.get("watts") for d in self.tray_devices if d.get("watts") is not None]
            return sum(vals) if vals else None
        return self.device_snapshot.get("watts")

    @property
    def weight_kg(self) -> Optional[float]:
        if self.is_tray:
            vals = [d.get("weight_kg") for d in self.tray_devices if d.get("weight_kg") is not None]
            return sum(vals) if vals else None
        return self.device_snapshot.get("weight_kg")

    @property
    def image_front(self) -> str:
        return self.device_snapshot.get("image_front", "")

    @property
    def image_rear(self) -> str:
        return self.device_snapshot.get("image_rear", "")


@dataclass
class Rack:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Rack"
    u_size: int = 20
    bays: int = 1          # number of side-by-side bays (1, 2 or 3)
    slots: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "u_size": self.u_size,
                "bays": self.bays,
                "slots": [s.to_dict() for s in self.slots]}

    @classmethod
    def from_dict(cls, d: dict) -> "Rack":
        bays = d.get("bays", 1)
        slots = [RackSlot.from_dict(s) for s in d.get("slots", [])]
        # Clamp any out-of-range bay (only reachable via already-corrupted
        # project data — nothing in the live UI can produce one) here, once,
        # at the data's entry point — rather than defensively re-checking
        # `bay` in every bay-scoped helper below (is_slot_occupied(),
        # next_free_position(), slot_at(), free_u()). Without this, a slot
        # with an out-of-range bay is silently invisible to those helpers
        # (never matches any valid bay they're called with) while free_u()
        # still counts its U against total capacity — the two disagree
        # (task.md #40).
        for s in slots:
            s.bay = max(0, min(bays - 1, s.bay))
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Rack"),
            u_size=d.get("u_size", 20),
            bays=bays,
            slots=slots,
        )

    def used_u(self) -> int:
        return sum(s.u_height for s in self.slots)

    def free_u(self) -> int:
        return self.u_size * self.bays - self.used_u()

    def total_watts(self) -> float:
        return sum(s.watts for s in self.slots if s.watts is not None)

    def total_weight(self) -> float:
        return sum(s.weight_kg for s in self.slots if s.weight_kg is not None)

    def is_slot_occupied(self, position_u: int, u_height: int, bay: int = 0) -> bool:
        for s in self.slots:
            if s.bay != bay:
                continue
            if not (position_u + u_height <= s.position_u or
                    position_u >= s.position_u + s.u_height):
                return True
        return False

    def next_free_position(self, bay: int = 0) -> Optional[int]:
        occupied = set()
        for s in self.slots:
            if s.bay != bay:
                continue
            for u in range(s.position_u, s.position_u + s.u_height):
                occupied.add(u)
        for u in range(1, self.u_size + 1):
            if u not in occupied:
                return u
        return None

    def slot_at(self, position_u: int, bay: int = 0) -> Optional["RackSlot"]:
        """Return the slot occupying position_u in bay, or None."""
        for s in self.slots:
            if s.bay == bay and s.position_u <= position_u < s.position_u + s.u_height:
                return s
        return None


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Project"
    client: str = ""
    venue: str = ""
    date: str = ""
    notes: str = ""
    racks: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "client": self.client,
                "venue": self.venue, "date": self.date, "notes": self.notes,
                "racks": [r.to_dict() for r in self.racks]}

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Project"),
            client=d.get("client", ""),
            venue=d.get("venue", ""),
            date=d.get("date", ""),
            notes=d.get("notes", ""),
            racks=[Rack.from_dict(r) for r in d.get("racks", [])],
        )

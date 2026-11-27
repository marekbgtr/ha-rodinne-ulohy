"""Deterministic household task engine. No Home Assistant dependencies.

All timestamps are aware. Occurrences snapshot rules; ledger reversals are exact.
The HA adapter serializes, persists and rolls back whole transactions.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

SCHEMA = 1
PUBLIC_ACTIONS = {"contribute_reward", "withdraw_contribution", "complete", "request_reward", "set_symbol", "set_goal"}


class RuleError(ValueError):
    """Invalid or stale user operation."""


def uid():
    return uuid4().hex


def require(condition, message):
    if not condition:
        raise RuleError(message)


def text(value, label, limit=100, empty=False):
    require(isinstance(value, str), f"{label}: očakávam text.")
    value = value.strip()
    require((empty or bool(value)) and len(value) <= limit, f"{label}: vyplň najviac {limit} znakov.")
    return value


def integer(value, label, low=0, high=10000):
    require(type(value) is int and low <= value <= high, f"{label}: celé číslo od {low} do {high}.")
    return value


def flag(value, label):
    require(type(value) is bool, f"{label}: očakávam áno/nie.")
    return value


def clock(value):
    require(isinstance(value, str) and len(value) == 5, "Čas zadaj HH:MM.")
    try:
        result = time.fromisoformat(value)
    except ValueError as exc:
        raise RuleError("Neplatný čas.") from exc
    require(result.tzinfo is None, "Čas musí byť miestny.")
    return result


class Engine:
    def __init__(self, state=None, tz="Europe/Bratislava"):
        self.zone = ZoneInfo(tz)
        self.s = deepcopy(state) if state is not None else {
            "schema": SCHEMA, "version": 0, "people": {}, "tasks": {},
            "rewards": {}, "occurrences": {}, "ledger": [], "requests": {},
            "last_day": None, "request_ids": [], "notices": [],
        }
        require(self.s.get("schema") == SCHEMA, "Nepodporovaná verzia uložených údajov.")

    def local(self, now):
        require(now.tzinfo is not None, "Čas musí obsahovať časové pásmo.")
        return now.astimezone(self.zone)

    def today(self, now):
        return self.local(now).date()

    def person(self, pid, active=False):
        p = self.s["people"].get(pid)
        require(p is not None, "Účastník neexistuje.")
        require(not active or p["active"], "Profil je neaktívny.")
        return p

    def balance(self, pid):
        return sum(e["deltas"].get(pid, 0) for e in self.s["ledger"])

    def log(self, deltas, reason, now, kind, ref="", day=None, actor="system"):
        entry = {"id": uid(), "at": now.isoformat(), "day": day or self.today(now).isoformat(),
                 "deltas": deltas, "reason": reason, "kind": kind, "ref": ref,
                 "actor": actor, "reversed_by": None}
        self.s["ledger"].append(entry)
        return entry["id"]

    def reverse(self, eid, now, reason, actor):
        entry = next((e for e in self.s["ledger"] if e["id"] == eid), None)
        require(entry is not None, "Záznam bodov sa nenašiel.")
        if entry["reversed_by"]:
            return
        reverse_id = self.log({p: -v for p, v in entry["deltas"].items()}, reason,
                              now, "reversal", entry["id"], entry["day"], actor)
        entry["reversed_by"] = reverse_id

    def selected(self, task):
        return [p for p, info in self.s["people"].items()
                if info["active"] and (task["everyone"] or p in task["people"])]

    def scheduled(self, task, day):
        if not task["active"] or day < date.fromisoformat(task["start"]):
            return False
        if task["frequency"] == "weekend":
            return day.weekday() >= 4
        if task["frequency"] == "once":
            return day.isoformat() <= task["date"]
        return task["frequency"] not in ("daily", "repeat") or day.weekday() in task["days"]

    def current(self, occ, now):
        day = self.today(now).isoformat()
        frequency = occ["task"]["frequency"]
        if frequency in ("daily", "repeat"):
            return occ["day"] == day
        return occ.get("available_from", occ["task"]["start"]) <= day and (
            not occ["cutoff"] or day <= self.local(datetime.fromisoformat(occ["cutoff"]) - timedelta(microseconds=1)).date().isoformat())

    def on_time(self, occ, member):
        return not occ["due"] or datetime.fromisoformat(member["submitted"]) <= datetime.fromisoformat(occ["due"])

    def stats_day(self, occ, member, now):
        if occ["task"]["frequency"] in ("daily", "repeat"):
            return occ["day"]
        if member.get("submitted"):
            return self.today(datetime.fromisoformat(member["submitted"])).isoformat()
        # Open multi-day tasks belong to the current day; closed ones to their final day.
        if occ["cutoff"]:
            end = self.today(datetime.fromisoformat(occ["cutoff"]) - timedelta(microseconds=1))
            return min(end, self.today(now)).isoformat()
        return self.today(now).isoformat()

    def make_occurrence(self, task, day):
        if not self.scheduled(task, day):
            return
        frequency = task["frequency"]
        period = day
        if frequency == "weekend":
            period = day - timedelta(days=day.weekday() - 4)
        elif frequency == "weekly":
            period = day - timedelta(days=day.weekday())
        elif frequency == "once":
            period = date.fromisoformat(task["date"])
        oid = task["id"] + ":" + ("ongoing" if frequency == "ongoing" else ("week:" if frequency == "weekly" else "weekend:" if frequency == "weekend" else "") + period.isoformat())
        if oid in self.s["occurrences"]:
            return
        if self.s.get("tracking_start") and day.isoformat() < self.s["tracking_start"]:
            return
        due = cutoff = None
        if frequency == "repeat":
            due = cutoff = datetime.combine(period + timedelta(days=1), time.min, self.zone)
        elif frequency == "weekend":
            end = period + timedelta(days=2)
            due = datetime.combine(end, clock(task["due"]), self.zone)
            cutoff = datetime.combine(end, clock(task["cutoff"]), self.zone)
        elif frequency == "weekly":
            due = cutoff = datetime.combine(period + timedelta(days=7), time.min, self.zone)
        elif frequency != "ongoing":
            due = datetime.combine(period, clock(task["due"]), self.zone)
            cutoff = datetime.combine(period, clock(task["cutoff"]), self.zone)
        if cutoff and self.s.get("tracking_started_at") and cutoff <= datetime.fromisoformat(self.s["tracking_started_at"]):
            return
        people = self.selected(task)
        if task["mode"] == "rotation" and people:
            start = date.fromisoformat(task["start"])
            if frequency in ("weekly", "weekend"):
                turns = (period - (start - timedelta(days=start.weekday()))).days // 7
            else:
                turns = sum((start + timedelta(days=i)).weekday() in task["days"] for i in range((day-start).days))
            people = [people[turns % len(people)]]
        if not people:
            return
        members = {p: {"submitted": None, "confirmed": False, "exempt": False,
                       "exempt_reason": "", "award": None, "penalty": None} for p in people}
        self.s["occurrences"][oid] = {
            "id": oid, "day": period.isoformat(), "task": deepcopy(task), "members": members,
            "available_from": max(task["start"], self.s.get("tracking_start") or task["start"], period.isoformat() if frequency in ("weekly", "weekend") else task["start"]),
            "winner": None, "group_award": None,
            "due": due.isoformat() if due else None,
            "cutoff": cutoff.isoformat() if cutoff else None,
        }

    def tick(self, now):
        today = self.today(now)
        start = date.fromisoformat(self.s["last_day"]) if self.s["last_day"] else today
        if (today - start).days > 31:
            self.s["notices"].append("HA bol nedostupný viac ako 31 dní. Staršie nevytvorené dni nemajú postihy.")
            self.s["notices"] = self.s["notices"][-10:]
            start = today - timedelta(days=31)
        if self.s.get("tracking_start"):
            start = max(start, date.fromisoformat(self.s["tracking_start"]))
        day = start
        while day <= today:
            for task in self.s["tasks"].values():
                self.make_occurrence(task, day)
            day += timedelta(days=1)
        self.s["last_day"] = today.isoformat()
        for occ in self.s["occurrences"].values():
            if not occ["cutoff"] or now < datetime.fromisoformat(occ["cutoff"]):
                continue
            for pid, member in occ["members"].items():
                if occ["task"]["frequency"] == "repeat":
                    self.repeat_penalty(occ, pid, now)
                    continue
                if member["exempt"] or member["submitted"] or member["penalty"]:
                    continue
                if occ["task"]["mode"] == "first":
                    continue  # A race never penalizes non-winners.
                if occ["task"]["penalty"]:
                    member["penalty"] = self.log({pid: -occ["task"]["penalty"]},
                        "Nesplnené: " + occ["task"]["name"], now, "missed", occ["id"], self.stats_day(occ, member, now))

    def amount(self, occ, member):
        on_time = member.get("full_points", False) or self.on_time(occ, member)
        return occ["task"]["points"] if on_time else occ["task"]["late_points"]

    def settle(self, occ, now, actor):
        mode = occ["task"]["mode"]
        eligible = {p: m for p, m in occ["members"].items() if not m["exempt"]}
        if mode == "together":
            if not eligible or occ["group_award"] or not all(m["confirmed"] for m in eligible.values()):
                return
            if occ["task"]["split"]:
                amount = min(self.amount(occ, m) for m in eligible.values())
                # Exact integer allocation; remaining points follow stored assignment order.
                base, extra = divmod(amount, len(eligible))
                deltas = {p: base + (i < extra) for i, p in enumerate(eligible)}
            else:
                deltas = {p: self.amount(occ, m) for p, m in eligible.items()}
            eid = self.log(deltas, "Spoločne: " + occ["task"]["name"], now,
                           "task", occ["id"], self.stats_day(occ, max(eligible.values(), key=lambda m: m["submitted"] or ""), now), actor)
            occ["group_award"] = eid
            for m in eligible.values():
                m["award"] = eid
            return
        for pid, member in eligible.items():
            if member["confirmed"] and not member["award"]:
                member["award"] = self.log({pid: self.amount(occ, member)},
                    "Splnené: " + occ["task"]["name"], now, "task", occ["id"], self.stats_day(occ, member, now), actor)

    def occurrence(self, oid, pid):
        occ = self.s["occurrences"].get(oid)
        require(occ is not None and pid in occ["members"], "Úloha nie je priradená tomuto účastníkovi.")
        return occ, occ["members"][pid]

    def complete(self, args, now, actor):
        pid = args["person"]
        self.person(pid, active=True)
        occ, m = self.occurrence(args["occurrence"], pid)
        require(self.current(occ, now), "Úloha nie je v aktuálnom období.")
        require(not m["exempt"], "Úloha je ospravedlnená.")
        if occ["task"]["frequency"] == "repeat":
            self.complete_repeat(occ, pid, now, actor)
            return
        if m["submitted"]:
            return
        require(not occ["cutoff"] or now < datetime.fromisoformat(occ["cutoff"]), "Čas na splnenie už vypršal.")
        if occ["task"]["mode"] == "first":
            require(not occ["winner"], "Odmenu už získal iný účastník.")
            occ["winner"] = pid  # Reserve winner while waiting for approval.
        m["submitted"] = now.isoformat()
        m["confirmed"] = not occ["task"]["approval"]
        self.settle(occ, now, actor)

    def approve(self, args, now, actor):
        occ, m = self.occurrence(args["occurrence"], args["person"])
        if occ["task"]["frequency"] == "repeat":
            record = self.repeat_record(m, args)
            require(not m["exempt"], "Úloha je ospravedlnená.")
            if not record["award"]:
                record["confirmed"] = True
                record["award"] = self.log({args["person"]: occ["task"]["points"]}, "Splnené: " + occ["task"]["name"], now, "task", occ["id"], occ["day"], actor)
            self.sync_repeat(m)
            return
        require(m["submitted"] and not m["exempt"], "Nie je čo schváliť.")
        m["confirmed"] = True
        self.settle(occ, now, actor)

    def cancel_linked(self, oid, people, now, actor):
        for req in self.s["requests"].values():
            if req.get("occurrence") == oid and req["person"] in people and req["status"] in ("pending", "approved"):
                req["status"] = "cancelled"
                req["note"] = "Zrušené po vrátení súvisiacej úlohy; už odovzdanú odmenu rieši rodič."
                if req.get("debit"):
                    self.reverse(req["debit"], now, "Vrátenie odmeny", actor)

    def undo(self, args, now, actor):
        occ, member = self.occurrence(args["occurrence"], args["person"])
        if occ["task"]["frequency"] == "repeat":
            record = self.repeat_record(member, args, allow_void=True)
            if record.get("voided"):
                return
            if record["award"]:
                self.reverse(record["award"], now, "Vrátenie: " + occ["task"]["name"], actor)
            record["voided"] = now.isoformat()
            self.sync_repeat(member)
            if not member["award"]:
                self.cancel_linked(occ["id"], [args["person"]], now, actor)
            return
        if not member["submitted"]:
            return
        if occ["task"]["mode"] == "together":
            affected = list(occ["members"])
            if occ["group_award"]:
                self.reverse(occ["group_award"], now, "Vrátenie: " + occ["task"]["name"], actor)
                occ["group_award"] = None
                for m in occ["members"].values():
                    m["award"] = None
        else:
            affected = [args["person"]]
            if member["award"]:
                self.reverse(member["award"], now, "Vrátenie: " + occ["task"]["name"], actor)
                member["award"] = None
        self.cancel_linked(occ["id"], affected, now, actor)
        member["submitted"] = None
        member["confirmed"] = False
        member.pop("full_points", None)
        member.pop("full_points_by", None)
        if occ["winner"] == args["person"]:
            occ["winner"] = None

    def exempt(self, args, now, actor):
        occ, member = self.occurrence(args["occurrence"], args["person"])
        require(occ["task"]["frequency"] == "repeat" or not member["submitted"], "Najprv vráť splnenie, potom úlohu ospravedlň.")
        member["exempt"] = True
        member["exempt_reason"] = text(args.get("reason", "Ospravedlnené rodičom"), "Dôvod", 200)
        if member["penalty"]:
            self.reverse(member["penalty"], now, "Ospravedlnené: " + occ["task"]["name"], actor)
            member["penalty"] = None
        if occ["task"]["frequency"] != "repeat":
            self.settle(occ, now, actor)

    def clear_group_award(self, occ, now, actor, cancel=False):
        if occ["group_award"]:
            self.reverse(occ["group_award"], now, "Prepočet spoločnej úlohy: " + occ["task"]["name"], actor)
            occ["group_award"] = None
            for member in occ["members"].values():
                member["award"] = None
            if cancel:
                self.cancel_linked(occ["id"], list(occ["members"]), now, actor)

    def unexempt(self, args, now, actor):
        occ, member = self.occurrence(args["occurrence"], args["person"])
        if not member["exempt"]:
            return
        # Bringing a member back makes a previously settled group incomplete.
        if occ["task"]["mode"] == "together":
            self.clear_group_award(occ, now, actor, cancel=True)
        member["exempt"] = False
        member["exempt_reason"] = ""
        # apply() immediately re-evaluates any overdue penalty, exactly once.

    def approve_full(self, args, now, actor):
        occ, member = self.occurrence(args["occurrence"], args["person"])
        require(occ["task"]["frequency"] != "repeat", "Opakované splnenia majú vždy plné body; použi Schváliť.")
        require(not member["exempt"], "Najprv zruš ospravedlnenie.")
        require(occ["task"]["mode"] != "first" or occ["winner"] in (None, args["person"]), "Úlohu už získal iný účastník.")
        if member.get("full_points") and member["confirmed"]:
            return
        if occ["task"]["mode"] == "together":
            self.clear_group_award(occ, now, actor)
        elif member["award"]:
            self.reverse(member["award"], now, "Prepočet na plné body: " + occ["task"]["name"], actor)
            member["award"] = None
        if member["penalty"]:
            self.reverse(member["penalty"], now, "Rodič uznal úlohu: " + occ["task"]["name"], actor)
            member["penalty"] = None
        member["submitted"] = member["submitted"] or now.isoformat()
        member["confirmed"] = True
        member["full_points"] = True
        member["full_points_by"] = {"actor": actor, "at": now.isoformat()}
        if occ["task"]["mode"] == "first":
            occ["winner"] = args["person"]
        self.settle(occ, now, actor)

    def set_statistics(self, args, now, actor):
        self.person(args["person"])["show_statistics"] = flag(args.get("enabled"), "Detské štatistiky")

    def repeat_records(self, member):
        return [r for r in member.get("attempts", []) if not r.get("voided")]

    def repeat_record(self, member, args, allow_void=False):
        record = next((r for r in member.get("attempts", []) if r["id"] == args.get("attempt")), None)
        require(record is not None and (allow_void or not record.get("voided")), "Vyber konkrétne splnenie.")
        return record

    def sync_repeat(self, member):
        records = self.repeat_records(member)
        awarded = [r for r in records if r["award"]]
        member["submitted"] = records[-1]["submitted"] if records else None
        member["confirmed"] = bool(records) and all(r["confirmed"] for r in records)
        member["award"] = awarded[-1]["award"] if awarded else None

    def complete_repeat(self, occ, pid, now, actor):
        member = occ["members"][pid]
        require(now < datetime.fromisoformat(occ["cutoff"]), "Čas na splnenie už vypršal.")
        records = self.repeat_records(member)
        task = occ["task"]
        require(not task["repeat_limit"] or len(records) < task["repeat_limit"], "Denný limit je už dosiahnutý.")
        if records:
            elapsed = (now - datetime.fromisoformat(records[-1]["submitted"])).total_seconds()
            require(elapsed >= max(2, task["repeat_gap"] * 60), "Pred ďalším splnením počkaj nastavený odstup.")
        record = {"id": uid(), "submitted": now.isoformat(), "confirmed": not task["approval"], "award": None, "voided": None}
        if record["confirmed"]:
            record["award"] = self.log({pid: task["points"]}, "Splnené: " + task["name"], now, "task", occ["id"], occ["day"], actor)
        member.setdefault("attempts", []).append(record)
        self.sync_repeat(member)

    def repeat_penalty(self, occ, pid, now):
        member = occ["members"][pid]
        missing = not member["exempt"] and len(self.repeat_records(member)) < occ["task"]["repeat_goal"]
        if missing and occ["task"]["penalty"] and not member["penalty"]:
            member["penalty"] = self.log({pid: -occ["task"]["penalty"]}, "Nesplnený denný cieľ: " + occ["task"]["name"], now, "missed", occ["id"], occ["day"])
        elif not missing and member["penalty"]:
            self.reverse(member["penalty"], now, "Denný cieľ uznaný: " + occ["task"]["name"], "system")
            member["penalty"] = None

    def stats_members(self, pid):
        for occ in self.s["occurrences"].values():
            member = occ["members"].get(pid)
            if not member:
                continue
            if occ["task"]["frequency"] != "repeat":
                yield occ, member
                continue
            records = self.repeat_records(member)
            for record in records:
                yield occ, dict(record, exempt=False)
            for _ in range(max(0, occ["task"]["repeat_goal"] - len(records))):
                yield occ, dict(member, submitted=None, award=None)

    def save_person(self, args, now, actor):
        pid = args.get("id") or uid()
        if args.get("id"):
            self.person(pid)
        old = self.s["people"].get(pid, {})
        avatar = text(args.get("avatar", ""), "Fotka", 250, empty=True)
        require(not avatar or (avatar.startswith("/local/") and not any(c in avatar for c in '<>"')), "Fotka: použi cestu /local/…")
        self.s["people"][pid] = {"id": pid, "name": text(args["name"], "Meno", 50),
            "symbol": text(args.get("symbol", "⭐"), "Symbol", 16),
            "unit": text(args.get("unit", "Hviezdičky"), "Názov bodov", 40),
            "avatar": avatar, "active": flag(args.get("active", True), "Aktívny"),
            "goal": old.get("goal", ""),
            "show_statistics": flag(args.get("show_statistics", old.get("show_statistics", False)), "Detské štatistiky")}
        # Deactivation excuses today's unfinished work; never edits past days.
        if not self.s["people"][pid]["active"]:
            for occ in self.s["occurrences"].values():
                if self.current(occ, now) and pid in occ["members"] and not occ["members"][pid]["submitted"]:
                    self.exempt({"occurrence": occ["id"], "person": pid, "reason": "Profil deaktivovaný"}, now, actor)

    def save_task(self, args, now, actor):
        tid = args.get("id") or uid()
        old = self.s["tasks"].get(tid)
        require(not args.get("id") or old is not None, "Úloha neexistuje.")
        mode = args.get("mode", "independent")
        require(mode in ("independent", "first", "together", "rotation"), "Neplatný režim.")
        frequency = args.get("frequency", "daily")
        require(frequency in ("daily", "once", "weekly", "weekend", "ongoing", "repeat"), "Neplatné opakovanie.")
        days = args.get("days", list(range(7)))
        require(isinstance(days, list) and (bool(days) or frequency not in ("daily", "repeat")) and all(type(d) is int and 0 <= d <= 6 for d in days), "Vyber dni v týždni.")
        people = args.get("people", [])
        require(isinstance(people, list) and all(p in self.s["people"] for p in people), "Neplatní účastníci.")
        everyone = flag(args.get("everyone", True), "Všetci")
        require(everyone or people, "Vyber aspoň jedného účastníka.")
        due, cutoff = args.get("due", "19:45"), args.get("cutoff", "22:00")
        if frequency in ("weekly", "ongoing", "repeat"):
            due, cutoff = "19:45", "22:00"  # Unused for these schedules.
        require(clock(due) < clock(cutoff), "Uzávierka musí byť neskôr než termín, v rovnaký deň.")
        task_date = args.get("date") or (old["date"] if old else self.today(now).isoformat())
        try:
            date.fromisoformat(task_date)
        except (ValueError, TypeError) as exc:
            raise RuleError("Neplatný dátum.") from exc
        if frequency == "once":
            require(task_date >= self.today(now).isoformat(), "Jednorazová úloha nesmie byť v minulosti.")
        points = integer(args.get("points", 1), "Body")
        late = integer(args.get("late_points", 0), "Body po termíne")
        require(late <= points, "Oneskorená odmena nesmie byť vyššia než riadna.")
        repeat_limit = integer(args.get("repeat_limit", 4), "Denný limit", 0, 100)
        repeat_goal = integer(args.get("repeat_goal", 0), "Denný cieľ", 0, 100)
        repeat_gap = integer(args.get("repeat_gap", 5), "Odstup v minútach", 0, 1440)
        if frequency == "repeat":
            require(mode in ("independent", "rotation"), "Viackrát denne: vyber Každý samostatne alebo Na striedačku.")
            require(not repeat_limit or repeat_goal <= repeat_limit, "Denný cieľ nesmie prekročiť limit.")
        task = {"id": tid, "name": text(args["name"], "Názov"), "icon": text(args.get("icon", "✓"), "Ikona", 16),
                "group": text(args.get("group", ""), "Rutina", 50, empty=True),
                "mode": mode, "frequency": frequency, "days": sorted(set(days)), "people": list(dict.fromkeys(people)),
                "everyone": everyone, "due": due, "cutoff": cutoff, "date": task_date,
                "points": points, "late_points": late,
                "repeat_limit": repeat_limit, "repeat_goal": repeat_goal, "repeat_gap": repeat_gap,
                "penalty": 0 if mode == "first" or frequency == "ongoing" else integer(args.get("penalty", 0), "Postih"),
                "approval": flag(args.get("approval", False), "Schvaľovanie"),
                "split": flag(args.get("split", False), "Delenie"),
                "active": flag(args.get("active", True), "Aktívna"),
                "start": old["start"] if old else self.today(now).isoformat()}
        # Keep active work immutable; avoid a second award when changing schedule.
        current = [o for o in self.s["occurrences"].values() if o["task"]["id"] == tid and self.current(o, now)]
        touched = lambda o: any(m["submitted"] or m["exempt"] or m["penalty"] or m.get("attempts") for m in o["members"].values())
        if old and any(touched(o) for o in current):
            require(frequency == old["frequency"] and task_date == old["date"], "Rozpracovanej úlohe nemožno zmeniť opakovanie alebo dátum. Vytvor novú úlohu.")
            self.s["tasks"][tid] = task
            return
        self.s["tasks"][tid] = task
        for occ in current:
            del self.s["occurrences"][occ["id"]]
        self.make_occurrence(task, self.today(now))

    def save_reward(self, args, now, actor):
        rid = args.get("id") or uid()
        require(not args.get("id") or rid in self.s["rewards"], "Odmena neexistuje.")
        kind = args.get("kind", "points")
        require(kind in ("points", "task", "task_points"), "Neplatný druh odmeny.")
        task = args.get("task", "")
        require(kind == "points" or task in self.s["tasks"], "Vyber súvisiacu úlohu.")
        shared = flag(args.get("shared", False), "Spoločné zbieranie")
        cost = integer(args.get("cost", 10), "Cena") if kind != "task" else 0
        require(not shared or (kind == "points" and cost > 0), "Spoločné zbieranie vyžaduje bodovú odmenu s kladnou cenou.")
        campaign = self.shared_request(rid)
        if campaign:
            require(shared and kind == "points" and cost == campaign["reward"]["cost"], "Najprv zruš alebo vybav rozbehnuté spoločné zbieranie; potom zmeň cenu alebo typ odmeny.")
        self.s["rewards"][rid] = {"id": rid, "name": text(args["name"], "Názov"),
            "icon": text(args.get("icon", "🎁"), "Ikona", 16), "kind": kind,
            "cost": cost, "shared": shared,
            "task": task if kind != "points" else "", "on_time": flag(args.get("on_time", False), "Načas"),
            "active": flag(args.get("active", True), "Aktívna")}

    def reward_link(self, reward, pid, now):
        for occ in reversed(list(self.s["occurrences"].values())):
            if occ["task"]["id"] != reward["task"] or not self.current(occ, now):
                continue
            member = occ["members"].get(pid)
            if member and member["award"] and (not reward["on_time"] or self.on_time(occ, member)):
                return occ["id"]
        return None

    def request_reward(self, args, now, actor):
        pid, rid = args["person"], args["reward"]
        self.person(pid, active=True)
        reward = self.s["rewards"].get(rid)
        require(reward and reward["active"], "Odmena nie je dostupná.")
        require(not reward.get("shared"), "Na spoločnú odmenu použi Prispieť.")
        require(not any(r["person"] == pid and r["reward"]["id"] == rid and r["status"] == "pending" for r in self.s["requests"].values()), "Žiadosť už čaká na rodiča.")
        oid = None
        if reward["kind"] in ("task", "task_points"):
            oid = self.reward_link(reward, pid, now)
            require(oid is not None, "Najprv splň súvisiacu úlohu podľa pravidiel odmeny.")
            require(not any(r.get("occurrence") == oid and r["person"] == pid and r["reward"]["id"] == rid and r["status"] in ("pending", "approved") for r in self.s["requests"].values()), "Táto odmena už bola vyžiadaná.")
        require(self.balance(pid) >= reward["cost"] or reward["kind"] == "task", "Zatiaľ nemáš dosť bodov.")
        req_id = uid()
        debit = self.log({pid: -reward["cost"]}, "Rezervácia odmeny: " + reward["name"], now, "reward", req_id, actor=actor)
        self.s["requests"][req_id] = {"id": req_id, "person": pid, "reward": deepcopy(reward),
            "at": now.isoformat(), "status": "pending", "debit": debit, "occurrence": oid, "note": ""}

    def shared_request(self, rid):
        return next((r for r in self.s["requests"].values()
                     if r.get("shared") and r["reward"]["id"] == rid and r["status"] in ("funding", "pending")), None)

    def contributions(self, req):
        totals = {}
        for item in req.get("contributions", []):
            if not item.get("withdrawn"):
                totals[item["person"]] = totals.get(item["person"], 0) + item["amount"]
        return totals

    def contribute_reward(self, args, now, actor):
        pid, rid = args["person"], args["reward"]
        self.person(pid, active=True)
        reward = self.s["rewards"].get(rid)
        require(reward and reward["active"] and reward.get("shared"), "Spoločná odmena nie je dostupná.")
        amount = integer(args.get("amount"), "Príspevok", 1)
        req = self.shared_request(rid)
        require(not req or req["status"] == "funding", "Odmena už čaká na rodiča.")
        remaining = (req["reward"]["cost"] - sum(self.contributions(req).values())) if req else reward["cost"]
        require(amount <= remaining, "Príspevok prekračuje zostávajúcu cenu odmeny.")
        require(self.balance(pid) >= amount, "Na tento príspevok nemáš dosť bodov.")
        if req is None:
            req_id = uid()
            req = {"id": req_id, "person": pid, "reward": deepcopy(reward), "shared": True,
                   "at": now.isoformat(), "status": "funding", "debit": None, "occurrence": None,
                   "note": "", "contributions": []}
            self.s["requests"][req_id] = req
        debit = self.log({pid: -amount}, "Príspevok na spoločnú odmenu: " + req["reward"]["name"], now, "reward", req["id"], actor=actor)
        req["contributions"].append({"person": pid, "amount": amount, "debit": debit, "at": now.isoformat(), "withdrawn": None})
        if sum(self.contributions(req).values()) == req["reward"]["cost"]:
            req["status"] = "pending"
            req["ready_at"] = now.isoformat()

    def withdraw_contribution(self, args, now, actor):
        pid = args["person"]
        self.person(pid)  # An inactive profile can still recover reserved points.
        req = self.s["requests"].get(args["request"])
        require(req and req.get("shared"), "Spoločné zbieranie neexistuje.")
        require(req["status"] == "funding", "Po nazbieraní ceny môže odmenu zrušiť rodič.")
        for item in req["contributions"]:
            if item["person"] == pid and not item.get("withdrawn"):
                self.reverse(item["debit"], now, "Vrátený príspevok: " + req["reward"]["name"], actor)
                item["withdrawn"] = now.isoformat()
        if not self.contributions(req):
            req["status"] = "cancelled"

    def decide_reward(self, args, now, actor):
        req = self.s["requests"].get(args["request"])
        require(req is not None, "Žiadosť neexistuje.")
        require(args["decision"] in ("approve", "reject"), "Neplatné rozhodnutie.")
        if req["status"] not in ("pending", "funding"):
            return
        require(args["decision"] == "reject" or req["status"] == "pending", "Najprv treba nazbierať celú cenu.")
        if args["decision"] == "reject":
            if req.get("shared"):
                for item in req["contributions"]:
                    if not item.get("withdrawn"):
                        self.reverse(item["debit"], now, "Zrušená spoločná odmena: " + req["reward"]["name"], actor)
                        item["withdrawn"] = now.isoformat()
            else:
                self.reverse(req["debit"], now, "Zamietnutá odmena: " + req["reward"]["name"], actor)
            req["status"] = "rejected"
        else:
            req["status"] = "approved"

    def return_reward(self, args, now, actor):
        req = self.s["requests"].get(args["request"])
        require(req is not None, "Žiadosť neexistuje.")
        if req["status"] == "returned":
            return
        require(req["status"] == "approved", "Vrátiť možno iba potvrdenú odmenu.")
        if req.get("shared"):
            for item in req["contributions"]:
                if not item.get("withdrawn"):
                    self.reverse(item["debit"], now, "Vrátená odmena: " + req["reward"]["name"], actor)
                    item["withdrawn"] = now.isoformat()
        else:
            self.reverse(req["debit"], now, "Vrátená odmena: " + req["reward"]["name"], actor)
        req["status"] = "returned"
        req["returned_at"] = now.isoformat()
        req["returned_by"] = actor

    def adjust(self, args, now, actor):
        pid = args["person"]
        self.person(pid)
        delta = integer(args["delta"], "Zmena bodov", -10000)
        require(delta != 0, "Zadaj nenulovú zmenu.")
        self.log({pid: delta}, text(args.get("reason", "Ručná úprava"), "Dôvod", 200), now, "manual", actor=actor)

    def reverse_adjustment(self, args, now, actor):
        entry = next((e for e in self.s["ledger"] if e["id"] == args["entry"]), None)
        require(entry and entry["kind"] == "manual", "Takto možno vrátiť iba ručnú úpravu.")
        self.reverse(entry["id"], now, "Vrátenie ručnej úpravy", actor)

    def set_symbol(self, args, now, actor):
        p = self.person(args["person"], active=True)
        p["symbol"] = text(args["symbol"], "Symbol", 16)
        p["unit"] = text(args["unit"], "Názov bodov", 40)

    def set_goal(self, args, now, actor):
        p = self.person(args["person"], active=True)
        rid = args.get("reward", "")
        require(not rid or (rid in self.s["rewards"] and self.s["rewards"][rid]["kind"] in ("points", "task_points")), "Vyber bodovú odmenu.")
        p["goal"] = rid

    def set_group_order(self, args, now, actor):
        order = args.get("groups")
        require(isinstance(order, list) and len(order) <= 100, "Neplatné poradie skupín.")
        cleaned = [text(g, "Skupina", 50) for g in order]
        require(len(cleaned) == len(set(cleaned)), "Skupiny sa nesmú opakovať.")
        self.s["group_order"] = cleaned

    def groups(self):
        known = list(dict.fromkeys(
            [t.get("group") or "Úlohy" for t in self.s["tasks"].values()]
            + [o["task"].get("group") or "Úlohy" for o in self.s["occurrences"].values()]
        ))
        ordered = [g for g in self.s.get("group_order", []) if g in known]
        return ordered + [g for g in known if g not in ordered]

    def reset_progress(self, args, now, actor):
        require(args.get("confirmation") == "VYMAZAT HISTORIU",
                "Pre potvrdenie napíš VYMAZAT HISTORIU.")
        require(args.get("backup_confirmed") is True, "Najprv potvrď vytvorenie zálohy HA.")
        start = args.get("start", "tomorrow")
        require(start in ("today", "tomorrow"), "Vyber začiatok dnes alebo zajtra.")
        start_date = self.today(now) + timedelta(days=1 if start == "tomorrow" else 0)
        self.s["occurrences"] = {}
        self.s["ledger"] = []
        self.s["requests"] = {}
        self.s["notices"] = []
        self.s["last_day"] = self.today(now).isoformat()
        self.s["tracking_start"] = start_date.isoformat()
        self.s["tracking_started_at"] = now.isoformat()
        # Definitions, symbols, goals, display order, version and replay guards stay.

    def weekly_stats(self, pid, now, weeks=8):
        today = self.today(now)
        monday = today - timedelta(days=today.weekday())
        result = []
        for offset in range(weeks):
            start = monday - timedelta(days=7 * offset)
            end = start + timedelta(days=6)
            counters = {"assigned": 0, "completed": 0, "on_time": 0,
                        "late": 0, "missed": 0, "waiting": 0, "open": 0, "exempt": 0}
            by_day = [{"date": (start + timedelta(days=i)).isoformat(),
                       "future": start + timedelta(days=i) > today,
                       "closed": start + timedelta(days=i) < today,
                       "assigned": 0, "completed": 0, "on_time": 0, "missed": 0,
                       "exempt": 0, "waiting": 0, "open": 0} for i in range(7)]
            groups = {}
            for occ, member in self.stats_members(pid):
                if occ["task"]["mode"] == "first" and occ["winner"] != pid:
                    continue  # A voluntary race never lowers non-winners' success rate.
                effective = self.stats_day(occ, member, now)
                if not start.isoformat() <= effective <= min(end, today).isoformat():
                    continue
                day = by_day[(date.fromisoformat(effective) - start).days]
                name = occ["task"].get("group") or "Úlohy"
                group = groups.setdefault(name, {"name": name, "assigned": 0, "completed": 0, "on_time": 0})
                if member["exempt"]:
                    counters["exempt"] += 1
                    day["exempt"] += 1
                    continue
                counters["assigned"] += 1
                day["assigned"] += 1
                group["assigned"] += 1
                if member["award"]:
                    counters["completed"] += 1
                    day["completed"] += 1
                    group["completed"] += 1
                    if self.on_time(occ, member):
                        counters["on_time"] += 1
                        day["on_time"] += 1
                        group["on_time"] += 1
                    else:
                        counters["late"] += 1
                elif member["submitted"]:
                    counters["waiting"] += 1
                    day["waiting"] += 1
                elif occ["cutoff"] and now >= datetime.fromisoformat(occ["cutoff"]):
                    counters["missed"] += 1
                    day["missed"] += 1
                else:
                    counters["open"] += 1
                    day["open"] += 1
            amounts = {"earned": 0, "bonus": 0, "penalties": 0, "spent": 0}
            for entry in self.s["ledger"]:
                if not start.isoformat() <= entry["day"] <= end.isoformat() or entry["reversed_by"] or entry["kind"] == "reversal":
                    continue
                delta = entry["deltas"].get(pid, 0)
                if entry["kind"] == "task":
                    amounts["earned"] += delta
                elif entry["kind"] == "manual":
                    amounts["bonus"] += max(0, delta)
                    amounts["penalties"] += max(0, -delta)
                elif entry["kind"] == "missed":
                    amounts["penalties"] += max(0, -delta)
                elif entry["kind"] == "reward":
                    amounts["spent"] += max(0, -delta)
            perfect = sum(d["closed"] and d["assigned"] > 0 and d["completed"] == d["assigned"] for d in by_day)
            badges = []
            if counters["completed"] >= 1:
                badges.append({"icon": "🌱", "label": "Prvý krok"})
            if counters["completed"] >= 5:
                badges.append({"icon": "✋", "label": "Päť hotových"})
            if counters["completed"] >= 3 and counters["on_time"] == counters["completed"]:
                badges.append({"icon": "⏰", "label": "Všetko načas"})
            if perfect:
                badges.append({"icon": "🌟", "label": "Hotový deň"})
            rate = round(100 * counters["completed"] / counters["assigned"]) if counters["assigned"] else None
            if not counters["assigned"]:
                summary = "Zatiaľ tu nie sú hodnotené úlohy. Každý nový krok sa počíta."
            elif not counters["completed"]:
                summary = "Začni jednou malou úlohou. Aj malý krok je pokrok."
            elif counters["completed"] == counters["assigned"]:
                summary = "Všetky doteraz priradené úlohy sú hotové. Výborne!"
            elif counters["on_time"] == counters["completed"]:
                summary = "Všetko, čo máš hotové, si zvládol načas. Pokračuj vlastným tempom."
            else:
                summary = "Každá dokončená úloha sa počíta. Skús si nabudúce nechať trochu viac času."
            result.append({"start": start.isoformat(), "end": end.isoformat(), "current": offset == 0,
                **counters, **amounts, "net": amounts["earned"] + amounts["bonus"] - amounts["penalties"] - amounts["spent"],
                "rate": rate, "perfect_days": perfect, "days": by_day,
                "groups": [groups[g] for g in self.groups() if g in groups and groups[g]["assigned"]],
                "badges": badges, "summary": summary})
        return result

    def apply(self, action, args, now, actor, admin):
        allowed = PUBLIC_ACTIONS | {"return_reward", "unexempt", "approve_full", "set_statistics", "save_person", "save_task", "save_reward", "approve", "undo", "exempt", "adjust", "reverse_adjustment", "decide_reward", "set_group_order", "reset_progress"}
        require(action in allowed, "Neznáma akcia.")
        require(admin or action in PUBLIC_ACTIONS, "Táto akcia je iba pre správcu Home Assistanta.")
        getattr(self, action)(args, now, actor)
        self.tick(now)

    def snapshot(self, now, admin=False):
        today = self.today(now)
        week = (today - timedelta(days=today.weekday())).isoformat()
        people = []
        for pid, p in self.s["people"].items():
            item = deepcopy(p)
            item["balance"] = self.balance(pid)
            weekly = [e for e in self.s["ledger"] if e["day"] >= week and pid in e["deltas"]]
            item["week_net"] = sum(e["deltas"][pid] for e in weekly)
            item["week_completed"] = sum(bool(m.get("award")) for o, m in self.stats_members(pid) if week <= self.stats_day(o, m, now) <= today.isoformat())
            item["show_statistics"] = p.get("show_statistics", False)
            if not admin and not item["show_statistics"]:
                item.pop("week_net", None)
                item.pop("week_completed", None)
            people.append(item)
        occurrences = [deepcopy(o) for o in self.s["occurrences"].values()
                       if self.current(o, now) or (admin and
                           (o["day"] >= (today - timedelta(days=7)).isoformat() or
                            any(m["submitted"] and not m["confirmed"] for m in o["members"].values())))]
        requests = list(self.s["requests"].values())
        recent_ids = {r["id"] for r in requests[-100:]}
        requests = [deepcopy(r) for r in requests if r["id"] in recent_ids or r["status"] in ("pending", "funding") or (admin and r["status"] == "approved")]
        for req in requests:
            if req.get("shared"):
                req["contributors"] = self.contributions(req)
                req["funded"] = sum(req["contributors"].values())
        for occ in occurrences:
            occ["current"] = self.current(occ, now)
        return {"version": self.s["version"], "admin": admin,
                "reward_links": {p: {r["id"]: self.reward_link(r, p, now) for r in self.s["rewards"].values() if r["kind"] != "points"} for p in self.s["people"]}, "today": today.isoformat(),
                "now": now.isoformat(), "timezone": str(self.zone), "people": people,
                "tasks": deepcopy(list(self.s["tasks"].values())) if admin else [],
                "rewards": deepcopy(list(self.s["rewards"].values())), "occurrences": occurrences,
                "requests": requests,
                "history": deepcopy(self.s["ledger"][-100:][::-1]), "notices": self.s["notices"],
                "group_order": self.groups(), "tracking_start": self.s.get("tracking_start"),
                "statistics": {pid: self.weekly_stats(pid, now) for pid, p in self.s["people"].items() if admin or p.get("show_statistics", False)}}

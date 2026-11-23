"""Meniu contextual pentru câmpurile de text.

Tk nu atașează niciun meniu la widget-urile `Entry`, deci clickul dreapta
nu face nimic — lipirea funcționează doar prin tastatură (Ctrl+V). Acest
modul adaugă meniul standard: decupează, copiază, lipește, selectează tot.
"""

import tkinter as tk
from typing import Any


def _widget_texte(camp: Any) -> Any:
    """Widget-ul de text efectiv al unui câmp.

    CustomTkinter 5 nu mai folosește `tkinter.Entry`, ci un `Frame` care
    conține un `Entry` intern (`_entry`). Evenimentele de mouse ajung la
    acel Entry, deci meniul trebuie legat pe el.
    """
    intern = getattr(camp, "_entry", None)
    if intern is not None and isinstance(intern, tk.Entry):
        return intern
    return camp


def ataseaza_meniu_contextual(camp: Any) -> None:
    """Adaugă meniul contextual unui câmp de text.

    Se atașează atât pe butonul 3 (Linux, Windows), cât și pe butonul 2
    (macOS, unde butonul secundar este cel drept).
    """
    tinta = _widget_texte(camp)

    meniu = tk.Menu(tinta, tearoff=0)

    def copiaza() -> None:
        """Copiază selecția în clipboard."""
        try:
            text = tinta.selection_get()
        except Exception:
            return
        try:
            tinta.clipboard_clear()
            tinta.clipboard_append(text)
        except Exception:
            pass

    def decupeaza() -> None:
        copiaza()
        try:
            tinta.delete("sel.first", "sel.last")
        except Exception:
            pass

    def lipeste() -> None:
        """Lipește textul din clipboard la poziția cursorului.

        Nu folosim evenimentul virtual `<<Paste>>`, pentru că acesta
        cere ca widget-ul să aibă focusul; accesăm clipboardul direct.
        """
        try:
            text = tinta.clipboard_get()
        except Exception:
            return
        try:
            pozitie = tinta.index("insert")
        except Exception:
            pozitie = "end"
        try:
            tinta.insert(pozitie, text)
        except Exception:
            pass

    meniu.add_command(label="Decupează", command=decupeaza)
    meniu.add_command(label="Copiază", command=copiaza)
    meniu.add_command(label="Lipește", command=lipeste)
    meniu.add_separator()
    meniu.add_command(label="Selectează tot", command=lambda: tinta.select_range(0, "end"))
    meniu.add_command(
        label="Șterge",
        command=lambda: tinta.delete(0, "end"),
    )

    def afiseaza_meniu(event) -> None:
        # Fără selecție, „Decupează" și „Copiază" nu au ce face.
        try:
            are_selectie = bool(tinta.selection_get())
        except Exception:
            are_selectie = False

        meniu.entryconfigure("Decupează", state="normal" if are_selectie else "disabled")
        meniu.entryconfigure("Copiază", state="normal" if are_selectie else "disabled")

        try:
            meniu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
        finally:
            try:
                meniu.grab_release()
            except Exception:
                pass

    tinta.bind("<Button-3>", afiseaza_meniu)
    tinta.bind("<Button-2>", afiseaza_meniu)


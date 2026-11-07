"""
Password-protected PDFs (rule 7.16-1: a protected PDF must allow screen readers to read it).

Changing the permissions needs the owner password. If the user gives it (optional), the file is
saved with the same passwords, the same encryption and the same permissions, plus the one that
lets screen readers read the text. Without the password nothing is changed and the report says
how the author can do it. The password is only kept in memory for the current run.
"""

from __future__ import annotations

import pikepdf

_owner_password: str = ""
_new_permissions: pikepdf.Permissions | None = None


def start_run(owner_password: str | None) -> None:
    global _owner_password, _new_permissions
    _owner_password = owner_password or ""
    _new_permissions = None


def open_password() -> str:
    return _owner_password


def allow_screen_readers(pdf: pikepdf.Pdf) -> bool:
    """Ask for the screen-reader permission to be added when the file is saved. False if the
    owner password was not given (or the file is not protected)."""
    global _new_permissions
    if not _owner_password or not pdf.is_encrypted:
        return False
    current = pdf.allow
    _new_permissions = pikepdf.Permissions(
        accessibility=True,
        extract=current.extract,
        modify_annotation=current.modify_annotation,
        modify_assembly=current.modify_assembly,
        modify_form=current.modify_form,
        modify_other=current.modify_other,
        print_lowres=current.print_lowres,
        print_highres=current.print_highres,
    )
    return True


def save_options(pdf: pikepdf.Pdf) -> dict:
    """How to save: unprotected files as they are; protected files with their own encryption,
    or with the new permission if it was asked for."""
    if not pdf.is_encrypted:
        return {}
    if _new_permissions is None:
        return {"encryption": True}
    info = pdf.encryption
    user = info.user_password
    user = user.decode("latin-1") if isinstance(user, bytes) else (user or "")
    revision = int(info.R)
    aes = revision >= 5 or "aes" in str(info.stream_method).lower()
    return {"encryption": pikepdf.Encryption(
        owner=_owner_password, user=user, R=revision, allow=_new_permissions, aes=aes and revision >= 4,
        metadata=revision >= 4,                 # older protection levels cannot encrypt metadata
    )}

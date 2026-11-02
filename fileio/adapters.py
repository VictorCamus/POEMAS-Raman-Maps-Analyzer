"""Adaptador segons el format de lectors de fitxers."""

from typing import TYPE_CHECKING, Protocol

from . import aist, h5, txtraman, wsxm

if TYPE_CHECKING:
    from pathlib import Path

    from classes.protocols import FileDataDict


class FileModule(Protocol):
    """Protocol de mòdul per a carregar un fitxer vàlid."""

    def load(self, filepath: Path) -> FileDataDict:
        """Carrega un fitxer d'un cert format segons trie l'usuari.

        Parameters
        ----------
        filepath: Path
            Camí del fitxer

        Returns
        -------
        file: FileDataDict
            Dades del fitxer

        """
        ...


FORMAT_MAP: dict[str, FileModule] = {
    ".aist": aist,
    ".h5": h5,
    ".hdf5": h5,
    ".top": wsxm,
    ".Auxfeed": wsxm,
    ".ch15": wsxm,
    ".ch16": wsxm,
    ".txt": txtraman,
}


def open_file(fmt: str, filepath: Path) -> FileDataDict:
    """Obri el fitxer segons el format triat.

    Parameters
    ----------
    fmt: str
        Format del fitxer
    filepath: Path
        Camí del fitxer

    Returns
    -------
    file: FileDataDict
        Dades del fitxer

    Raises
    ------
    NotImplementedError
        Si el format triat no està disponible.

    """
    module = FORMAT_MAP.get(fmt)

    if module is None:
        msg = "El format de fitxer és desconegut."
        raise NotImplementedError(msg)

    return module.load(filepath)


def open_session(filepath: Path) -> dict[str, FileDataDict]:
    """Obri una sessió amb format HDF5.

    Parameters
    ----------
    filepath: Path
        Camí del fitxer

    Returns
    -------
    session: dict[str, FileDataDict]
        Dades de la sessió

    """
    return h5.load_session(filepath)

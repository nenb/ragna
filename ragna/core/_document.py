from __future__ import annotations

import abc
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Optional, Type, TypeVar, Union

import jwt
from pydantic import BaseModel

from ._utils import PackageRequirement, RagnaException, Requirement, RequirementsMixin

if TYPE_CHECKING:
    from ragna.deploy import Config


class Document(RequirementsMixin, abc.ABC):
    """Abstract base class for all documents."""

    def __init__(
        self,
        *,
        id: Optional[uuid.UUID] = None,
        name: str,
        metadata: dict[str, Any],
        handler: Optional[DocumentHandler] = None,
    ):
        self.id = id or uuid.uuid4()
        self.name = name
        self.metadata = metadata
        self.handler = handler or self.get_handler(name)

    @staticmethod
    def supported_suffixes() -> set[str]:
        """
        Returns:
            Suffixes, i.e. `".txt"`, that can be handled by the builtin
                [ragna.core.DocumentHandler][]s.
        """
        return set(DOCUMENT_HANDLERS.keys())

    @staticmethod
    def get_handler(name: str) -> DocumentHandler:
        """Get a document handler based on a suffix.

        Args:
            name: Name of the document.
        """
        handler = DOCUMENT_HANDLERS.get(Path(name).suffix)
        if handler is None:
            raise RagnaException

        return handler

    @classmethod
    @abc.abstractmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: uuid.UUID, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        pass

    @abc.abstractmethod
    def is_readable(self) -> bool:
        ...

    @abc.abstractmethod
    def read(self) -> bytes:
        ...

    def extract_pages(self) -> Iterator[Page]:
        yield from self.handler.extract_pages(self)


class LocalDocument(Document):
    """Document class for files on the local file system.

    !!! tip

        This object is usually not instantiated manually, but rather through
        [ragna.core.LocalDocument.from_path][].
    """

    @classmethod
    def from_path(
        cls,
        path: Union[str, Path],
        *,
        id: Optional[uuid.UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
        handler: Optional[DocumentHandler] = None,
    ) -> LocalDocument:
        """Create a [ragna.core.LocalDocument][] from a path.

        Args:
            path: Local path to the file.
            id: ID of the document. If omitted, one is generated.
            metadata: Optional metadata of the document.
            handler: Document handler. If omitted, a builtin handler is selected based
                on the suffix of the `path`.

        Raises:
            RagnaException: If `metadata` is passed and contains a `"path"` key.
        """
        if metadata is None:
            metadata = {}
        elif "path" in metadata:
            raise RagnaException(
                "The metadata already includes a 'path' key. "
                "Did you mean to instantiate the class directly?"
            )

        path = Path(path).expanduser().resolve()
        metadata["path"] = str(path)

        return cls(id=id, name=path.name, metadata=metadata, handler=handler)

    @property
    def path(self) -> Path:
        return Path(self.metadata["path"])

    def is_readable(self) -> bool:
        return self.path.exists()

    def read(self) -> bytes:
        with open(self.path, "rb") as stream:
            return stream.read()

    _JWT_SECRET = os.environ.get(
        "RAGNA_API_DOCUMENT_UPLOAD_SECRET", secrets.token_urlsafe(32)[:32]
    )
    _JWT_ALGORITHM = "HS256"

    @classmethod
    async def get_upload_info(
        cls, *, config: Config, user: str, id: uuid.UUID, name: str
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        url = f"{config.api.url}/document"
        data = {
            "token": jwt.encode(
                payload={
                    "user": user,
                    "id": str(id),
                    "exp": time.time() + 5 * 60,
                },
                key=cls._JWT_SECRET,
                algorithm=cls._JWT_ALGORITHM,
            )
        }
        metadata = {"path": str(config.local_cache_root / "documents" / str(id))}
        return url, data, metadata

    @classmethod
    def decode_upload_token(cls, token: str) -> tuple[str, uuid.UUID]:
        try:
            payload = jwt.decode(
                token, key=cls._JWT_SECRET, algorithms=[cls._JWT_ALGORITHM]
            )
        except jwt.InvalidSignatureError:
            raise RagnaException(
                "Token invalid", http_status_code=401, http_detail=RagnaException.EVENT
            )
        except jwt.ExpiredSignatureError:
            raise RagnaException(
                "Token expired", http_status_code=401, http_detail=RagnaException.EVENT
            )
        return payload["user"], uuid.UUID(payload["id"])


class Page(BaseModel):
    """Dataclass for pages of a document

    Attributes:
        text: Text included in the page.
        number: Page number.
    """

    text: str
    number: Optional[int] = None


class DocumentHandler(RequirementsMixin, abc.ABC):
    """Base class for all document handlers."""

    @classmethod
    @abc.abstractmethod
    def supported_suffixes(cls) -> list[str]:
        """
        Returns:
            Suffixes supported by this document handler.
        """
        pass

    @abc.abstractmethod
    def extract_pages(self, document: Document) -> Iterator[Page]:
        """Extract pages from a document.

        Args:
            document: Document to extract pages from.

        Returns:
            Extracted pages.
        """
        ...


T = TypeVar("T", bound=DocumentHandler)


class DocumentHandlerRegistry(dict[str, DocumentHandler]):
    def load_if_available(self, cls: Type[T]) -> Type[T]:
        if cls.is_available():
            instance = cls()
            for suffix in cls.supported_suffixes():
                self[suffix] = instance

        return cls


DOCUMENT_HANDLERS = DocumentHandlerRegistry()


@DOCUMENT_HANDLERS.load_if_available
class TxtDocumentHandler(DocumentHandler):
    """Document handler for `.txt` documents."""

    @classmethod
    def supported_suffixes(cls) -> list[str]:
        return [".txt"]

    def extract_pages(self, document: Document) -> Iterator[Page]:
        yield Page(text=document.read().decode())


@DOCUMENT_HANDLERS.load_if_available
class PdfDocumentHandler(DocumentHandler):
    """Document handler for `.pdf` documents.

    !!! info "Package requirements"

        - [`pymupdf`](https://pymupdf.readthedocs.io/en/latest/)
    """

    @classmethod
    def requirements(cls) -> list[Requirement]:
        return [PackageRequirement("pymupdf>=1.23.6")]

    @classmethod
    def supported_suffixes(cls) -> list[str]:
        # TODO: pymudpdf supports a lot more formats, while .pdf is by far the most
        #  prominent. Should we expose the others here as well?
        return [".pdf"]

    def extract_pages(self, document: Document) -> Iterator[Page]:
        import fitz

        with fitz.Document(
            stream=document.read(), filetype=Path(document.name).suffix
        ) as document:
            for number, page in enumerate(document, 1):
                yield Page(text=page.get_text(sort=True), number=number)

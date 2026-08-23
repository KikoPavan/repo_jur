"""Read-only Legal Knowledge retrieval derived from the canonical bundle."""

from .index import LexicalIndexBackend, SqliteFts5Index

__all__ = ["LexicalIndexBackend", "SqliteFts5Index"]

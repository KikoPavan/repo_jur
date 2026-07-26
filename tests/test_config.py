from __future__ import annotations

import pytest

from pipeline_juridico.config import RoutingConfig


def test_routing_config_defaults_are_valid() -> None:
    config = RoutingConfig()

    assert config.native_min_text_chars == 50
    assert config.full_page_image_min_ratio == 0.70
    assert config.significant_image_min_ratio == 0.15


def test_routing_config_rejects_negative_native_text_limit() -> None:
    with pytest.raises(ValueError):
        RoutingConfig(native_min_text_chars=-1)


def test_routing_config_rejects_full_page_image_ratio_above_one() -> None:
    with pytest.raises(ValueError):
        RoutingConfig(full_page_image_min_ratio=1.5)


def test_routing_config_rejects_negative_significant_image_ratio() -> None:
    with pytest.raises(ValueError):
        RoutingConfig(significant_image_min_ratio=-0.1)


def test_routing_config_rejects_significant_ratio_above_full_page_ratio() -> None:
    with pytest.raises(
        ValueError,
        match="imagem significativa não pode ser maior que o de página inteira",
    ):
        RoutingConfig(
            full_page_image_min_ratio=0.1,
            significant_image_min_ratio=0.5,
        )


def test_routing_config_from_env_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NATIVE_MIN_TEXT_CHARS", raising=False)
    monkeypatch.delenv("FULL_PAGE_IMAGE_MIN_RATIO", raising=False)
    monkeypatch.delenv("SIGNIFICANT_IMAGE_MIN_RATIO", raising=False)

    assert RoutingConfig.from_env() == RoutingConfig()


def test_routing_config_from_env_converts_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NATIVE_MIN_TEXT_CHARS", "75")
    monkeypatch.setenv("FULL_PAGE_IMAGE_MIN_RATIO", "0.8")
    monkeypatch.setenv("SIGNIFICANT_IMAGE_MIN_RATIO", "0.25")

    config = RoutingConfig.from_env()

    assert config.native_min_text_chars == 75
    assert isinstance(config.native_min_text_chars, int)
    assert config.full_page_image_min_ratio == 0.8
    assert isinstance(config.full_page_image_min_ratio, float)
    assert config.significant_image_min_ratio == 0.25
    assert isinstance(config.significant_image_min_ratio, float)

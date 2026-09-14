def test_package_exposes_version() -> None:
    import pca

    assert pca.__version__ == "0.1.0"

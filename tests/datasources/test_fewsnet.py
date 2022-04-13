"""Tests for the FewsNet module."""

import pytest
from conftest import ISO2

from aatoolbox.config.countryconfig import FewsNetConfig
from aatoolbox.datasources.fewsnet.fewsnet import FewsNet

DATASOURCE_BASE_DIR = "fewsnet"
_PUB_YEAR = 2020
_PUB_MONTH = 7
_PUB_MONTH_STR = f"{7:02d}"


@pytest.fixture(autouse=True)
def mock_iso2(mocker):
    """Mock iso2 to iso3 conversion."""
    mocker.patch(
        "aatoolbox.datasources.fewsnet.fewsnet.Country.get_iso2_from_iso3",
        return_value=ISO2.upper(),
    )


def test_download_country(
    mock_aa_data_dir, mock_country_config, mock_download_call, mocker
):
    """Test that the correct country url and path is returned."""
    fewsnet = FewsNet(country_config=mock_country_config)
    url, output_path = mock_download_call(
        fewsnet_class=fewsnet,
        pub_year=_PUB_YEAR,
        pub_month=_PUB_MONTH,
        country_data=True,
        region_data=False,
    )
    assert (
        url == "https://fdw.fews.net/api/ipcpackage/"
        f"?country_code={ISO2.upper()}&collection_date={_PUB_YEAR}-"
        f"{_PUB_MONTH_STR}-01"
    )
    assert (
        output_path
        == mock_aa_data_dir
        / "public"
        / "raw"
        / "glb"
        / DATASOURCE_BASE_DIR
        / f"{ISO2.upper()}_{_PUB_YEAR}{_PUB_MONTH_STR}"
    )


def test_download_region(
    mock_aa_data_dir, mock_country_config, mock_download_call
):
    """Test that the correct region url and path is returned."""
    fewsnet = FewsNet(country_config=mock_country_config)
    url, output_path = mock_download_call(
        fewsnet_class=fewsnet,
        pub_year=_PUB_YEAR,
        pub_month=_PUB_MONTH,
        country_data=False,
        region_data=True,
    )

    assert (
        url == f"https://fews.net/data_portal_download/download?"
        "data_file_path=http://shapefiles.fews.net.s3.amazonaws.com/"
        f"HFIC/EA/east-africa{_PUB_YEAR}{_PUB_MONTH_STR}.zip"
    )
    assert (
        output_path
        == mock_aa_data_dir
        / "public"
        / "raw"
        / "glb"
        / DATASOURCE_BASE_DIR
        / f"EA_{_PUB_YEAR}{_PUB_MONTH_STR}"
    )


def test_download_nodata(mock_country_config, mock_download_call):
    """Test that RuntimeError is returned when no data exists."""
    with pytest.raises(RuntimeError) as e:
        fewsnet = FewsNet(country_config=mock_country_config)
        url, output_path = mock_download_call(
            fewsnet_class=fewsnet,
            pub_year=_PUB_YEAR,
            pub_month=_PUB_MONTH,
            country_data=False,
            region_data=False,
        )
        assert output_path is None
    assert (
        f"No country or regional data found for {_PUB_YEAR}-{_PUB_MONTH_STR}"
        in str(e.value)
    )


def test_invalid_region_name():
    """Test raised error when too high admin level requested."""
    with pytest.raises(ValueError):
        FewsNetConfig.regionname_valid(
            v="supereast-africa",
            values={"region_name_code_mapping": {"east-africa": "EA"}},
        )


def test_date_valid(mock_country_config):
    """Test error when input date is not valid."""
    fewsnet = FewsNet(country_config=mock_country_config)
    with pytest.raises(ValueError):
        fewsnet._check_date_validity(pub_year=2000, pub_month=12)
        fewsnet._check_date_validity(pub_year=2000, pub_month=13)
        fewsnet._check_date_validity(pub_year=2100, pub_month=12)


@pytest.fixture
def mock_download_call(mock_fake_url, mock_countryregion):
    """Mock call to download."""
    url_mock = mock_fake_url

    def _get_country_mock(
        fewsnet_class, pub_year, pub_month, country_data, region_data
    ):
        mock_countryregion(country_data, region_data)

        output_path = fewsnet_class.download(
            pub_year=pub_year, pub_month=pub_month
        )

        _, kwargs_download_url = url_mock.call_args
        url = kwargs_download_url["url"]

        return url, output_path

    return _get_country_mock


@pytest.fixture
def mock_fake_url(mocker):
    """Mock url and unzip call."""
    fakedownloadurl = mocker.patch(
        "aatoolbox.datasources.fewsnet.fewsnet.download_url"
    )
    mocker.patch("aatoolbox.datasources.fewsnet.fewsnet.unzip")
    return fakedownloadurl


@pytest.fixture
def mock_countryregion(mocker):
    """Mock that no country and/or region data exists."""

    def _mock_countryregion(country_data: bool, region_data: bool):
        if country_data:
            return None
        else:
            if region_data:
                return mocker.patch(
                    "aatoolbox.datasources.fewsnet.fewsnet."
                    "FewsNet._download_country",
                    side_effect=ValueError,
                )
            else:
                return mocker.patch(
                    "aatoolbox.datasources.fewsnet.fewsnet."
                    "FewsNet._download_country",
                    side_effect=ValueError,
                ), mocker.patch(
                    "aatoolbox.datasources.fewsnet.fewsnet."
                    "FewsNet._download_region",
                    side_effect=ValueError,
                )

    return _mock_countryregion


@pytest.fixture
def mock_gpd_read_file(mocker):
    """Mock GeoPandas file reading function."""
    return mocker.patch("aatoolbox.datasources.fewsnet.fewsnet.gpd.read_file")


def test_load(
    mock_country_config, mock_aa_data_dir, mock_gpd_read_file, mocker
):
    """Test loading of fewsnet data."""
    fewsnet = FewsNet(country_config=mock_country_config)
    mocker.patch("pathlib.Path.is_dir", return_value=True)
    mocker.patch("pathlib.Path.is_file", return_value=True)
    fewsnet.load(
        pub_year=_PUB_YEAR, pub_month=_PUB_MONTH, projection_period="CS"
    )
    mock_gpd_read_file.assert_has_calls(
        [
            mocker.call(
                mock_aa_data_dir
                / "public"
                / "raw"
                / "glb"
                / DATASOURCE_BASE_DIR
                / f"{ISO2.upper()}_{_PUB_YEAR}{_PUB_MONTH_STR}"
                / f"{ISO2.upper()}_{_PUB_YEAR}{_PUB_MONTH_STR}_CS.shp"
            ),
        ]
    )

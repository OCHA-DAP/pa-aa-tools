"""Tests for GloFAS data download and processing."""
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from aatoolbox import (
    GeoBoundingBox,
    GlofasForecast,
    GlofasReanalysis,
    GlofasReforecast,
)


@pytest.fixture
def mock_retrieve(mocker):
    """Mock only the retrieve method of the Client."""
    mocker.patch(
        "aatoolbox.datasources.glofas.glofas.cdsapi.Client.__init__",
        return_value=None,
    )
    return mocker.patch(
        "aatoolbox.datasources.glofas.glofas.cdsapi.Client.retrieve"
    )


@pytest.fixture
def mock_result(mocker):
    """Mock the entire Result class."""
    # This is needed because the reply is changed dynamically
    # so very difficult to use a Mock object
    class MockResult:
        def __init__(self, *args, **kwargs):
            self.reply = {"state": "completed"}
            self.state = None

        def update(self):
            pass

        @mock.create_autospec
        def download(self, filepath):
            pass

    return mocker.patch(
        "aatoolbox.datasources.glofas.glofas.cdsapi.api.Result",
        return_value=MockResult(),
    )


@pytest.fixture
def geo_bounding_box():
    """Input GeoBoundingBox to use."""
    # TODO: maybe move this to conftest?
    gbb = GeoBoundingBox(lat_max=1.0, lat_min=-2.2, lon_max=3.3, lon_min=-4.4)
    return gbb


def test_reanalysis_download(
    mock_country_config,
    mock_aa_data_dir,
    mock_retrieve,
    mock_result,
    geo_bounding_box,
):
    """
    Test GloFAS reanalysis download.

    Test that the query generated by the download method of GlofasReanlysis
    with default parameters is as expected
    """
    glofas_reanalysis = GlofasReanalysis(
        country_config=mock_country_config,
        geo_bounding_box=geo_bounding_box,
        start_date=datetime(year=2022, month=1, day=1),
        end_date=datetime(year=2022, month=12, day=31),
    )
    glofas_reanalysis.download()
    expected_retrieve_args = {
        "name": "cems-glofas-historical",
        "request": {
            "variable": "river_discharge_in_the_last_24_hours",
            "format": "grib",
            "product_type": "consolidated",
            "system_version": "version_3_1",
            "hydrological_model": "lisflood",
            "hyear": "2022",
            "hmonth": [str(x + 1).zfill(2) for x in range(12)],
            "hday": [str(x + 1).zfill(2) for x in range(31)],
            "area": [1.05, -4.45, -2.25, 3.35],
        },
    }
    expected_result_path = Path(
        f"{mock_aa_data_dir}/public/raw/{mock_country_config.iso3}"
        f"/glofas/cems-glofas-historical/"
        f"{mock_country_config.iso3}_"
        f"cems-glofas-historical_2022_Np1d05Sm2d25Ep3d35Wm4d45.grib"
    )
    mock_retrieve.assert_called_with(**expected_retrieve_args)
    mock_result.return_value.download.assert_called_with(
        mock.ANY, expected_result_path
    )


def test_forecast_download(
    mock_country_config,
    mock_aa_data_dir,
    mock_retrieve,
    mock_result,
    geo_bounding_box,
):
    """
    Test GloFAS forecast download.

    Test that the query generated by the download method of GlofasForecast
    with default parameters is as expected
    """
    glofas_forecast = GlofasForecast(
        country_config=mock_country_config,
        geo_bounding_box=geo_bounding_box,
        leadtime_max=3,
        start_date=datetime(year=2022, month=1, day=1),
        end_date=datetime(year=2022, month=1, day=1),
    )
    glofas_forecast.download()
    expected_retrieve_args = {
        "name": "cems-glofas-forecast",
        "request": {
            "variable": "river_discharge_in_the_last_24_hours",
            "format": "grib",
            "product_type": [
                "control_forecast",
                "ensemble_perturbed_forecasts",
            ],
            "system_version": "operational",
            "hydrological_model": "lisflood",
            "year": "2022",
            "month": "01",
            "day": "01",
            "area": [1.05, -4.45, -2.25, 3.35],
            "leadtime_hour": ["24", "48", "72"],
        },
    }

    expected_result_path = Path(
        f"{mock_aa_data_dir}/public/raw/{mock_country_config.iso3}/"
        f"glofas/cems-glofas-forecast/"
        f"{mock_country_config.iso3}_"
        f"cems-glofas-forecast_2022-01-01_ltmax03d_Np1d05Sm2d25Ep3d35Wm4d45"
        f".grib"
    )
    mock_retrieve.assert_called_with(**expected_retrieve_args)
    mock_result.return_value.download.assert_called_with(
        mock.ANY, expected_result_path
    )


def test_reforecast_download(
    mock_country_config,
    mock_aa_data_dir,
    mock_retrieve,
    mock_result,
    geo_bounding_box,
):
    """
    Test GloFAS reforecast download.

    Test that the query generated by the download method of
    GlofasReforecast with default parameters is as expected
    """
    glofas_reforecast = GlofasReforecast(
        country_config=mock_country_config,
        geo_bounding_box=geo_bounding_box,
        leadtime_max=3,
        start_date=datetime(year=2022, month=1, day=1),
        end_date=datetime(year=2022, month=1, day=31),
    )
    glofas_reforecast.download()
    expected_retrieve_args = {
        "name": "cems-glofas-reforecast",
        "request": {
            "variable": "river_discharge_in_the_last_24_hours",
            "format": "grib",
            "product_type": [
                "control_reforecast",
                "ensemble_perturbed_reforecasts",
            ],
            "system_version": "version_3_1",
            "hydrological_model": "lisflood",
            "hyear": "2022",
            "hmonth": "01",
            "hday": [str(x + 1).zfill(2) for x in range(31)],
            "area": [1.05, -4.45, -2.25, 3.35],
            "leadtime_hour": ["24", "48", "72"],
        },
    }
    expected_result_path = Path(
        f"{mock_aa_data_dir}/public/raw/{mock_country_config.iso3}/"
        f"glofas/cems-glofas-reforecast/"
        f"{mock_country_config.iso3}_"
        f"cems-glofas-reforecast_2022-01_ltmax03d_Np1d05Sm2d25Ep3d35Wm4d45"
        f".grib"
    )
    mock_retrieve.assert_called_with(**expected_retrieve_args)
    mock_result.return_value.download.assert_called_with(
        mock.ANY, expected_result_path
    )

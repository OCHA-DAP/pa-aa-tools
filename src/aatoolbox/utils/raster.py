"""
Utilities to manipulate and analyze raster data.

This module extends xarray and rioxarray to provide
additional functionality for raster processing and
post-processing. The extension is based on the
guidance for how to `extend xarray
<http://xarray.pydata.org/en/stable/internals/extending-xarray.html>`_:

However, since rioxarray already extends xarray, this
modules extensions inherit from the RasterArray and
RasterDataset extensions respectively. This ensures
cleaner code in the module as ``rio`` methods are
available immediately, but also means a couple of
design decisions are followed.

The xarray.DataArray and xarray.Dataset
extensions here inherit from rioxarray base classes.
Thus, methods that are identical for both objects
are defined in a mixin class ``AatRasterMixin`` which
can be inherited by the two respective extensions.
"""

import logging
from typing import Any, Callable, Dict, List, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import rioxarray  # noqa: F401
import xarray as xr
from rioxarray.exceptions import DimensionError, MissingCRS, NoDataInBounds
from rioxarray.raster_array import RasterArray
from rioxarray.raster_dataset import RasterDataset
from rioxarray.rioxarray import _get_data_var_message

logger = logging.getLogger(__name__)


class AatRasterMixin:
    """AA toolbox mixin base class."""

    # setting attributes to avoid mypy error, from SO
    # https://stackoverflow.com/questions/53120262/mypy-how-to-
    # ignore-missing-attribute-errors-in-mixins/53228204#53228204
    _get_obj: Callable
    x_dim: str
    y_dim: str

    def __init__(self, xarray_obj):
        super().__init__(xarray_obj)

        # Adding lat/lon to set of default spatial dims
        if "lat" in self._obj.dims and "lon" in self._obj.dims:
            self._x_dim = "lon"
            self._y_dim = "lat"

        # Managing time coordinate default dims
        self._t_dim = None
        for t in ["t", "T", "time"]:
            if t in self._obj.dims:
                self._t_dim = t

    # methods derived from rioxarray.rioxarray.x_dim and y_dim
    @property
    def t_dim(self):
        """str: The dimension for time."""
        if self._t_dim is None:
            raise DimensionError(
                "Time dimension not found. 'aat.set_time_dim()' or "
                "using 'rename()' to change the dimension name to "
                f"'t' can address this.{_get_data_var_message(self._obj)}"
            )
        return self._t_dim

    def set_time_dim(
        self, t_dim: str, inplace: bool = False
    ) -> Union[xr.DataArray, xr.Dataset]:
        """Set the time dimension of the dataset.

        Parameters
        ----------
        t_dim: str
            The name of the time dimension.
        inplace: bool, optional
            If True, it will modify the dataarray in place.
            Otherwise it will return a modified copy.

        Returns
        -------
        Union[xarray.DataArray, xarray.Dataset]

        Examples
        --------
        >>> import xarray
        >>> import numpy
        >>> da = xarray.DataArray(
        ...  numpy.arange(64).reshape(4,4,4),
        ...  coords={"lat":numpy.array([87, 88, 89, 90]),
        ...          "lon":numpy.array([5, 120, 199, 360]),
        ...          "F":numpy.array([10,11,12,13])}
        ... )
        >>> da.aat.set_time_dim(t_dim="F", inplace=True)
        >>> da.aat.t_dim
        'F'
        """
        data_obj = self._get_obj(inplace=inplace)
        if t_dim not in data_obj.dims:
            raise DimensionError(
                "Time dimension ({t_dim}) not found."
                f"{_get_data_var_message(data_obj)}"
            )
        data_obj.aat._t_dim = t_dim
        return data_obj if not inplace else None

    def correct_calendar(
        self, inplace: bool = False
    ) -> Union[xr.DataArray, xr.Dataset]:
        """Correct calendar attribute for recognition by xarray.

        Some datasets come with a wrong calendar attribute that isn't
        recognized by xarray. This function corrects the coordinate
        attribute to ensure that a ``calendar`` attribute exists
        and specifies a calendar alias that is supportable by
        ``xarray.cftime_range`` and NetCDF in general.

        Currently ensures that calendar attributes that are either
        specified with ``units="months since"`` or ``calendar="360"``
        explicitly have ``calendar="360_day"``. This is based on
        discussions in `this GitHub issue
        <https://github.com/Unidata/netcdf4-python/issues/434>`_.
        If and when further issues are found with calendar
        attributes, support for conversion will be added here.

        Parameters
        ----------
        inplace: bool, optional
            If True, it will modify the dataarray in place.
            Otherwise it will return a modified copy.

        Returns
        -------
        Union[xarray.DataArray, xarray.Dataset]
            Dataset with transformed calendar coordinate.

        Examples
        --------
        >>> import xarray
        >>> import numpy
        >>> da = xarray.DataArray(
        ...  numpy.arange(64).reshape(4,4,4),
        ...  coords={"lat":numpy.array([87, 88, 89, 90]),
        ...          "lon":numpy.array([5, 120, 199, 360]),
        ...          "t":numpy.array([10,11,12,13])}
        ... )
        >>> da["t"].attrs["units"] = "months since 1960-01-01"
        >>> da_crct = da.aat.correct_calendar()
        >>> da_crct["t"].attrs["calendar"]
        '360_day'
        """
        data_obj = self._get_obj(inplace=inplace)
        if (
            "calendar" in data_obj[self.t_dim].attrs.keys()
            and data_obj[self.t_dim].attrs["calendar"] == "360"
        ):
            data_obj[self.t_dim].attrs["calendar"] = "360_day"
            logger.info("Calendar attribute changed from '360' to '360_day'.")

        elif (
            "units" in data_obj[self.t_dim].attrs.keys()
            and "months since" in data_obj[self.t_dim].attrs["units"]
        ):
            data_obj[self.t_dim].attrs["calendar"] = "360_day"
            logger.info(
                "Calendar attribute '360_day' added, "
                "equivalent of 'units' 'months since'."
            )

        else:
            logger.info("No 'units' or 'calendar' attributes to correct.")

        return data_obj if not inplace else None

    def invert_coordinates(self, inplace: bool = False) -> xr.DataArray:
        """
        Invert latitude and longitude in data array.

        This function checks for inversion of latitude and longitude
        and inverts them if needed. Datasets with inverted coordinates
        can produce incorrect results in certain functions like
        ``rasterstats.zonal_stats()``. Correctly ordered coordinates
        should be:

        * latitude: Largest to smallest.
        * longitude: Smallest to largest.

        If data array already has correct coordinate ordering, it is
        directly returned. Function largely copied from
        https://github.com/perrygeo/python-rasterstats/issues/218.

        Parameters
        ----------
        inplace : bool, optional
            If True, will overwrite existing data array. Default is False.

        Returns
        -------
        Union[xarray.DataArray, xarray.Dataset]
            Dataset or data array with correct coordinate ordering.

        Examples
        --------
        >>> import xarray
        >>> import numpy
        >>> da = xarray.DataArray(
        ...  numpy.arange(16).reshape(4,4),
        ...  coords={"lat":numpy.array([87, 88, 89, 90]),
        ...          "lon":numpy.array([70, 69, 68, 67])}
        ... )
        >>> da_inv = da.aat.invert_coordinates()
        >>> da_inv.get_index("lon")
        Int64Index([67, 68, 69, 70], dtype='int64', name='lon')
        >>> da_inv.get_index("lat")
        Int64Index([90, 89, 88, 87], dtype='int64', name='lat')
        """
        data_obj = self._get_obj(inplace=inplace)
        lon_inv, lat_inv = self._check_coords_inverted()

        # Flip the raster as necessary (based on the flags)
        inv_dict = {}

        if lon_inv:
            logger.info("Longitude was inverted, reversing coordinates.")
            inv_dict[self.x_dim] = data_obj[self.x_dim][::-1]

        if lat_inv:
            logger.info("Latitude was inverted, reversing coordinates.")
            inv_dict[self.y_dim] = data_obj[self.y_dim][::-1]

        if inv_dict:
            data_obj = data_obj.reindex(inv_dict)

        return data_obj if not inplace else None

    def _check_coords_inverted(self):
        """
        Check if latitude and longitude inverted.

        Examples
        --------
        >>> import xarray
        >>> import numpy
        >>> da = xarray.DataArray(
        ...  numpy.arange(16).reshape(4,4),
        ...  coords={"lat":numpy.array([90, 89, 88, 87]),
        ...          "lon":numpy.array([70, 69, 68, 67])}
        ... )
        >>> da.aat._check_coords_inverted()
        (True, False)
        """
        data_obj = self._get_obj(inplace=False)
        lat = data_obj.get_index(self.y_dim)
        lon = data_obj.get_index(self.x_dim)
        return lon[0] > lon[-1], lat[0] < lat[-1]

    def change_longitude_range(
        self, inplace: bool = False
    ) -> Union[xr.DataArray, xr.Dataset]:
        """Convert longitude range between -180 to 180 and 0 to 360.

        For some raster data, outputs are incorrect if longitude ranges
        are not converted from 0 to 360 to -180 to 180, such as the IRI
        seasonal forecast, but *not* the IRI CAMS observational terciles,
        which are incorrect if ranges are stored as -180 to 180.

        ``change_longitude_range()`` will convert between the
        two coordinate systems based on its current state. If coordinates
        lie solely between 0 and 180 then there is no need for conversion
        and the input  will be returned.

        Parameters
        ----------
        inplace : bool, optional
            If True, will overwrite existing data array. Default is False.

        Returns
        -------
        Union[xarray.DataArray, xarray.Dataset]
            Dataset with transformed longitude coordinates.

        Examples
        --------
        >>> import xarray
        >>> import numpy
        >>> temp = 15 + 8 * numpy.random.randn(4, 4, 3)
        >>> precip = 10 * np.random.rand(4, 4, 3)
        >>> ds = xarray.Dataset(
        ...   {
        ...     "temperature": (["lat", "lon", "time"], temp),
        ...     "precipitation": (["lat", "lon", "time"], precip)
        ...   },
        ...   coords={
        ...     "lat":numpy.array([87, 88, 89, 90]),
        ...     "lon":numpy.array([5, 120, 199, 360]),
        ...     "time": pd.date_range("2014-09-06", periods=3)
        ...   }
        ... )
        >>> ds_inv = ds.aat.change_longitude_range()
        >>> ds_inv.get_index("lon")
        Int64Index([-161, 0, 5, 120], dtype='int64', name='lon')
        >>> # invert coordinates back to original, in place
        >>> ds_inv.aat.change_longitude_range(inplace=True)
        >>> ds_inv.get_index("lon")
        Int64Index([0, 5, 120, 199], dtype='int64', name='lon')
        """
        data_obj = self._get_obj(inplace=inplace)
        lon_min = data_obj.indexes[self.x_dim].min()
        lon_max = data_obj.indexes[self.x_dim].max()

        if lon_max > 180:
            logger.info("Converting longitude from 0 360 to -180 to 180.")

            data_obj[self.x_dim] = np.sort(
                ((data_obj[self.x_dim] + 180) % 360) - 180
            )

        elif lon_min < 0:
            logger.info("Converting longitude from -180 to 180 to 0 to 360.")

            data_obj[self.x_dim] = np.sort(
                np.where(  # noqa: FKA01
                    data_obj[self.x_dim] < 0,
                    data_obj[self.x_dim] + 360,
                    data_obj[self.x_dim],
                )
            )

        else:
            logger.info(
                "Indeterminate longitude range and no need to convert."
            )

        return data_obj if not inplace else None


@xr.register_dataarray_accessor("aat")
class AatRasterArray(AatRasterMixin, RasterArray):
    """AA toolbox extension for xarray.DataArray."""

    def __init__(self, xarray_object):
        super().__init__(xarray_object)

    def compute_raster_statistics(
        self,
        gdf: gpd.GeoDataFrame,
        feature_col: str,
        stats_list: List[str] = None,
        percentile_list: List[int] = None,
        all_touched: bool = False,
        geom_col: str = "geometry",
    ) -> pd.DataFrame:
        """Compute raster statistics for polygon geometry.

        ``compute_raster_statistics()`` is designed to
        quickly compute raster statistics across a polygon
        and its features.

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame
            GeoDataFrame with row per area for stats computation.
        feature_col : str
            Column in ``gdf`` to use as row/feature identifier.
        stats_list : List[str], optional
            List of statistics to calculate, by default None.
            Passed to ``get_attr()``.
        percentile_list : List[int], optional
            List of percentiles to compute, by default None.
        all_touched : bool, optional
            If ``True`` all cells touching the region will be
            included, by default False. If ``False``, only
            cells with their centre in the region will be
            included.
        geom_col : str, optional
            Column in ``gdf`` with geometry, by default "geometry".

        Returns
        -------
        pandas.DataFrame
            Dataframe with computed statistics.
        """
        data_obj = self._get_obj(inplace=False)
        if data_obj.rio.crs is None:
            raise MissingCRS("No CRS found, set CRS before computation.")

        df_list = []

        if stats_list is None:
            stats_list = ["mean", "std", "min", "max", "sum", "count"]

        for feature in gdf[feature_col].unique():
            gdf_adm = gdf[gdf[feature_col] == feature]

            da_clip = data_obj.rio.set_spatial_dims(
                x_dim=self.x_dim, y_dim=self.y_dim
            )

            # clip returns error if no overlapping raster cells for geometry
            # so catching and skipping rest of iteration so no stats computed
            try:
                da_clip = da_clip.rio.clip(
                    gdf_adm[geom_col], all_touched=all_touched
                )
            except NoDataInBounds:
                logger.warning(
                    "No overlapping raster cells for %s, skipping.", feature
                )
                continue

            grid_stat_all = []
            for stat in stats_list:
                # count automatically ignores NaNs
                # therefore skipna can also not be given as an argument
                # implemented count cause needed for computing percentages
                kwargs: Dict[str, Any] = {}
                if stat != "count":
                    kwargs["skipna"] = True
                # makes sum return NaN instead of 0 if array
                # only contains NaNs
                if stat == "sum":
                    kwargs["min_count"] = 1
                grid_stat = getattr(da_clip, stat)(
                    dim=[self.x_dim, self.y_dim], **kwargs
                ).rename(f"{stat}_{feature_col}")
                grid_stat_all.append(grid_stat)

            if percentile_list is not None:
                grid_quant = [
                    da_clip.quantile(quant / 100, dim=[self.x_dim, self.y_dim])
                    .drop("quantile")
                    .rename(f"{quant}quant_{feature_col}")
                    for quant in percentile_list
                ]
                grid_stat_all.extend(grid_quant)

            # if dims is 0, it throws an error when merging
            # and then converting to a df
            # this occurs when the input da is 2D
            if not grid_stat_all[0].dims:
                df_adm = pd.DataFrame(
                    {
                        da_stat.name: [da_stat.values]
                        for da_stat in grid_stat_all
                    }
                )

            else:
                zonal_stats_xr = xr.merge(grid_stat_all)
                df_adm = (
                    zonal_stats_xr.to_dataframe()
                    .drop("spatial_ref", axis=1)
                    .reset_index()
                )
            df_adm[feature_col] = feature
            df_list.append(df_adm)

        df_zonal_stats = pd.concat(df_list).reset_index(drop=True)
        return df_zonal_stats


@xr.register_dataset_accessor("aat")
class AatRasterDataset(AatRasterMixin, RasterDataset):
    """AA toolbox extension for xarray.Dataset."""

    def __init__(self, xarray_object):
        super().__init__(xarray_object)

    def get_raster_array(self, var: str) -> xr.DataArray:
        """Get xarray.DataArray from variable and keep dimensions.

        Accessing a component xarray.DataArray using the
        non-coordinate variable name loses and dimensions set
        through ``rio`` or ``aat``. This includes ``x_dim``,
        ``y_dim``, and ``t_dim`` that have to be specifically
        set using ``rio.set_spatial_dims()`` or
        ``aat.set_time_dim()`` respectively. For any dataset
        ``ds``, ``ds.get_raster_array("var")`` will retrieve
        the data array without losing the dimensions. Using
        ``ds["var"]`` will lose the dimensions.

        Parameters
        ----------
        var : str
            Name of variable.

        Returns
        -------
        xarray.DataArray

        Examples
        --------
        >>> import xarray
        >>> import numpy
        >>> temp = 15 + 8 * numpy.random.randn(4, 4, 3)
        >>> precip = 10 * np.random.rand(4, 4, 3)
        >>> ds = xarray.Dataset(
        ...   {
        ...     "temperature": (["lat", "lon", "F"], temp),
        ...     "precipitation": (["lat", "lon", "F"], precip)
        ...   },
        ...   coords={
        ...     "lat":numpy.array([87, 88, 89, 90]),
        ...     "lon":numpy.array([5, 120, 199, 360]),
        ...     "F": pd.date_range("2014-09-06", periods=3)
        ...   }
        ... )
        >>> ds.aat.set_time_dim("F", inplace=True)
        >>> da = ds.aat.get_raster_array("temperature")
        >>> da.aat.t_dim
        'F'
        >>> # directly accessing array loses set dimensions
        >>> ds['temperature'].aat.t_dim # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
            ...
        rioxarray.exceptions.DimensionError: Time dimension not found.
            'aat.set_time_dim()' or using 'rename()' to change the
            dimension name to 't' can address this.
        Data variable: temperature
        """
        obj = self._obj[var]
        # rioxarray attributes
        if self._x_dim is not None and self._y_dim is not None:
            obj.rio.set_spatial_dims(
                x_dim=self._x_dim, y_dim=self._y_dim, inplace=True
            )
        if self._crs is not None:
            obj.rio.set_crs(self._crs, inplace=True)

        # raster module attributes
        if self._t_dim is not None:
            obj.aat.set_time_dim(self._t_dim, inplace=True)

        return obj

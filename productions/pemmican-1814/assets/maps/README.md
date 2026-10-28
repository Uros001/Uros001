# Map data

Natural Earth vector data (public domain, https://www.naturalearthdata.com/). The GeoJSON files are not committed
(~100 MB). Re-download the same layers from the `nvkelso/natural-earth-vector` GitHub repository (`geojson/` folder):

- 10m: land, ocean, coastline, lakes, lakes_north_america, rivers_lake_centerlines, rivers_north_america,
  admin_0_boundary_lines_land, admin_1_states_provinces_lines, graticules_10
- 50m: land, lakes, ocean, rivers_lake_centerlines, coastline, admin_0_countries
- 110m: land, admin_0_countries

`cache/land_global.png` and `cache/land_region.png` are pre-rasterized land masks built from these files by
`tools/film/maps.py`; they are committed so the maps can be re-rendered for land/water without the vectors
(rivers, lakes and borders still need the GeoJSON). Shaded relief: `shadedrelief.jpg` from the matplotlib
basemap data package (NASA/NOAA, public domain).

[![forthebadge](https://forthebadge.com/images/badges/made-with-python.svg)](https://forthebadge.com)
[![forthebadge](https://forthebadge.com/images/badges/contains-technical-debt.svg)](https://forthebadge.com)

Dane:
1. Samochody
- https://overpass-turbo.eu/
- użyj komendy:
```
[out:json][timeout:25];
{{geocodeArea:Warszawa}}->.searchArea;
(
  way["highway"~"motorway|trunk|primary|secondary|tertiary|unclassified|residential"](area.searchArea);
);
out body;
>;
out skel qt;
```
- eksport jako GeoJSON

2. Komunikacja miejska
- https://www.ztm.waw.pl/pliki-do-pobrania/dane-rozkladowe/
- na dole strony link

3. P&R
- skrypt data/scrape_pr.py

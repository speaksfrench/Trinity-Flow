This program, given an anchoring past date in the format YYYY-MM-DD, calculates ten years of historical river flow data in the Trinity river over a three-week timeframe.
It then graphs the years with the maximum and minimum water flow volume in those ten years. For the anchor date, it plots the two weeks beforehand and uses a linear regression line to predict the next seven days.
The title of the graph reports the current change in water flow and the total volume of water up to the anchor date in acre-feet.

Usage:
python main.py <YYYY-MM-DD>

Necessary Python modules:
hydrofunctions
humanize
matplotlib
datetime
numpy
statistics

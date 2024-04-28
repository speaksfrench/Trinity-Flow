import hydrofunctions as hf, matplotlib.pyplot as plt, matplotlib.dates as mdates, numpy as np, statistics
import matplotlib
import humanize # makes stuff easier for humans to read
matplotlib.use('TkAgg') # specify GUI
from datetime import datetime, timedelta
import argparse

# TODO:
# 2023-09-27 has the same min/max line
# Anything containing February 29th does not work (thanks to DateTime)
# Incomplete data causes a complete crash, find fix (?)


def main(args):
    plt.figure(figsize=(12, 7))
    trinity_burnt_ranch_id = '11527000'
    anchor = datetime.strptime(str(args.anchor), '%Y-%m-%d')
    data = list()
    amount_of_years = 10
    column = 'USGS:11527000:00060:00000'
    leap_day = datetime(2000, 2, 29)

    # Get information from NWIS for every year in the last ten years
    # Download data
    for year in range(amount_of_years):
        begin_date = datetime(anchor.year - year, anchor.month, anchor.day - 14)
        if year > 0: 
            end_date = (begin_date + timedelta(days=21))    # ending date is year years in the past and seven days into the future
        else: 
            end_date = anchor                                                        # if year = 0, then it is the anchor year and we cannot go 7 days in the future

        print('Fetching date range:', begin_date, 'to', end_date)

        year_raw = hf.NWIS(trinity_burnt_ranch_id, 'iv', start_date=begin_date.isoformat(), end_date=end_date.isoformat(), verbose=False)
        data.append(year_raw)

    # Creates a list of dataframes of every NWIS data entry
    dframes = list()
    for i in data:
        dframes.append(i.df('discharge')[:])

    # Calculate the average flows for each year
    sum_flows = list()
    for i in dframes: # iterates through every dataframe 
        sum = 0
        for ii in i[column]:
            sum += ii * 15 * 60
        sum_flows.append(sum)

    # Find the max and min flow years
    max_year_idx = sum_flows.index(max(sum_flows[1:])) # avoid the first year
    min_year_idx = sum_flows.index(min(sum_flows[1:]))

    # The "derivative"
    curr_flow1 = dframes[0][column].iloc[-1]
    curr_flow2 = dframes[0][column].iloc[-2]
    derivative = (curr_flow1 - curr_flow2) * 4

    # Get the mean and stdev for every year
    entries = list()
    for year in dframes[1:]: # skip the current year
        for idx, entry in enumerate(year[column]): # appends every time frame to the appropriate time frame section
            try:
                entries[idx].append(entry)
            except IndexError: # if for some reason this array is too short, append another
                entries.append([])
                entries[idx].append(entry)

    means = list()
    stds = list()
    for time in entries:
        if np.isnan(time).any(): # makes sure there are no NaN values 
            temp = list()
            for i in time: # in the case of a NaN value, just create a new array without the NaN and move on.
                if not np.isnan(i):
                    temp.append(i)
            stds.append(statistics.stdev(temp))
            means.append(statistics.mean(temp))
            continue
        stds.append(statistics.stdev(time))
        means.append(statistics.mean(time))

    # Formats the dates
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())

    try:
        max_x_axis = [datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[max_year_idx].index] # makes a list of every time in the max year and removes the year
        min_x_axis = [datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[min_year_idx].index]
    except ValueError:
        print('Error: DateTime does not consider February 29th (leap day) a valid date, even in the case of a leap year. Your anchor date {0} is either within two weeks after leap day or one week before.'.format(anchor))
        quit()
    # get x ticks based off month and year only
    x_ticks = list()
    for idx, i in enumerate(max_x_axis):
        if idx % 500 == 0:
            x_ticks.append(datetime.strptime(str(i)[5:10], "%m-%d"))
    plt.xticks(x_ticks) 

    # Get the dataframe for each year
    curr_year = dframes[0]
    max_year = dframes[max_year_idx]
    min_year = dframes[min_year_idx]

    # Current
    curr_date_ym = datetime.strptime(str(dframes[0].index[-1])[5:19],"%m-%d %H:%M:%S") # current year and month based on anchor

    # For some odd reason, the current year starts a litte bit earlier  than the other years. I really don't know why this is.
    plt.plot([datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in dframes[0].index], curr_year, 'k', label=f'Anchor year ({anchor.isoformat()[0:4]})')

    # Max
    max_year_date = (anchor - timedelta(days = max_year_idx * 365)).isoformat()[0:4]
    plt.plot(max_x_axis, max_year, 'g', label=f'Max year ({max_year_date})')

    # Minimum
    min_year_date = (anchor - timedelta(days = min_year_idx * 365)).isoformat()[0:4]
    plt.plot(min_x_axis, min_year, 'b', label=f'Min year ({min_year_date})')

    # STDev top
    # Y-vals
    std_top_yvals = list()
    std_bottom_yvals = list()

    for idx, i in enumerate(means):
        std_top_yvals.append(means[idx] + 0.5 * stds[idx])
        std_bottom_yvals.append(means[idx] - 0.5 * stds[idx])

    # TODO: Make plot start on anchor day and not after 
    # Average fill
    plt.plot(min_x_axis, std_top_yvals, color='0.5', linestyle='--')
    plt.plot(min_x_axis, std_bottom_yvals, color='0.5', linestyle='--')
    plt.gca().fill_between(min_x_axis, std_top_yvals, std_bottom_yvals, color='0.9')

    # Mean graph
    plt.plot(min_x_axis, means, color='w', linestyle='dashdot', label='Mean')


    # Linear Regression 
    current_year = dframes[0]
    x_vals = [idx for idx, i in enumerate(current_year.index)] # to_numeric does not make them reasonable indices, but in fact large integers
    y_vals = list(dframes[0][column])

    x_bar = statistics.mean(x_vals)
    y_bar = statistics.mean(y_vals)
    x_std = statistics.stdev(x_vals)
    
    # TODO: Fix: for some dates, NWIS has NaN values. If I just remove those from the data, my axis will be off.
    try:
        y_std = statistics.stdev(y_vals)
    except AttributeError: 
        print('NWIS\'s database is missing entries for that timeframe. Try another anchor date.')
        quit()

    total = 0.0
    for i in range(len(x_vals)): # yes, I did not use dataframes for this. it seemed easier without them, as using dataframes also returns a dataframe for r, which seems impractical and confusing
        total += (x_vals[i] - x_bar) * (y_vals[i] - y_bar)

    r = total / ((len(x_vals) - 1) * x_std * y_std)
    slope = r * (y_std / x_std)

    regression_end_date = anchor + timedelta(days=7)

    # 1) creates an arange of values starting from the current date and going 7 days into the future then 2) removes the year from all of those values
    increment = 1 / 24 / 60 * 15 # 15-minute increment
    x_start = dframes[0][column].iloc[-1] # the final value of the current year (the y-intercept of the regression line)
    regression_xvals = [datetime.strptime(str(i)[5:19], "%m-%d %H:%M:%S") for i in np.arange(anchor + timedelta(days=0.25), regression_end_date, timedelta(days=increment)).astype(datetime)] # oddly enough, we have to start the regression line 0.25 days after the current date
    regression_yvals = [i * slope + x_start for i in range(len(regression_xvals))]

    plt.axvline(x = curr_date_ym, color = 'r', linestyle = '--', label='{0}'.format(str(anchor)[5:10])) # converts the current date to m/y and plots a line on that date (marks the beginning of the regression)
    plt.plot(regression_xvals, regression_yvals, color = 'k')

    plt.legend(loc="upper left")
    plt.suptitle('Trinity River at Hoopa (CFS)', fontsize=20)

    current_flow = humanize.intcomma(sum_flows[0] / 43560)[:10]
    change = str(derivative)[:4].strip('-').strip('.')
    if derivative > 0: plt.title(f'{current_flow} acre-feet : increasing {change} CFS/hr') # if derivative is positive, say increasing, decreasing, or stagnant
    elif derivative < 0: plt.title(f'{current_flow} acre-feet : dropping {change} CFS/hr')
    else: plt.title(f'{current_flow} acre-feet : no change ({change} CFS/hr)')
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Graphs the maximum, minimum, current, and average flow of the Trinity River over the past 10 years.')
    parser.add_argument('anchor', metavar='anchor', type=str, help='Usage: main.py <time> (YYYY-MM-DD)', default=str(datetime.now().isoformat()))  
    try:
        args = parser.parse_args()
    except:
        print('Usage: main.py <time> (YYYY-MM-DD)')
        quit()
    main(args)